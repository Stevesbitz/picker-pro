from pydantic import BaseModel


class Room(BaseModel):
    id: str
    name: str


class CreateRoomRequest(BaseModel):
    name: str


class RoomResponse(Room):
    share_url: str
