from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional

from app.schemas.rooms import Room, TaskPool
from app.schemas.users import StateResponse, User
from app.store.base import BaseRoomStore

DEFAULT_POOL_ID = "default"


class MemoryStore:
    """Per-room, in-memory picker state tracking users and selection rounds."""

    def __init__(self, seed_defaults: bool = True):
        self._lock = Lock()
        self._users: Dict[str, User] = {}
        self._last_picked_id: Optional[str] = None
        self._last_picked_user: Optional[User] = None
        self._last_picked_id_by_pool: Dict[str, Optional[str]] = {}
        self._last_picked_user_by_pool: Dict[str, Optional[User]] = {}
        if seed_defaults:
            self._seed_default_users()

    def _seed_default_users(self):
        for name in ["Mario", "Luigi", "Yoshi"]:
            self.add_user(name, pool_id=DEFAULT_POOL_ID)

    def get_state(self, pool_id: Optional[str] = None) -> StateResponse:
        with self._lock:
            target_pool = pool_id or DEFAULT_POOL_ID
            users = [user for user in self._users.values() if user.pool_id == target_pool]
            last_user = self._last_picked_user_by_pool.get(target_pool)
            if target_pool == DEFAULT_POOL_ID and last_user is None and self._last_picked_user is not None:
                last_user = self._last_picked_user
            if target_pool == DEFAULT_POOL_ID:
                self._last_picked_id = self._last_picked_id_by_pool.get(target_pool) or self._last_picked_id
                self._last_picked_user = last_user
            return StateResponse(
                users=users,
                last_picked_user=last_user,
                pool_id=target_pool,
            )

    def add_user(self, name: str, pool_id: Optional[str] = None) -> User:
        with self._lock:
            target_pool = pool_id or DEFAULT_POOL_ID
            user = User(
                id=str(uuid.uuid4())[:8],
                name=name,
                checked=True,
                pickedThisRound=False,
                pool_id=target_pool,
            )
            self._users[user.id] = user
            return user

    def toggle_check(self, user_id: str, checked: bool, pool_id: Optional[str] = None) -> Optional[User]:
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return None
            if pool_id is not None and user.pool_id != pool_id:
                return None
            user.checked = checked
            return user

    def toggle_ooo(self, user_id: str, is_ooo: bool, pool_id: Optional[str] = None) -> Optional[User]:
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return None
            if pool_id is not None and user.pool_id != pool_id:
                return None
            user.is_ooo = is_ooo
            return user

    def delete_user(self, user_id: str, pool_id: Optional[str] = None) -> bool:
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return False
            if pool_id is not None and user.pool_id != pool_id:
                return False
            if self._last_picked_id_by_pool.get(user.pool_id) == user_id:
                self._last_picked_id_by_pool[user.pool_id] = None
                self._last_picked_user_by_pool[user.pool_id] = None
            if self._last_picked_id == user_id:
                self._last_picked_id = None
                self._last_picked_user = None
            del self._users[user_id]
            return True

    def pick_next(self, pool_id: Optional[str] = None) -> Optional[User]:
        with self._lock:
            target_pool = pool_id or DEFAULT_POOL_ID
            checked_users = [
                user for user in self._users.values() if user.pool_id == target_pool and user.checked and not user.is_ooo
            ]
            if not checked_users:
                return None

            eligible = [user for user in checked_users if not user.pickedThisRound]
            if not eligible:
                for user in checked_users:
                    user.pickedThisRound = False
                eligible = checked_users

            candidate_pool = eligible
            last_picked_id = self._last_picked_id_by_pool.get(target_pool)
            if last_picked_id is None and target_pool == DEFAULT_POOL_ID:
                last_picked_id = self._last_picked_id
            if last_picked_id and len(checked_users) > 1:
                filtered = [user for user in eligible if user.id != last_picked_id]
                if filtered:
                    candidate_pool = filtered

            chosen = random.choice(candidate_pool)
            chosen.pickedThisRound = True
            chosen.picked_at = datetime.now(timezone.utc).isoformat()
            self._last_picked_id_by_pool[target_pool] = chosen.id
            self._last_picked_user_by_pool[target_pool] = chosen
            if target_pool == DEFAULT_POOL_ID:
                self._last_picked_id = chosen.id
                self._last_picked_user = chosen
            return chosen

    def reset_round(self, pool_id: Optional[str] = None):
        with self._lock:
            target_pool = pool_id or DEFAULT_POOL_ID
            for user in self._users.values():
                if user.pool_id == target_pool:
                    user.pickedThisRound = False
            if target_pool == DEFAULT_POOL_ID:
                legacy_last_id = self._last_picked_id_by_pool.get(target_pool)
                if legacy_last_id is None and self._last_picked_id is not None:
                    self._last_picked_id_by_pool[target_pool] = self._last_picked_id
                    self._last_picked_user_by_pool[target_pool] = self._last_picked_user
                self._last_picked_id = self._last_picked_id_by_pool.get(target_pool) or self._last_picked_id
                self._last_picked_user = self._last_picked_user_by_pool.get(target_pool) or self._last_picked_user


