from typing import Optional

from app.schemas.users import StateResponse, User
from app.store.base import StateStore

DEFAULT_POOL_ID = "default"


class PickerService:
    """Application service for picker operations backed by an injected store."""

    def __init__(self, state_store: StateStore):
        self._state_store = state_store

    def get_state(self, pool_id: Optional[str] = None) -> StateResponse:
        return self._state_store.get_state(pool_id) if pool_id else self._state_store.get_state()

    def add_user(self, name: str, pool_id: Optional[str] = None) -> User:
        return self._state_store.add_user(name, pool_id) if pool_id else self._state_store.add_user(name)

    def toggle_check(self, user_id: str, checked: bool, pool_id: Optional[str] = None) -> Optional[User]:
        return self._state_store.toggle_check(user_id, checked, pool_id) if pool_id else self._state_store.toggle_check(user_id, checked)

    def toggle_ooo(self, user_id: str, is_ooo: bool, pool_id: Optional[str] = None) -> Optional[User]:
        return self._state_store.toggle_ooo(user_id, is_ooo, pool_id) if pool_id else self._state_store.toggle_ooo(user_id, is_ooo)

    def delete_user(self, user_id: str, pool_id: Optional[str] = None) -> bool:
        return self._state_store.delete_user(user_id, pool_id) if pool_id else self._state_store.delete_user(user_id)

    def pick_next(self, pool_id: Optional[str] = None) -> Optional[User]:
        return self._state_store.pick_next(pool_id) if pool_id else self._state_store.pick_next()

    def reset_round(self, pool_id: Optional[str] = None) -> None:
        self._state_store.reset_round(pool_id) if pool_id else self._state_store.reset_round()
