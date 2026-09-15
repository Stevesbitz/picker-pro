from __future__ import annotations

import os
import random
import uuid
from datetime import datetime, timezone
from functools import wraps
from threading import Lock, RLock
from typing import Dict, List, Optional

from sqlalchemy import Boolean, Column, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.schemas.rooms import AdminDashboardData, AdminRoomSummary, Room, TaskPool
from app.schemas.users import StateResponse, User
from app.store.base import BaseRoomStore

DEFAULT_POOL_ID = "default"


def synchronized(method):
    @wraps(method)
    def locked_method(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return locked_method


class BaseDB(DeclarativeBase):
    pass


class DbRoom(BaseDB):
    __tablename__ = "rooms"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    slack_channel_id = Column(String, nullable=True)


class DbPool(BaseDB):
    __tablename__ = "task_pools"

    id = Column(String, primary_key=True)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    last_picked_user_id = Column(String, nullable=True)


class DbUser(BaseDB):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    pool_id = Column(String, ForeignKey("task_pools.id"), nullable=False)
    name = Column(String, nullable=False)
    checked = Column(Boolean, default=True, nullable=False)
    pickedThisRound = Column(Boolean, default=False, nullable=False)
    picked_at = Column(String, nullable=True)
    is_ooo = Column(Boolean, default=False, nullable=False)


class DatabaseStateStore:
    def __init__(self, session_factory, room_id: str, lock: Optional[RLock] = None):
        self._session_factory = session_factory
        self.room_id = room_id
        self._lock = lock or RLock()

    def _user_to_model(self, row: DbUser) -> User:
        return User(
            id=row.id,
            name=row.name,
            checked=row.checked,
            pickedThisRound=row.pickedThisRound,
            picked_at=row.picked_at,
            is_ooo=row.is_ooo,
            pool_id=row.pool_id,
        )

    @synchronized
    def get_state(self, pool_id: Optional[str] = None) -> StateResponse:
        session: Session = self._session_factory()
        try:
            target_pool = pool_id or DEFAULT_POOL_ID
            rows = session.query(DbUser).filter(DbUser.room_id == self.room_id, DbUser.pool_id == target_pool).all()
            last_picked = None
            pool_row = session.query(DbPool).filter(DbPool.room_id == self.room_id, DbPool.id == target_pool).one_or_none()
            if pool_row and pool_row.last_picked_user_id:
                last_user = session.query(DbUser).filter(DbUser.room_id == self.room_id, DbUser.id == pool_row.last_picked_user_id).one_or_none()
                if last_user:
                    last_picked = self._user_to_model(last_user)
            return StateResponse(users=[self._user_to_model(row) for row in rows], last_picked_user=last_picked, pool_id=target_pool)
        finally:
            session.close()

    @synchronized
    def add_user(self, name: str, pool_id: Optional[str] = None) -> User:
        session: Session = self._session_factory()
        try:
            target_pool = pool_id or DEFAULT_POOL_ID
            user = DbUser(
                id=uuid.uuid4().hex[:8],
                name=name,
                room_id=self.room_id,
                pool_id=target_pool,
                checked=True,
                pickedThisRound=False,
                is_ooo=False,
            )
            session.add(user)
            session.commit()
            return self._user_to_model(user)
        finally:
            session.close()

    @synchronized
    def toggle_check(self, user_id: str, checked: bool, pool_id: Optional[str] = None) -> Optional[User]:
        session: Session = self._session_factory()
        try:
            target_pool = pool_id or DEFAULT_POOL_ID
            user = session.query(DbUser).filter(DbUser.id == user_id, DbUser.room_id == self.room_id, DbUser.pool_id == target_pool).one_or_none()
            if not user:
                return None
            user.checked = checked
            session.commit()
            return self._user_to_model(user)
        finally:
            session.close()

    @synchronized
    def toggle_ooo(self, user_id: str, is_ooo: bool, pool_id: Optional[str] = None) -> Optional[User]:
        session: Session = self._session_factory()
        try:
            target_pool = pool_id or DEFAULT_POOL_ID
            user = session.query(DbUser).filter(DbUser.id == user_id, DbUser.room_id == self.room_id, DbUser.pool_id == target_pool).one_or_none()
            if not user:
                return None
            user.is_ooo = is_ooo
            session.commit()
            return self._user_to_model(user)
        finally:
            session.close()

    @synchronized
    def delete_user(self, user_id: str, pool_id: Optional[str] = None) -> bool:
        session: Session = self._session_factory()
        try:
            target_pool = pool_id or DEFAULT_POOL_ID
            user = session.query(DbUser).filter(DbUser.id == user_id, DbUser.room_id == self.room_id, DbUser.pool_id == target_pool).one_or_none()
            if not user:
                return False
            pool = session.query(DbPool).filter(DbPool.room_id == self.room_id, DbPool.id == user.pool_id).one_or_none()
            if pool and pool.last_picked_user_id == user.id:
                pool.last_picked_user_id = None
            session.delete(user)
            session.commit()
            return True
        finally:
            session.close()

    @synchronized
    def pick_next(self, pool_id: Optional[str] = None) -> Optional[User]:
        session: Session = self._session_factory()
        try:
            target_pool = pool_id or DEFAULT_POOL_ID
            checked_users = session.query(DbUser).filter(
                DbUser.room_id == self.room_id,
                DbUser.pool_id == target_pool,
                DbUser.checked.is_(True),
                DbUser.is_ooo.is_(False),
            ).all()
            if not checked_users:
                return None

            eligible = [user for user in checked_users if not user.pickedThisRound]
            if not eligible:
                for user in checked_users:
                    user.pickedThisRound = False
                eligible = checked_users

            pool = session.query(DbPool).filter(DbPool.room_id == self.room_id, DbPool.id == target_pool).one_or_none()
            last_picked_id = pool.last_picked_user_id if pool else None
            candidate_pool = eligible
            if last_picked_id and len(checked_users) > 1:
                filtered = [user for user in eligible if user.id != last_picked_id]
                if filtered:
                    candidate_pool = filtered

            chosen = random.choice(candidate_pool)
            chosen.pickedThisRound = True
            chosen.picked_at = datetime.now(timezone.utc).isoformat()
            if pool:
                pool.last_picked_user_id = chosen.id
            session.commit()
            return self._user_to_model(chosen)
        finally:
            session.close()

    @synchronized
    def reset_round(self, pool_id: Optional[str] = None):
        session: Session = self._session_factory()
        try:
            target_pool = pool_id or DEFAULT_POOL_ID
            users = session.query(DbUser).filter(DbUser.room_id == self.room_id, DbUser.pool_id == target_pool).all()
            for user in users:
                user.pickedThisRound = False
            session.commit()
        finally:
            session.close()


class DatabaseRoomStore(BaseRoomStore):
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL is required for DatabaseRoomStore")

        self.engine = create_engine(self.database_url, future=True)
        BaseDB.metadata.create_all(self.engine)
        self._session_factory = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        self._locks: Dict[str, RLock] = {}
        self._locks_lock = Lock()

    def _lock_for_room(self, room_id: str) -> RLock:
        with self._locks_lock:
            lock = self._locks.get(room_id)
            if lock is None:
                lock = RLock()
                self._locks[room_id] = lock
            return lock

    def create_room(self, name: str) -> Room:
        room_id = uuid.uuid4().hex[:8]
        room = Room(id=room_id, name=name, created_at=datetime.now(timezone.utc).isoformat())
        session: Session = self._session_factory()
        try:
            session.add(DbRoom(id=room.id, name=room.name, created_at=room.created_at))
            session.add(DbPool(id=DEFAULT_POOL_ID, room_id=room.id, name="Default", created_at=room.created_at, last_picked_user_id=None))
            session.commit()
            return room
        finally:
            session.close()

    def get_room(self, room_id: str) -> Optional[Room]:
        session: Session = self._session_factory()
        try:
            row = session.query(DbRoom).filter(DbRoom.id == room_id).one_or_none()
            if not row:
                return None
            return Room(id=row.id, name=row.name, created_at=row.created_at, slack_channel_id=row.slack_channel_id)
        finally:
            session.close()

    def save_room(self, room: Room) -> Room:
        session: Session = self._session_factory()
        try:
            existing = session.query(DbRoom).filter(DbRoom.id == room.id).one_or_none()
            if existing is None:
                session.add(DbRoom(id=room.id, name=room.name, created_at=room.created_at or datetime.now(timezone.utc).isoformat()))
            else:
                existing.name = room.name
                existing.slack_channel_id = room.slack_channel_id
                if room.created_at:
                    existing.created_at = room.created_at
            session.commit()
            return room
        finally:
            session.close()

    def delete_room(self, room_id: str) -> bool:
        session: Session = self._session_factory()
        try:
            room = session.query(DbRoom).filter(DbRoom.id == room_id).one_or_none()
            if room is None:
                return False
            session.query(DbUser).filter(DbUser.room_id == room_id).delete()
            session.query(DbPool).filter(DbPool.room_id == room_id).delete()
            session.delete(room)
            session.commit()
            return True
        finally:
            session.close()

    def list_rooms(self) -> List[Room]:
        session: Session = self._session_factory()
        try:
            rows = session.query(DbRoom).all()
            return [Room(id=row.id, name=row.name, created_at=row.created_at, slack_channel_id=row.slack_channel_id) for row in rows]
        finally:
            session.close()

    def get_state_store(self, room_id: str):
        return DatabaseStateStore(self._session_factory, room_id, self._lock_for_room(room_id))

    def create_pool(self, room_id: str, name: str) -> TaskPool:
        session: Session = self._session_factory()
        try:
            pool_id = uuid.uuid4().hex[:8]
            created_at = datetime.now(timezone.utc).isoformat()
            pool = DbPool(id=pool_id, room_id=room_id, name=name, created_at=created_at)
            session.add(pool)
            session.commit()
            return TaskPool(id=pool.id, name=pool.name, created_at=pool.created_at)
        finally:
            session.close()

    def list_pools(self, room_id: str) -> List[TaskPool]:
        session: Session = self._session_factory()
        try:
            rows = session.query(DbPool).filter(DbPool.room_id == room_id).all()
            return [TaskPool(id=row.id, name=row.name, created_at=row.created_at) for row in rows]
        finally:
            session.close()

    def get_admin_dashboard_data(self):
        session: Session = self._session_factory()
        try:
            rooms = session.query(DbRoom).all()
            summaries = []
            for room in rooms:
                pool = session.query(DbPool).filter(DbPool.room_id == room.id, DbPool.id == DEFAULT_POOL_ID).one_or_none()
                last_name = None
                if pool and pool.last_picked_user_id:
                    user = session.query(DbUser).filter(DbUser.id == pool.last_picked_user_id, DbUser.room_id == room.id).one_or_none()
                    if user:
                        last_name = user.name
                user_count = session.query(DbUser).filter(DbUser.room_id == room.id).count()
                summaries.append(AdminRoomSummary(id=room.id, name=room.name, user_count=user_count, last_picked=last_name))
            return AdminDashboardData(active_sessions=len(summaries), rooms=summaries)
        finally:
            session.close()
