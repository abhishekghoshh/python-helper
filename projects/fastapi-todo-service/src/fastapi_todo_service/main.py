import aiofiles
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from uvicorn import logging
from fastapi_todo_service.api.v1 import users, todos
from fastapi_todo_service.core.config import settings
from fastapi_todo_service.core.database import engine
from sqlmodel import SQLModel
import os

from fastapi_todo_service.core.logger_client import LoggerClient

logger = LoggerClient.get_logger(__name__)


async def async_get_content(file_name: str) -> str:
    async with aiofiles.open(file_name, mode='r') as f:
        content = await f.read()
    return content.strip()


def sync_get_content(file_name: str) -> str:
    result_path = os.path.abspath(os.path.join(os.path.dirname(__file__), file_name))
    # list all the files in the directory to verify the path
    for file in os.listdir(os.path.dirname(result_path)):
        logger.info(f"Found file: {file}")
    with open(result_path, mode='r') as f:
        return f.read().strip()

VERSION = sync_get_content("../../.version")


@asynccontextmanager
async def lifespan(app: FastAPI):
    LoggerClient.setup_logging()
    async with engine.begin() as conn:
        # Automigrate db on startup
        await conn.run_sync(SQLModel.metadata.create_all)
    yield


app = FastAPI(title=settings.PROJECT_NAME, version=VERSION, lifespan=lifespan)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(todos.router, prefix=settings.API_V1_STR)




@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": VERSION
        }