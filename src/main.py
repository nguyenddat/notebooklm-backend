from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from core import settings
from routes import total_router

def get_application() -> FastAPI:
    application = FastAPI()
    application.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(total_router)
    return application

app = get_application()