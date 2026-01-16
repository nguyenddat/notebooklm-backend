from models.entities import Message
from models.entities.model_message import MessageRole
from services.srv_base import BaseService
from services.llm.srv_llm import llm_service

class MessageService(BaseService[Message]):
    def __init__(self, model: type[Message]):
        super().__init__(model)
    
    def get_last_messages_by_notebook_id(
        self,
        notebook_id: int,
        db,
        limit: int = 3,
    ):
        messages = (
            db.query(self.model)
            .filter(self.model.notebook_id == notebook_id)
            .order_by(self.model.id.desc())
            .limit(limit)
            .all()
        )

        return list(reversed(messages))
    
    def format_messages(
        self,
        messages: list[Message],
    ) -> list[dict]:
        conversation_lines = []
        for msg in messages:
            role = "User" if msg.role == MessageRole.USER else "Assistant"
            conversation_lines.append(
                f"{role}: {msg.content.strip()}"
            )

        conversation_text = "\n".join(conversation_lines)
        return conversation_text
        
    def summarize_conversation(
        self,
        messages: list[Message],
    ) -> str:
        formatted_messages = self.format_messages(messages)
        
        if not formatted_messages:
            return ""
        
        # Gọi llm để tóm tắt
        params = {"question": "", "conversation_history": formatted_messages,}
        result = llm_service.get_chat_completion("summarize_history", params)
        return result["response"]

    def chat(self, query: str, history: str, documents: str) -> str:
        params = {
            "question": query,
            "conversation_history": history,
            "retrieved_documents": documents,
        }

        result = llm_service.get_chat_completion("notebook_chat", params)
        return result

message_service = MessageService(Message)