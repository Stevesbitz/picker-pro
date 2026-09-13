import asyncio
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.store import User, store

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(
    title="Random User Picker",
    description="Thread-safe, in-memory round-robin user picker API.",
    version="1.0.0",
)


class CreateUserRequest(BaseModel):
    name: str


class ToggleUserRequest(BaseModel):
    checked: bool


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/users", response_model=List[User])
def get_users():
    return store.get_all()


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
    # Simulate a brief delay to allow the client-side picking animation to run
    await asyncio.sleep(1.5)
    return store.pick_next()


@app.post("/api/reset")
def reset_round():
    store.reset_round()
    return {"status": "success"}