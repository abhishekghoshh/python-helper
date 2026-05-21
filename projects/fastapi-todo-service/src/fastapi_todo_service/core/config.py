

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Todo Service"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/todo_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        case_sensitive = True

settings = Settings()