class MemoryRoomStore(BaseRoomStore):
    """Stores room state and a default task pool for each room."""

    def __init__(self):
        self._lock = Lock()
        self._rooms: Dict[str, Room] = {}
        self._room_states: Dict[str, MemoryStore] = {}
        self._room_pools: Dict[str, Dict[str, TaskPool]] = {}

    def create_room(self, name: str) -> Room:
        with self._lock:
            room_id = uuid.uuid4().hex[:8]
            room = Room(id=room_id, name=name, created_at=datetime.now(timezone.utc).isoformat())
            self._rooms[room_id] = room
            self._room_states[room_id] = MemoryStore(seed_defaults=False)
            self._room_pools[room_id] = {
                DEFAULT_POOL_ID: TaskPool(id=DEFAULT_POOL_ID, name="Default", created_at=room.created_at)
            }
            return room

    def get_room(self, room_id: str) -> Optional[Room]:
        with self._lock:
            return self._rooms.get(room_id)

    def save_room(self, room: Room) -> Room:
        with self._lock:
            self._rooms[room.id] = room
            self._room_states.setdefault(room.id, MemoryStore(seed_defaults=False))
            if room.id not in self._room_pools:
                self._room_pools[room.id] = {
                    DEFAULT_POOL_ID: TaskPool(id=DEFAULT_POOL_ID, name="Default", created_at=room.created_at)
                }
            return room

    def delete_room(self, room_id: str) -> bool:
        with self._lock:
            removed = self._rooms.pop(room_id, None) is not None
            self._room_states.pop(room_id, None)
            self._room_pools.pop(room_id, None)
            return removed

    def list_rooms(self) -> List[Room]:
        with self._lock:
            return list(self._rooms.values())

    def get_state_store(self, room_id: str) -> Optional[MemoryStore]:
        with self._lock:
            return self._room_states.get(room_id)

    def create_pool(self, room_id: str, name: str) -> TaskPool:
        with self._lock:
            pools = self._room_pools.setdefault(room_id, {})
            pool_id = uuid.uuid4().hex[:8]
            pool = TaskPool(id=pool_id, name=name, created_at=datetime.now(timezone.utc).isoformat())
            pools[pool_id] = pool
            if room_id not in self._room_states:
                self._room_states[room_id] = MemoryStore(seed_defaults=False)
            return pool

    def list_pools(self, room_id: str) -> List[TaskPool]:
        with self._lock:
            return list(self._room_pools.get(room_id, {}).values())

    def get_admin_dashboard_data(self):
        from app.schemas.rooms import AdminDashboardData, AdminRoomSummary

        with self._lock:
            summaries = []
            for room_id, room in self._rooms.items():
                state = self._room_states.get(room_id)
                room_users = state.get_state().users if state else []
                last_name = None
                if state:
                    pool_state = state.get_state(pool_id=DEFAULT_POOL_ID)
                    if pool_state.last_picked_user:
                        last_name = pool_state.last_picked_user.name
                summaries.append(
                    AdminRoomSummary(
                        id=room_id,
                        name=room.name,
                        user_count=len(room_users),
                        last_picked=last_name,
                    )
                )
            return AdminDashboardData(active_sessions=len(summaries), rooms=summaries)


RoomStore = MemoryRoomStore
