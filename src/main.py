import os
import warnings
import torch

print(f"PyTorch version: {torch.__version__}")
print(f"Is CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"Current device: {torch.cuda.get_device_name(0)}")

warnings.filterwarnings("ignore", category=UserWarning)
os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from core import settings, setup_logging
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

    setup_logging()
    
    application.include_router(total_router)
    return application

app = get_application()