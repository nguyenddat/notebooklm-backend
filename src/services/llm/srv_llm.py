import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

from core.llm import openai_llm, gemini_llm
from .get_prompt import get_prompt_by_task
from langchain_core.messages import HumanMessage
from core import logger

class LLMService:
    def __init__(self, max_concurrent: int = 3):
        self._semaphore = threading.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)

    def get_chat_completion(self, task: str, params: Dict):
        with self._semaphore:
            prompt, parser = get_prompt_by_task(task)

            # TEXT-ONLY TASK
            if task in {"summarize_history", "correct_section_structure", "rerank", "notebook_chat", "rewrite_question"}:
                chain = prompt | openai_llm | parser
                return chain.invoke(params).dict()

            # IMAGE TASK
            elif task in {"image_captioning", "image_captioning_v2"}:
                return self._run_image_task(prompt, parser, params)

            else:
                raise ValueError(f"Unknown task: {task}")

    def _build_message(self, question: Optional[str] = None, images: Optional[List[str]] = None) -> HumanMessage:
        if question is None and images is None:
            raise ValueError("At least one of question or images must be provided.")
        
        content = []
        if question:
            content.append({"type": "text", "text": question}) 
        for base64 in images:
            content.append(
                {"type": "image",
                 "base64": base64,
                 "mime_type": "image/png"}
            )
        return HumanMessage(content=content)
    
    def _run_image_task(self, prompt, parser, params: Dict):
        question = params.get("question", None)
        images = params.get("images", None)
        retrieved_documents = params.get("retrieved_documents", None)

        # system message
        system_messages = prompt.format_messages(retrieved_documents=retrieved_documents)

        # multimodal message
        human_message = self._build_message(question, images)
        
        messages = system_messages + [human_message]
        response = gemini_llm.invoke(messages)
        return parser.parse(response.content).dict()
    
    def batch_get_chat_completion(
        self, 
        tasks_with_params: List[Tuple[str, Dict]]
    ) -> List[Tuple[int, Dict, Optional[Exception]]]:
        results = []
        def process_single(index: int, task: str, params: Dict):
            try:
                result = self.get_chat_completion(task, params)
                return (index, result, None)
            except Exception as e:
                logger.error(f"Error in batch processing task {task} at index {index}: {e}")
                return (index, None, e)
        
        # Submit all tasks to executor
        futures = []
        for idx, (task, params) in enumerate(tasks_with_params):
            future = self._executor.submit(process_single, idx, task, params)
            futures.append(future)
        
        # Collect results as they complete
        for future in as_completed(futures):
            results.append(future.result())
        
        # Sort by original index to maintain order
        results.sort(key=lambda x: x[0])
        return results

llm_service = LLMService(max_concurrent=3)