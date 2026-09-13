import random
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Optional

from app.schemas.users import StateResponse, User


class PickerService:
    """Thread-safe in-memory state and fairness rules for one room."""

    def __init__(self, seed_defaults: bool = False):
        self._lock = Lock()
        self._users: Dict[str, User] = {}
        self._last_picked_id: Optional[str] = None
        self._last_picked_user: Optional[User] = None
        if seed_defaults:
            self._seed_default_users()

    def _seed_default_users(self) -> None:
        for name in ("Mario", "Luigi", "Yoshi"):
            self.add_user(name)

    def get_state(self) -> StateResponse:
        with self._lock:
            return StateResponse(users=list(self._users.values()), last_picked_user=self._last_picked_user)

    def add_user(self, name: str) -> User:
        with self._lock:
            user = User(id=uuid.uuid4().hex[:8], name=name)
            self._users[user.id] = user
            return user

    def toggle_check(self, user_id: str, checked: bool) -> Optional[User]:
        with self._lock:
            user = self._users.get(user_id)
            if user:
                user.checked = checked
            return user

    def delete_user(self, user_id: str) -> bool:
        with self._lock:
            if self._last_picked_id == user_id:
                self._last_picked_id = None
                self._last_picked_user = None
            return self._users.pop(user_id, None) is not None

    def pick_next(self) -> Optional[User]:
        with self._lock:
            checked_users = [user for user in self._users.values() if user.checked]
            if not checked_users:
                return None

            eligible = [user for user in checked_users if not user.pickedThisRound]
            if not eligible:
                for user in checked_users:
                    user.pickedThisRound = False
                eligible = checked_users

            candidates = eligible
            if self._last_picked_id and len(checked_users) > 1:
                without_last = [user for user in eligible if user.id != self._last_picked_id]
                if without_last:
                    candidates = without_last

            chosen = random.choice(candidates)
            chosen.pickedThisRound = True
            chosen.picked_at = datetime.now(timezone.utc).isoformat()
            self._last_picked_id = chosen.id
            self._last_picked_user = chosen
            return chosen

    def reset_round(self) -> None:
        with self._lock:
            for user in self._users.values():
                user.pickedThisRound = False
