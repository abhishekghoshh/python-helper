from fastapi_todo_service.repositories.todo_repo import TodoRepository
from fastapi_todo_service.models.todo import TodoCreate, TodoResponse
from typing import List

class TodoService:
    def __init__(self, repo: TodoRepository):
        self.repo = repo

    async def create_todo(self, todo_data: TodoCreate, user_id: int) -> TodoResponse:
        todo = await self.repo.create(todo_data, user_id)
        return TodoResponse(**todo.model_dump())

    async def get_todos(self, user_id: int) -> List[TodoResponse]:
        todos = await self.repo.get_by_user(user_id)
        return [TodoResponse(**t.model_dump()) for t in todos]