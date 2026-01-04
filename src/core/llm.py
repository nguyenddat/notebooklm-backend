from pix2tex.cli import LatexOCR
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI

from core import config

openai_embeddings = OpenAIEmbeddings(api_key=config.openai_api_key)

qa_llm = ChatOpenAI(model_name="gpt-4.1-mini", api_key=config.openai_api_key, temperature=0)
summary_llm = ChatOpenAI(model_name="gpt-4o-mini", api_key=config.openai_api_key, temperature=0)
image_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=config.gemini_api_key, temperature=0)
latex_ocr = LatexOCR()