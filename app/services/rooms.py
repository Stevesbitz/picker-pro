import uuid
from threading import Lock
from typing import Dict, Optional

from app.schemas.rooms import Room
from app.services.picker import PickerService


class RoomService:
    """Creates rooms and owns their isolated picker services."""

    def __init__(self):
        self._lock = Lock()
        self._rooms: Dict[str, Room] = {}
        self._pickers: Dict[str, PickerService] = {}

    def create_room(self, name: str) -> Room:
        with self._lock:
            room = Room(id=uuid.uuid4().hex, name=name)
            self._rooms[room.id] = room
            self._pickers[room.id] = PickerService()
            return room

    def get_room(self, room_id: str) -> Optional[Room]:
        with self._lock:
            return self._rooms.get(room_id)

    def get_picker(self, room_id: str) -> Optional[PickerService]:
        with self._lock:
            return self._pickers.get(room_id)
