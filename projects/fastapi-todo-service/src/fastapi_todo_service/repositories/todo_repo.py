from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi_todo_service.models.todo import Todo, TodoCreate
from typing import List

class TodoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, todo_data: TodoCreate, user_id: int) -> Todo:
        db_todo = Todo(**todo_data.model_dump(), user_id=user_id)
        self.session.add(db_todo)
        await self.session.commit()
        await self.session.refresh(db_todo)
        return db_todo

    async def get_by_user(self, user_id: int) -> List[Todo]:
        statement = select(Todo).where(Todo.user_id == user_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())