from typing import List, Optional

from pydantic import BaseModel


class Room(BaseModel):
    id: str
    name: str
    created_at: Optional[str] = None
    slack_channel_id: Optional[str] = None


class TaskPool(BaseModel):
    id: str
    name: str
    created_at: Optional[str] = None


class CreateRoomRequest(BaseModel):
    name: str


class CreatePoolRequest(BaseModel):
    name: str


class UpdateSlackChannelRequest(BaseModel):
    channel_id: str = ""


class RoomResponse(Room):
    share_url: str


class AdminRoomSummary(BaseModel):
    id: str
    name: str
    user_count: int
    last_picked: Optional[str] = None


class AdminDashboardData(BaseModel):
    active_sessions: int
    rooms: List[AdminRoomSummary]
