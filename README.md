# pickerPro

pickerPro is a FastAPI-based round-robin picker app for creating shareable team rooms and selecting users fairly. Users can add or remove team members, mark them as active or inactive, and pick a new user while preventing repeat picks until the round resets.

## Features

- Round-robin fairness with automatic reset after each full cycle
- Task-specific pools such as Standup, Code Review, and On-Call
- Out-of-office status that excludes unavailable users from picks
- Optional Slack notifications for the selected task assignee
- Isolated team rooms with unique room URLs
- Thread-safe in-memory state management with optional SQLAlchemy persistence
- Admin dashboard access for session visibility
- API rate limiting per client IP
- Vanilla HTML/CSS/JS frontend with composable FastAPI templates

## Architecture

The application follows a small layered design:

- **API layer:** `app/main.py` handles HTTP concerns, validation, authentication, and response formatting.
- **Application layer:** `app/services/` exposes room and picker use cases through injected service objects.
- **Storage layer:** `app/store/` defines `BaseRoomStore` and `StateStore` contracts with in-memory and SQLAlchemy implementations.
- **Schema layer:** `app/schemas/` contains the Pydantic contracts shared by the API and storage implementations.
- **Frontend layer:** `app/templates/` contains the layout, shared components, and page markup; `app/static/` contains page-specific behavior.

The default backend is in-memory. Set `DATABASE_URL` to use SQLAlchemy persistence. SQLite and PostgreSQL-style URLs are supported by SQLAlchemy, for example:

```bash
DATABASE_URL=sqlite:///./picker.db uvicorn app.main:app --reload
```

The application falls back to in-memory storage if the configured database cannot be initialized.

### Slack configuration

Configure the Slack Web API to send assignments to a specific channel:

```bash
export SLACK_BOT_TOKEN=xoxb-your-token
export SLACK_CHANNEL_ID=C0123456789
```

The bot must be a member of the target channel and have permission to post messages. For a simpler single-channel setup, configure an incoming webhook instead:

```bash
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

When both configurations are present, the Web API configuration takes precedence. Slack credentials are read only by the server and are never sent to the browser.

Each room can override the default channel by entering a Slack channel ID below the task-pool controls and saving it. This value is stored with the room and is used for that room’s notifications. If a room has no channel ID, `SLACK_CHANNEL_ID` is used.

## Current project structure

```text
picker-app/
├── .github/
│   └── workflows/
│       └── ci.yml
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, routes, middleware, auth, rate limiting
│   ├── store/
│   │   ├── __init__.py          # Selects the configured storage backend
│   │   ├── base.py              # Storage interface
│   │   ├── memory.py            # Default in-memory backend
│   │   └── db.py                # Optional SQLAlchemy backend
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── rooms.py             # Room request/response models
│   │   └── users.py             # User and picker state models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── picker.py            # Picker use-case service
│   │   └── rooms.py             # Room and pool use-case service
│   ├── static/
│   │   ├── styles.css           # Shared frontend styles
│   │   ├── site.js              # Shared site behavior
│   │   ├── home.js              # Room creation behavior
│   │   ├── login.js             # Admin login behavior
│   │   ├── admin.js             # Admin dashboard behavior
│   │   └── room.js              # Pool and picker behavior
│   └── templates/
│       ├── components/
│       │   ├── header.html      # Shared header and navigation
│       │   └── footer.html      # Shared footer
│       ├── pages/
│       │   ├── home.html        # Room creation page
│       │   ├── login.html       # Admin login page
│       │   ├── admin.html       # Admin dashboard page
│       │   └── room.html        # Team picker page
│       ├── error.html
│       └── index.html            # Layout and page composition
├── tests/
│   ├── __init__.py
│   ├── test_main.py             # API-level tests
│   └── test_store.py            # Store and picker behavior tests
├── .gitignore
├── README.md
├── requirements.txt             # Python dependencies
└── venv/
```

## How the app is organized

- `app/main.py` initializes the FastAPI application and exposes both page routes and API endpoints.
- `app/store/` defines the storage abstraction, in-memory backend, and optional SQLAlchemy backend.
- `app/schemas/` contains the Pydantic models used for room, user, and API payload validation.
- `app/services/` contains reusable picker and room service logic.
- `app/templates/components/` contains shared page chrome, while `app/templates/pages/` contains page-specific markup.
- `app/static/` contains shared styles and one JavaScript module per page behavior.
- `tests/` covers both the API and the fairness logic in the in-memory picker state.

## Local setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd picker-app
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Run the application

```bash
uvicorn app.main:app --reload
```

Then open:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs

## Room and API behavior

- Create a room from the main app or API.
- Each room gets its own isolated state and user list.
- Users can be toggled on/off before selection.
- Each room can contain multiple task pools. Pass `pool_id` to state and user/picker endpoints to work with a specific pool.
- Users can be marked OOO through `PATCH /api/rooms/{room_id}/users/{user_id}/ooo`.
- The picker chooses a user fairly without repeating them in the same round.
- Room data uses memory by default and resets when the server restarts. Set `DATABASE_URL` to use the SQLAlchemy backend.

### Main endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/rooms` | Create a team room |
| `GET` | `/api/rooms/{room_id}/pools` | List task pools |
| `POST` | `/api/rooms/{room_id}/pools` | Create a task pool |
| `GET` | `/api/rooms/{room_id}/state?pool_id=...` | Read pool state |
| `POST` | `/api/rooms/{room_id}/users?pool_id=...` | Add a user |
| `PATCH` | `/api/rooms/{room_id}/users/{user_id}?pool_id=...` | Toggle eligibility |
| `PATCH` | `/api/rooms/{room_id}/users/{user_id}/ooo?pool_id=...` | Toggle OOO status |
| `POST` | `/api/rooms/{room_id}/pick?pool_id=...` | Pick the next available user |
| `POST` | `/api/rooms/{room_id}/reset?pool_id=...` | Reset the current round |
| `POST` | `/api/rooms/{room_id}/notify-slack?pool_id=...` | Notify Slack about the selected user |
| `PATCH` | `/api/rooms/{room_id}/slack-channel` | Save or clear the room Slack channel ID |

The room UI enables **Notify Slack** after a user has been selected. The notification uses the selected pool’s last-picked user and can be sent again when needed. If Slack is not configured, the rest of the picker remains available and the notification returns `503`.

## Tests

Run the project tests with:

```bash
python -m unittest discover -v
```

The test suite validates room behavior, picker fairness, round resets, and API handlers. Additional smoke checks cover template rendering and the SQLAlchemy SQLite backend.
