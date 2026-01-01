from sqlalchemy.orm import Session

from models.entities.model_notebook import Notebook
from services.srv_base import BaseService

class NotebookService(BaseService[Notebook]):
    def __init__(self, model: type[Notebook]):
        super().__init__(model)
        
    def get_notebooks_by_user_id_paginated(self, user_id: int, db: Session, limit: int = 20, last_id: int = 0):
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .filter(self.model.id > last_id)
            .order_by(self.model.id.asc())
            .limit(limit)
            .all()
        )
        
notebook_service = NotebookService(Notebook)