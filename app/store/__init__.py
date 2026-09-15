import logging
import os
import random

from app.schemas.rooms import AdminDashboardData, AdminRoomSummary, Room, TaskPool
from app.schemas.users import StateResponse, User
from app.store.memory import DEFAULT_POOL_ID, MemoryRoomStore, MemoryStore, RoomStore

logger = logging.getLogger(__name__)

try:
    from app.store.db import DatabaseRoomStore
except Exception:  # pragma: no cover - optional dependency protection
    DatabaseRoomStore = None


if DatabaseRoomStore is not None:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            room_store = DatabaseRoomStore(database_url=database_url)
        except Exception:
            logger.warning("Database connection failed; falling back to in-memory room store.", exc_info=True)
            room_store = MemoryRoomStore()
    else:
        logger.warning("DATABASE_URL not set; using in-memory room store.")
        room_store = MemoryRoomStore()
else:
    logger.warning("SQLAlchemy unavailable; using in-memory room store.")
    room_store = MemoryRoomStore()

__all__ = [
    "DEFAULT_POOL_ID",
    "AdminDashboardData",
    "AdminRoomSummary",
    "MemoryStore",
    "MemoryRoomStore",
    "Room",
    "RoomStore",
    "StateResponse",
    "TaskPool",
    "User",
    "random",
    "room_store",
]
