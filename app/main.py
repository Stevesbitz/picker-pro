import asyncio
import os
from collections import defaultdict, deque
from math import ceil
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Deque, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.store import AdminDashboardData, Room, StateResponse, User, room_store

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(
    title="pickerPro®",
    description="Thread-safe, in-memory round-robin user picker API with Admin management.",
    version="1.2.0",
)

# Mount static folder
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

ADMIN_PASSKEY = os.getenv("ADMIN_PASSKEY", "admin123")
ADMIN_COOKIE_KEY = "admin_auth_session"

RATE_LIMIT_REQUESTS = 120
RATE_LIMIT_WINDOW_SECONDS = 60


class ApiRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = Lock()
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

    def retry_after(self, client_id: str, now: Optional[float] = None) -> Optional[int]:
        current_time = monotonic() if now is None else now
        with self._lock:
            requests = self._requests[client_id]
            cutoff = current_time - self.window_seconds
            while requests and requests[0] <= cutoff:
                requests.popleft()

            if len(requests) >= self.max_requests:
                return max(1, ceil(self.window_seconds - (current_time - requests[0])))

            requests.append(current_time)
            return None


api_rate_limiter = ApiRateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)


@app.middleware("http")
async def rate_limit_api_requests(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        client_id = request.client.host if request.client else "unknown"
        retry_after = api_rate_limiter.retry_after(client_id)
        if retry_after is not None:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again shortly."},
                headers={"Retry-After": str(retry_after)},
            )
    return await call_next(request)


class CreateUserRequest(BaseModel):
    name: str


class CreateRoomRequest(BaseModel):
    name: str


class AdminLoginRequest(BaseModel):
    passkey: str


class RoomResponse(Room):
    share_url: str


class ToggleUserRequest(BaseModel):
    checked: bool


def is_authenticated_admin(request: Request) -> bool:
    return request.cookies.get(ADMIN_COOKIE_KEY) == ADMIN_PASSKEY


def is_api_request(request: Request) -> bool:
    return request.url.path.startswith("/api/")


def error_page(request: Request, status_code: int, title: str, message: str):
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={"status_code": status_code, "title": title, "message": message},
        status_code=status_code,
    )

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions without exposing internal details."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions without exposing internal details."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if is_api_request(request):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    if exc.status_code == 404:
        return error_page(request, 404, "Page not found", "The page or team room you requested does not exist.")
    return error_page(request, exc.status_code, "Something went wrong", str(exc.detail))


# --- Page Routing ---

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "room": None,
            "is_admin": is_authenticated_admin(request),
            "is_login_page": False,
        },
    )


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    if is_authenticated_admin(request):
        return RedirectResponse(url="/admin")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "room": None,
            "is_admin": False,
            "is_login_page": True,
        },
    )


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard_page(request: Request):
    if not is_authenticated_admin(request):
        return RedirectResponse(url="/admin/login")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "room": None,
            "is_admin": True,
            "is_login_page": False,
        },
    )


@app.get("/rooms/{room_id}", response_class=HTMLResponse, name="read_room")
def read_room(request: Request, room_id: str):
    room = room_store.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "room": room,
            "is_admin": is_authenticated_admin(request),
            "is_login_page": False,
        },
    )


def get_room_state_or_404(room_id: str):
    state_store = room_store.get_state_store(room_id)
    if not state_store:
        raise HTTPException(status_code=404, detail="Room not found")
    return state_store


# --- Admin API Routes ---

@app.post("/api/admin/login")
def admin_login(payload: AdminLoginRequest, response: Response):
    if payload.passkey != ADMIN_PASSKEY:
        raise HTTPException(status_code=401, detail="Invalid admin passkey")
    response.set_cookie(key=ADMIN_COOKIE_KEY, value=ADMIN_PASSKEY, httponly=True)
    return {"status": "success"}


@app.post("/api/admin/logout")
def admin_logout(response: Response):
    response.delete_cookie(key=ADMIN_COOKIE_KEY)
    return {"status": "success"}


@app.get("/api/admin/sessions", response_model=AdminDashboardData)
def get_admin_sessions(request: Request):
    if not is_authenticated_admin(request):
        raise HTTPException(status_code=401, detail="Unauthorized admin access")
    return room_store.get_admin_dashboard_data()


# --- User API Routes ---

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

    if candidate_count > 1:
        await asyncio.sleep(1.2)
    return state_store.pick_next()


@app.post("/api/rooms/{room_id}/reset")
def reset_round(room_id: str):
    get_room_state_or_404(room_id).reset_round()
    return {"status": "success"}

