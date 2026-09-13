import asyncio
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
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


def is_api_request(request: Request) -> bool:
    return request.url.path.startswith("/api/")


def error_page(request: Request, status_code: int, title: str, message: str):
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={"status_code": status_code, "title": title, "message": message},
        status_code=status_code,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if is_api_request(request):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    if exc.status_code == 404:
        return error_page(request, 404, "Page not found", "The page or team room you requested does not exist.")
    return error_page(request, exc.status_code, "Something went wrong", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if is_api_request(request):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})
    return error_page(request, 400, "Invalid request", "Please check your details and try again.")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if is_api_request(request):
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    return error_page(request, 500, "Unexpected error", "Please try again in a moment.")


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
    state_store = get_room_state_or_404(room_id)
    state = state_store.get_state()
    checked_users = [user for user in state.users if user.checked]
    remaining_users = [user for user in checked_users if not user.pickedThisRound]
    candidate_count = len(remaining_users) or len(checked_users)

    # The delay only supports the shuffle animation; skip it for a guaranteed pick.
    if candidate_count > 1:
        await asyncio.sleep(1.2)
    return state_store.pick_next()


@app.post("/api/rooms/{room_id}/reset")
def reset_round(room_id: str):
    get_room_state_or_404(room_id).reset_round()
    return {"status": "success"}
