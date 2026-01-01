from typing import Dict

from core.llm import qa_llm
from utils.get_prompt import get_prompt_by_task

class LLMService:
    @staticmethod
    def get_chat_completion(task: str, params: Dict):
        prompt, parser = get_prompt_by_task(task)
        chain = prompt | qa_llm | parser
        return chain.invoke(params).dict()