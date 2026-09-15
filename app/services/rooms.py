from typing import List, Optional

from app.schemas.rooms import Room, TaskPool
from app.services.picker import PickerService
from app.schemas.rooms import AdminDashboardData
from app.store.base import BaseRoomStore, StateStore


class RoomService:
    """Application service for room and task-pool operations."""

    def __init__(self, room_store: BaseRoomStore):
        self._room_store = room_store

    def create_room(self, name: str) -> Room:
        return self._room_store.create_room(name)

    def get_room(self, room_id: str) -> Optional[Room]:
        return self._room_store.get_room(room_id)

    def save_room(self, room: Room) -> Room:
        return self._room_store.save_room(room)

    def get_picker(self, room_id: str) -> Optional[PickerService]:
        state_store = self._room_store.get_state_store(room_id)
        return PickerService(state_store) if state_store else None

    def get_state_store(self, room_id: str) -> Optional[StateStore]:
        return self._room_store.get_state_store(room_id)

    def get_admin_dashboard_data(self) -> AdminDashboardData:
        return self._room_store.get_admin_dashboard_data()

    def create_pool(self, room_id: str, name: str) -> TaskPool:
        return self._room_store.create_pool(room_id, name)

    def list_pools(self, room_id: str) -> List[TaskPool]:
        return self._room_store.list_pools(room_id)
