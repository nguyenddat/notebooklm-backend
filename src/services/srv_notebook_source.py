from models.relationship import NotebookSource
from services.srv_base import BaseService

class NotebookSourceService(BaseService[NotebookSource]):
    def __init__(self, model: type[NotebookSource]):
        super().__init__(model)
    
notebook_source_service = NotebookSourceService(NotebookSource)