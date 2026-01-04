import re
from docling.document_converter import DocumentConverter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from core.llm import summary_llm
from utils.token_count import estimate_token_count

class ContextualRetrievalService:
    def __init__(self):
        self.document_converter = DocumentConverter()
        self.llm = summary_llm
        self.context_len = 128000

    # chuyển file thành text/ markdown
    def document_to_md(self, file_path):
        result = self.document_converter.convert(file_path)
        markdown_text = result.document.export_to_markdown()
        return markdown_text
    
    def normalize_text(self, text):
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        return text.strip()

    # document-level: tóm tắt toàn bộ văn bản
    def document_level(self, md_text):
        system_prompt = """
        You are an expert document analyst.
        Summarize the following document in 5-7 concise bullet points.
        Focus on main ideas, structure, and intent.
        """.strip()

        # Tính tokens
        prompt_len = estimate_token_count(self.llm.model_name, system_prompt)
        doc_len = estimate_token_count(self.llm.model_name, md_text)

        # Nếu đủ tokens của model
        if prompt_len + doc_len <= self.context_len:
            print("Document fits context. Summarizing directly.")
            prompt = system_prompt + "\n\nDocument:\n" + md_text
            return self.llm.invoke(prompt).content
        
        # Nếu dài hơn -> tách thành chunks -> merge
        print(f"Document too long ({doc_len} tokens). Using hierarchical summarization.")
        max_doc_len = self.context_len - prompt_len - 512
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_doc_len,
            chunk_overlap=100,
            separators=["\n## ", "\n# ", "\n\n", "\n", ".", " ", ""],
            length_function=lambda x: estimate_token_count(
                self.llm.model_name, x
            ),
        )
        chunks = splitter.split_text(md_text)
        
        partial_summaries = []
        for idx, chunk in enumerate(chunks):
            print(f"Summarizing chunk {idx+1}/{len(chunks)}")
            chunk_prompt = system_prompt + f"\n\nDocument chunk ({idx+1}/{len(chunks)}):\n" + chunk
            partial = self.llm.invoke(chunk_prompt).content
            partial_summaries.append(partial)
            
        # Merge
        merge_prompt = """
You are given summaries of different parts of a document.
Merge them into a coherent global summary with 5–7 bullet points.
Avoid repetition.
""".strip()
        merged_text = "\n".join(partial_summaries)
        final_prompt = merge_prompt + "\n\nPartial summaries:\n" + merged_text
        return self.llm.invoke(final_prompt).content
        
    
    def split_by_sections(self, md_text):
        sections = []
        current_path = []
        buffer = []

        for line in md_text.splitlines():
            heading = re.match(r'^(#+)\s+(.*)', line)
            if heading:
                if buffer:
                    sections.append({
                        "path": " > ".join(current_path) if current_path else "ROOT",
                        "content": "\n".join(buffer)
                    })
                    buffer = []

                level = len(heading.group(1))
                title = heading.group(2).strip()

                current_path = current_path[:level-1]
                current_path.append(title)
            else:
                buffer.append(line)

        if buffer:
            sections.append({
                "path": " > ".join(current_path),
                "content": "\n".join(buffer)
            })

        return sections
    
    
    def section_level(self, section_text, section_path, doc_summary):
        prompt = f"""
        You are summarizing a section of a larger document.

        Document summary:
        {doc_summary}

        Section path:
        {section_path}

        Section content:
        {section_text}

        Summarize this section in 2-3 concise bullet points.
        """.strip()
        return self.llm.invoke(prompt).content
    
    
    def chunk_section(self, section_text):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""],
            length_function=lambda x: estimate_token_count(
                self.llm.model_name, x
            ),
        )
        return splitter.split_text(section_text)
    
    # chunking văn bản -> gắn section path cho chunk + contextualize
    def contextualize_chunk(
        self,
        chunk,
        doc_summary,
        section_path,
        section_summary,
    ):
        prompt = f"""
        You are preparing a text chunk for retrieval in a RAG system.

        Document summary:
        {doc_summary}

        Section path:
        {section_path}

        Section summary:
        {section_summary}

        Chunk:
        {chunk}

        Rewrite the chunk so that it can be understood independently
        during retrieval. Do NOT add new facts.
        """.strip()
        return self.llm.invoke(prompt).content

    def build_contextual_chunks(self, md_text):
        md_text = self.normalize_text(md_text)
        
        # Tóm tắt docs -> chia thành các sections
        doc_summary = self.document_level(md_text)
        sections = self.split_by_sections(md_text)

        all_chunks = []
        for sec in sections:
            section_summary = self.section_level(sec["content"], sec["path"], doc_summary)
            chunks = self.chunk_section(sec["content"])
            for idx, chunk in enumerate(chunks):
                ctx_chunk = self.contextualize_chunk(chunk, doc_summary, sec["path"], section_summary)

                all_chunks.append({
                    "text": ctx_chunk,
                    "metadata": {
                        "section_path": sec["path"],
                        "section_summary": section_summary,
                        "chunk_index": idx
                    }
                })

        return all_chunks

    def build_faiss_index(self, md_text: str, save_path: str = "faiss_index"):
        contextual_chunks = self.build_contextual_chunks(md_text)
        documents = []
        for chunk in contextual_chunks:
            documents.append(
                Document(
                    page_content=chunk["text"],
                    metadata=chunk["metadata"]
                )
            )

        print(f"Building FAISS index with {len(documents)} chunks...")
        vectorstore = FAISS.from_documents(
            documents,
            embedding=self.embedding
        )

        vectorstore.save_local(save_path)
        print(f"FAISS index saved to {save_path}")
        return vectorstore
    
    def load_faiss_index(self, path: str = "faiss_index"):
        return FAISS.load_local(path, embeddings=self.embedding, allow_dangerous_deserialization=True)
    
    def rewrite_query(self, user_query: str):
        prompt = f"""
        You are optimizing a user query for document retrieval.

        User question:
        {user_query}

        Rewrite the query to be:
        - Concise
        - Keyword-focused
        - Free of conversational language

        Return ONLY the rewritten query.
        """.strip()

        return self.llm.invoke(prompt).content.strip()

    def query_relevant_documents(
        self,
        user_query: str,
        vectorstore,
        top_k: int = 5,
        rerank_top_k: int = 3,
    ):
        retrieval_query = self.rewrite_query(user_query)
        print(f"[Retrieval query] {retrieval_query}")

        docs = vectorstore.as_retriever().get_relevant_documents(retrieval_query)
        
        results = []
        for i, doc in enumerate(docs):
            results.append({
                "rank": i + 1,
                "text": doc.page_content,
                "metadata": doc.metadata
            })

        return results


contextual_retrieval_service = ContextualRetrievalService()