import random
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional
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


class MemoryStore:
    def __init__(self):
        self._lock = Lock()
        self._users: Dict[str, User] = {}
        self._last_picked_id: Optional[str] = None
        self._last_picked_user: Optional[User] = None
        self._seed_default_users()

    def _seed_default_users(self):
        for name in ["Mario", "Luigi", "Yoshi"]:
            uid = str(uuid.uuid4())[:8]
            self._users[uid] = User(id=uid, name=name)

    def get_state(self) -> StateResponse:
        with self._lock:
            return StateResponse(
                users=list(self._users.values()),
                last_picked_user=self._last_picked_user
            )

    def add_user(self, name: str) -> User:
        with self._lock:
            uid = str(uuid.uuid4())[:8]
            user = User(id=uid, name=name)
            self._users[uid] = user
            return user

    def toggle_check(self, user_id: str, checked: bool) -> Optional[User]:
        with self._lock:
            if user_id in self._users:
                self._users[user_id].checked = checked
                return self._users[user_id]
            return None

    def delete_user(self, user_id: str) -> bool:
        with self._lock:
            if self._last_picked_id == user_id:
                self._last_picked_id = None
                self._last_picked_user = None
            return self._users.pop(user_id, None) is not None

    def pick_next(self) -> Optional[User]:
        with self._lock:
            checked_users = [u for u in self._users.values() if u.checked]
            if not checked_users:
                return None

            eligible = [u for u in checked_users if not u.pickedThisRound]

            # Auto-reset round if all checked users have been picked
            if not eligible:
                for u in checked_users:
                    u.pickedThisRound = False
                eligible = checked_users

            # Prevent consecutive selection
            candidate_pool = eligible
            if self._last_picked_id and len(checked_users) > 1:
                filtered = [u for u in eligible if u.id != self._last_picked_id]
                if filtered:
                    candidate_pool = filtered

            chosen = random.choice(candidate_pool)
            chosen.pickedThisRound = True
            chosen.picked_at = datetime.now(timezone.utc).isoformat()
            
            self._last_picked_id = chosen.id
            self._last_picked_user = chosen
            return chosen

    def reset_round(self):
        with self._lock:
            for u in self._users.values():
                u.pickedThisRound = False


store = MemoryStore()