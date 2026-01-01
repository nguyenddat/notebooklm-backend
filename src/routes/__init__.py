from fastapi import APIRouter

from .route_retrieve import router as retrieve_router
from .route_user import router as user_router
from .route_notebook import router as notebook_router

total_router = APIRouter(prefix="/api")

total_router.include_router(retrieve_router, prefix="/retrieve", tags=["retrieve"])
total_router.include_router(user_router, prefix="/user", tags=["user"])
total_router.include_router(notebook_router, prefix="/notebook", tags=["notebook"])