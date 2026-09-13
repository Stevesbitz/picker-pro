# Random User Picker

A lightweight, high-performance web application for fair, round-robin random selection. Built using FastAPI and responsive HTML5/CSS3, state is synced server-side across all active clients in real-time.

---

## Key Features

* **Round-Robin Fair Picking:** Ensures every active user gets picked exactly once before the round resets automatically.
* **Thread-Safe In-Memory Store:** Shared application state across active sessions backed by a thread-safe Python engine.
* **Lightweight REST API:** Modular backend endpoints built with FastAPI and validated using Pydantic.
* **Zero Dependencies Frontend:** Vanilla JS frontend with dark mode UI and native fetch API integration.

---

## Project Structure

```text
random-user-picker/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI routes & entry point
│   ├── store.py         # Thread-safe in-memory state engine
│   └── templates/
│       └── index.html   # User interface
├── .gitignore
├── README.md
└── requirements.txt     # Python dependencies