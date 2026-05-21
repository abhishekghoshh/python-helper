from sqlmodel import SQLModel, Field, Relationship
from typing import Optional



class TodoBase(SQLModel):
    title: str
    description: Optional[str] = None
    is_completed: bool = Field(default=False)

class Todo(TodoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    owner: "User" = Relationship(back_populates="todos")

class TodoCreate(TodoBase):
    pass

class TodoResponse(TodoBase):
    id: int
    user_id: int