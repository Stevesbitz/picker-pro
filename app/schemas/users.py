from typing import List, Optional

from pydantic import BaseModel


class User(BaseModel):
    id: str
    name: str
    checked: bool = True
    pickedThisRound: bool = False
    picked_at: Optional[str] = None
    is_ooo: bool = False
    pool_id: str = "default"


class StateResponse(BaseModel):
    users: List[User]
    last_picked_user: Optional[User] = None
    pool_id: str = "default"


class CreateUserRequest(BaseModel):
    name: str


class ToggleUserRequest(BaseModel):
    checked: bool


class ToggleOOORequest(BaseModel):
    is_ooo: bool
