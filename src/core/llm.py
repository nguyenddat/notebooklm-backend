from pix2tex.cli import LatexOCR
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI

from core import config

openai_embeddings = OpenAIEmbeddings(api_key=config.openai_api_key)

openai_llm = ChatOpenAI(model_name="gpt-4.1-mini", api_key=config.openai_api_key, temperature=0)
gemini_llm = ChatOpenAI(
    model_name="google/gemini-2.5-flash-preview-09-2025",
    openai_api_key=config.openrouter_api_key,
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0
)

latex_ocr = LatexOCR()