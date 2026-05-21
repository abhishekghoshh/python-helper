from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi_todo_service.core.database import get_async_session
from fastapi_todo_service.core.redis import get_redis, RedisClient
from fastapi_todo_service.repositories.user_repo import UserRepository
from fastapi_todo_service.repositories.todo_repo import TodoRepository
from fastapi_todo_service.services.user_service import UserService
from fastapi_todo_service.services.todo_service import TodoService

def get_user_repo(session: AsyncSession = Depends(get_async_session)) -> UserRepository:
    return UserRepository(session)

def get_todo_repo(session: AsyncSession = Depends(get_async_session)) -> TodoRepository:
    return TodoRepository(session)

def get_user_service(
    repo: UserRepository = Depends(get_user_repo),
    redis: RedisClient = Depends(get_redis)
) -> UserService:
    return UserService(repo, redis)

def get_todo_service(repo: TodoRepository = Depends(get_todo_repo)) -> TodoService:
    return TodoService(repo)