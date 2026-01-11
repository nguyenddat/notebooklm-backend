import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Config(BaseSettings):
    # directory
    base_dir: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
    artifact_dir: str = os.path.join(base_dir, 'artifact')
    static_dir: str = os.path.join(base_dir, 'static')
    
    # database
    database_url: str = os.getenv("DATABASE_URL", "")
    qdrant_url: str = os.getenv("QDRANT_URL", "")
    qdrant_collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "NotebookLM")
    qdrant_embedding_dim: int = os.getenv("QDRANT_EMBEDDING_DIM", 1536)
    
    # log level
    log_level: str = "INFO"
    
    # JWT
    secret_key: str = os.getenv('SECRET_KEY', 'Gay')
    security_algorithm: str = os.getenv('SECURITY_ALGORITHM', "HS256")
    access_token_expire_minutes: int = os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30)
    refresh_token_expire_days: int = os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 7)
    
    # openai
    openai_api_key: str = os.getenv('OPENAI_API_KEY', '')
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    
    # retrieve config
    min_image_area: int = 500

config = Config()
os.makedirs(config.artifact_dir, exist_ok=True)
os.makedirs(config.static_dir, exist_ok=True)