from fastapi import APIRouter, Depends
from fastapi_todo_service.models.user import UserCreate, UserResponse
from fastapi_todo_service.services.user_service import UserService
from fastapi_todo_service.dependencies import get_user_service

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate, service: UserService = Depends(get_user_service)):
    return await service.register_user(user)

@router.get("/{user_id}", response_model=UserResponse)
async def read_user(user_id: int, service: UserService = Depends(get_user_service)):
    return await service.get_user(user_id)