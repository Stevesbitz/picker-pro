import asyncio
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.store import Room, StateResponse, User, room_store

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(
    title="pickerPro®",
    description="Thread-safe, in-memory round-robin user picker API.",
    version="1.1.0",
)


class CreateUserRequest(BaseModel):
    name: str


class CreateRoomRequest(BaseModel):
    name: str


class RoomResponse(Room):
    share_url: str


class ToggleUserRequest(BaseModel):
    checked: bool


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"room": None})


@app.get("/rooms/{room_id}", response_class=HTMLResponse, name="read_room")
def read_room(request: Request, room_id: str):
    room = room_store.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return templates.TemplateResponse(request=request, name="index.html", context={"room": room})


def get_room_state_or_404(room_id: str):
    state_store = room_store.get_state_store(room_id)
    if not state_store:
        raise HTTPException(status_code=404, detail="Room not found")
    return state_store


@app.post("/api/rooms", response_model=RoomResponse, status_code=201)
def create_room(request: Request, payload: CreateRoomRequest):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Team name cannot be empty")
    room = room_store.create_room(name)
    return RoomResponse(
        **room.model_dump(), share_url=str(request.url_for("read_room", room_id=room.id))
    )


@app.get("/api/rooms/{room_id}/state", response_model=StateResponse)
def get_state(room_id: str):
    return get_room_state_or_404(room_id).get_state()


@app.post("/api/rooms/{room_id}/users", response_model=User)
def create_user(room_id: str, payload: CreateUserRequest):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    return get_room_state_or_404(room_id).add_user(name)


@app.patch("/api/rooms/{room_id}/users/{user_id}", response_model=User)
def toggle_user(room_id: str, user_id: str, payload: ToggleUserRequest):
    user = get_room_state_or_404(room_id).toggle_check(user_id, payload.checked)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.delete("/api/rooms/{room_id}/users/{user_id}")
def delete_user(room_id: str, user_id: str):
    if not get_room_state_or_404(room_id).delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success"}


@app.post("/api/rooms/{room_id}/pick", response_model=Optional[User])
async def pick_user(room_id: str):
    await asyncio.sleep(1.2)
    return get_room_state_or_404(room_id).pick_next()


@app.post("/api/rooms/{room_id}/reset")
def reset_round(room_id: str):
    get_room_state_or_404(room_id).reset_round()
    return {"status": "success"}
