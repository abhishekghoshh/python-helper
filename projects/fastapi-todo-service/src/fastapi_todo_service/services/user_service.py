import json
from fastapi_todo_service.repositories.user_repo import UserRepository
from fastapi_todo_service.models.user import UserCreate, UserResponse
from fastapi_todo_service.core.redis import RedisClient
from fastapi import HTTPException

class UserService:
    def __init__(self, repo: UserRepository, redis: RedisClient):
        self.repo = repo
        self.redis = redis

    async def register_user(self, user_data: UserCreate) -> UserResponse:
        existing = await self.repo.get_by_email(user_data.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        user = await self.repo.create(user_data)
        return UserResponse(id=user.id, email=user.email, username=user.username)

    async def get_user(self, user_id: int) -> UserResponse:
        cache_key = f"user:{user_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return UserResponse(**json.loads(cached))

        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        res = UserResponse(id=user.id, email=user.email, username=user.username)
        await self.redis.set(cache_key, res.model_dump_json(), ex=300)
        return res