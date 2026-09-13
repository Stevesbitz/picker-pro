from typing import List, Optional

from pydantic import BaseModel


class User(BaseModel):
    id: str
    name: str
    checked: bool = True
    pickedThisRound: bool = False
    picked_at: Optional[str] = None


class StateResponse(BaseModel):
    users: List[User]
    last_picked_user: Optional[User] = None


class CreateUserRequest(BaseModel):
    name: str


class ToggleUserRequest(BaseModel):
    checked: bool
