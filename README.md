# RoomLine

An AI concierge for hotel guests, built with a LangGraph tool-calling agent. Guests chat naturally about room service, housekeeping, maintenance, and wake-up calls; the agent decides which action to take and calls the matching backend tool. A separate staff dashboard shows everything the agent has logged and lets staff work through it.

## What it does

**Guest chat** — a guest opens the page, enters their room number, and talks to the concierge in plain language ("can I get extra towels", "order me a club sandwich", "wake me up at 7"). The agent has 8 tools available and picks whichever fits the request, or asks a clarifying question when the request is ambiguous between two of them.

**Staff dashboard** — a live view of everything currently open: housekeeping requests, maintenance tickets, room service orders, wake-up calls, and staff escalations. Staff can update status on each, and check a room out — which clears that room's conversation memory and cancels its guest-specific open requests, while deliberately leaving maintenance tickets and escalations open since those outlive the guest's stay.

## Architecture

```
Guest message ──▶ /chat ──▶ LangGraph agent loop
                                 │
                    system prompt (built fresh per
                    request from hotel_config.json)
                                 │
                         ┌───────┴────────┐
                         │  8 tools:      │
                         │  order, house- │
                         │  keeping,      │
                         │  maintenance,  │
                         │  wake-up call  │
                         │  (+ cancel),   │
                         │  order status, │
                         │  menu lookup,  │
                         │  escalate      │
                         └───────┬────────┘
                                 │
                    SQLite (roomline.db) - the
                    actual business records
```

Conversation memory is per-room: the room number is used directly as the LangGraph thread ID, so a guest can close the tab and come back later in the same stay and the agent still has context. That memory is stored separately (`checkpoints.db`) from the business data (`roomline.db`), and staff checkout explicitly clears the former without touching the latter — memory is conversational and disposable, business records are not.

## Tech stack

- **Backend**: FastAPI, LangGraph + LangChain (via `langchain-litellm`, so the model provider is swappable through one config value), SQLModel/SQLAlchemy (async, SQLite), Langfuse for tracing
- **Frontend**: plain HTML/CSS/JS, no framework or build step — served directly by FastAPI as static files
- **Auth**: none yet (see Known limitations)

## Project structure

```
backend/
  app/
    agent/         LangGraph workflow, tools, system prompt, model config
    main.py         /chat, /health, /hotel-config, mounts the frontend
    staff.py        /staff/* - dashboard data + status/checkout endpoints
    models.py        SQLModel tables (Order, HousekeepingRequest, etc.)
    hotel_config.py   loads hotel_config.json (single source of truth)
  hotel_config.json   hotel name, branding text, amenities, menu - edit this
                        to reconfigure the whole app for a different hotel
frontend/
  index.html, style.css, app.js     guest chat page
  staff/                             staff dashboard (separate page)
```

## Running it locally

```bash
cd backend
cp .env.example .env   # then fill in LLM_MODEL and the matching *_API_KEY
python -m venv venv    # or use an existing venv
source venv/bin/activate
pip install -r ../requirements.txt
uvicorn app.main:app --reload
```

Then open `http://localhost:8000/` for the guest chat, or `http://localhost:8000/staff/` for the dashboard.

## A couple of design decisions worth knowing about

- **`hotel_config.json` is the single source of truth.** It feeds the agent's system prompt *and* both frontend pages (via a `/hotel-config` endpoint) — changing the hotel's name, menu, or amenities in one file updates the AI's behavior and what guests/staff see, with nothing to keep in sync by hand.
- **AI replies are markdown, sanitized before render.** The model naturally writes tables and bold text; the frontend renders that as real HTML but runs it through DOMPurify first, since a manipulated reply containing something like a script tag should never be able to execute in a guest's browser.
- **Checkout is a considered action, not a blunt reset.** It refuses by default if a room still has open requests (returns what's outstanding so the frontend can confirm), and only cancels the guest-specific items (orders, housekeeping, wake-up calls) — a maintenance ticket for a broken AC stays open after checkout, because the AC is still broken.

## Known limitations

- **No authentication** on either the guest chat or the staff dashboard — anyone with the URL can act as any room number, and the staff dashboard has no login at all.

Two related gaps that used to be listed here - orders being placeable for items not on the real menu, and the agent being unable to say what a guest's most recent order actually contained - are fixed: `place_room_service_order` now rejects anything not in `hotel_config.json`'s menu before it touches the database, and `get_order_status` returns the ordered items, not just a status string.

This is a documented gap rather than an oversight discovered after the fact - it has a specific fix in mind (a lightweight password gate), just not built yet.
