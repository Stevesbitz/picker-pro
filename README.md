# pickrPro

A lightweight, high-performance web application for fair, round-robin random selection. Built using FastAPI and responsive HTML5/CSS3, state is synced server-side across all active clients in real-time.

---

## Key Features

* **Round-Robin Fair Picking:** Ensures every active user gets picked exactly once before the round resets automatically.
* **Shareable Team Rooms:** Each team creates an isolated room and shares its unique link with members.
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
```
## Installation & Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/Stevesbitz/picker-pro
cd picker-pro
```

### 2. Create and activate a virtual environment
#### macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Windows (Command Prompt):
```bash
python -m venv venv
venv\Scripts\activate
```

#### Windows (PowerShell):
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install project dependencies
```bash
pip install -r requirements.txt
```

## Running the Application

### Start the server with live reloading
```bash
uvicorn app.main:app --reload
```
Web Application: [http://127.0.0.1:8000](http://127.0.0.1:8000)

Swagger API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Team rooms

Open the app root and create a room for a team. The app redirects to a unique
room URL; share that URL with the team. Rosters, picks, and round status are
isolated to that room. Anyone with the link can access the room, so treat it as
the team's access key. Room data is currently in memory and resets when the
server restarts.

## Running tests

The test suite uses Python's built-in `unittest` module and needs no extra test
dependencies. From the project root, run:

```bash
python -m unittest discover -v
```

The tests cover the in-memory store's fairness rules, round reset behavior,
checked-user handling, timestamps, and each API handler's validation and error
responses.

## Continuous integration

GitHub Actions runs the full test suite and compiles the application after every
push to any branch. The workflow is defined in `.github/workflows/ci.yml`.
