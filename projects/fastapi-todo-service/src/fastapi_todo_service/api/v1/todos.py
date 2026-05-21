from fastapi import APIRouter, Depends
from typing import List
from fastapi_todo_service.models.todo import TodoCreate, TodoResponse
from fastapi_todo_service.services.todo_service import TodoService
from fastapi_todo_service.dependencies import get_todo_service

router = APIRouter(prefix="/todos", tags=["todos"])

@router.post("/{user_id}", response_model=TodoResponse)
async def create_todo(user_id: int, todo: TodoCreate, service: TodoService = Depends(get_todo_service)):
    return await service.create_todo(todo, user_id)

@router.get("/{user_id}", response_model=List[TodoResponse])
async def read_todos(user_id: int, service: TodoService = Depends(get_todo_service)):
    return await service.get_todos(user_id)