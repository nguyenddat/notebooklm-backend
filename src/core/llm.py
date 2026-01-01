from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from core import config

openai_embeddings = OpenAIEmbeddings(api_key=config.openai_api_key)

qa_llm = ChatOpenAI(model_name="gpt-4.1-mini", api_key=config.openai_api_key, temperature=0)
summary_llm = ChatOpenAI(model_name="gpt-4o-mini", api_key=config.openai_api_key, temperature=0)