import asyncio
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.store import StateResponse, User, store

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(
    title="pickerPro®",
    description="Thread-safe, in-memory round-robin user picker API.",
    version="1.1.0",
)


class CreateUserRequest(BaseModel):
    name: str


class ToggleUserRequest(BaseModel):
    checked: bool


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/state", response_model=StateResponse)
def get_state():
    return store.get_state()


@app.post("/api/users", response_model=User)
def create_user(payload: CreateUserRequest):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    return store.add_user(name)


@app.patch("/api/users/{user_id}", response_model=User)
def toggle_user(user_id: str, payload: ToggleUserRequest):
    user = store.toggle_check(user_id, payload.checked)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.delete("/api/users/{user_id}")
def delete_user(user_id: str):
    if not store.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success"}


@app.post("/api/pick", response_model=Optional[User])
async def pick_user():
    await asyncio.sleep(1.2)
    return store.pick_next()


@app.post("/api/reset")
def reset_round():
    store.reset_round()
    return {"status": "success"}