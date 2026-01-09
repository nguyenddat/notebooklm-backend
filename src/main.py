import os
import warnings

warnings.filterwarnings("ignore", category=UserWarning)
os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
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

    application.mount(
        "/static",
        StaticFiles(directory="static"),
        name="static"
    )

    application.include_router(total_router)
    return application

app = get_application()