from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    todos: List["Todo"] = Relationship(back_populates="owner")

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int