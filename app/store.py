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


class Room(BaseModel):
    id: str
    name: str


class AdminRoomSummary(BaseModel):
    id: str
    name: str
    user_count: int
    last_picked: Optional[str] = None


class AdminDashboardData(BaseModel):
    active_sessions: int
    rooms: List[AdminRoomSummary]


class MemoryStore:
    def __init__(self, seed_defaults: bool = True):
        self._lock = Lock()
        self._users: Dict[str, User] = {}
        self._last_picked_id: Optional[str] = None
        self._last_picked_user: Optional[User] = None
        if seed_defaults:
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


class RoomStore:
    """Owns a separate picker state for every shareable team room."""

    def __init__(self):
        self._lock = Lock()
        self._rooms: Dict[str, Room] = {}
        self._room_states: Dict[str, MemoryStore] = {}

    def create_room(self, name: str) -> Room:
        with self._lock:
            room_id = uuid.uuid4().hex[:8]
            room = Room(id=room_id, name=name)
            self._rooms[room_id] = room
            self._room_states[room_id] = MemoryStore(seed_defaults=False)
            return room

    def get_room(self, room_id: str) -> Optional[Room]:
        with self._lock:
            return self._rooms.get(room_id)

    def get_state_store(self, room_id: str) -> Optional[MemoryStore]:
        with self._lock:
            return self._room_states.get(room_id)

    def get_admin_dashboard_data(self) -> AdminDashboardData:
        with self._lock:
            summaries = []
            for room_id, room in self._rooms.items():
                store = self._room_states[room_id]
                state = store.get_state()
                last_name = state.last_picked_user.name if state.last_picked_user else None
                summaries.append(
                    AdminRoomSummary(
                        id=room_id,
                        name=room.name,
                        user_count=len(state.users),
                        last_picked=last_name,
                    )
                )
            return AdminDashboardData(
                active_sessions=len(summaries),
                rooms=summaries,
            )


room_store = RoomStore()