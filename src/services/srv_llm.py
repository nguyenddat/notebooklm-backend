import threading
from typing import Dict

from core.llm import openai_llm, gemini_llm
from utils.get_prompt import get_prompt_by_task
from langchain_core.messages import HumanMessage


class LLMService:
    def __init__(self, max_concurrent: int = 3):
        self._semaphore = threading.Semaphore(max_concurrent)

    def get_chat_completion(self, task: str, params: Dict):
        with self._semaphore:
            prompt, parser = get_prompt_by_task(task)

            # TEXT-ONLY TASK
            if task in {"summarize_history", "notebook_chat", "correct_section_structure"}:
                chain = prompt | openai_llm | parser
                return chain.invoke(params).dict()

            # IMAGE TASK
            elif task in {"image_captioning", "formula_formating"}:
                return self._run_image_task(prompt, parser, params)

            else:
                raise ValueError(f"Unknown task: {task}")

    def _build_image_human_message(
        self,
        question: str,
        image_base64: str,
        mime_type: str,
    ):
        return HumanMessage(
            content=[
                {"type": "text", "text": question},
                {
                    "type": "image_url",
                    "image_url": {"url": image_base64},
                },
            ]
        )

    def _run_image_task(self, prompt, parser, params: Dict):
        question = params["question"]
        context = params["context"]
        image_base64 = params["image_base64"]
        mime_type = params.get("mime_type", "image/png")

        # SYSTEM message
        system_messages = prompt.format_messages(context=context)

        # HUMAN multimodal message
        human_message = self._build_image_human_message(
            question=question,
            image_base64=image_base64,
            mime_type=mime_type,
        )

        messages = system_messages + [human_message]

        response = gemini_llm.invoke(messages)
        return parser.parse(response.content).dict()

llm_service = LLMService(max_concurrent=3)