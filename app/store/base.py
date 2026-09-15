from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Protocol

from app.schemas.rooms import Room, TaskPool
from app.schemas.users import StateResponse, User


class StateStore(Protocol):
    def get_state(self, pool_id: Optional[str] = None) -> StateResponse:
        ...

    def add_user(self, name: str, pool_id: Optional[str] = None) -> User:
        ...

    def toggle_check(self, user_id: str, checked: bool, pool_id: Optional[str] = None) -> Optional[User]:
        ...

    def toggle_ooo(self, user_id: str, is_ooo: bool, pool_id: Optional[str] = None) -> Optional[User]:
        ...

    def delete_user(self, user_id: str, pool_id: Optional[str] = None) -> bool:
        ...

    def pick_next(self, pool_id: Optional[str] = None) -> Optional[User]:
        ...

    def reset_round(self, pool_id: Optional[str] = None) -> None:
        ...


class BaseRoomStore(ABC):
    """Persistence contract for room metadata and room state."""

    @abstractmethod
    def create_room(self, name: str) -> Room:
        raise NotImplementedError

    @abstractmethod
    def get_room(self, room_id: str) -> Optional[Room]:
        raise NotImplementedError

    @abstractmethod
    def save_room(self, room: Room) -> Room:
        raise NotImplementedError

    @abstractmethod
    def delete_room(self, room_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list_rooms(self) -> List[Room]:
        raise NotImplementedError

    @abstractmethod
    def get_state_store(self, room_id: str) -> Optional[StateStore]:
        raise NotImplementedError

    @abstractmethod
    def create_pool(self, room_id: str, name: str) -> TaskPool:
        raise NotImplementedError

    @abstractmethod
    def list_pools(self, room_id: str) -> List[TaskPool]:
        raise NotImplementedError

    @abstractmethod
    def get_admin_dashboard_data(self):
        raise NotImplementedError
