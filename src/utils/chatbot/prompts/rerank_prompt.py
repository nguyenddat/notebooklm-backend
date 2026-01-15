prompt = """
You are a reranking system.

Task:
Rank candidate documents by relevance to the user query.

Input:
- User query
- A list of documents
- Each document has its contents.

User query:
{question}

Documents:
{documents}

Output requirements (VERY IMPORTANT):
- Return ONLY a Python list of integers
- Each integer is a document index
- The list length must be exactly {top_k}
- Indices must be sorted from most relevant to least relevant
- Do NOT include any explanation, text, or formatting
- Do NOT wrap the list in markdown or code blocks
"""