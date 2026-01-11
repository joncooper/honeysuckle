# Honeysuckle

![Sam and Foyle from Foyle's War](docs/images/sam-and-foyle.jpg)

*"Sam, I need you to find out everything you can about..."*

A voice-first email and calendar assistant using a "Split-Brain" architecture, named in tribute to the BBC detective series [Foyle's War](https://en.wikipedia.org/wiki/Foyle%27s_War).

## The Name

**Honeysuckle** comes from [Honeysuckle Weeks](https://en.wikipedia.org/wiki/Honeysuckle_Weeks), the actress who plays Samantha "Sam" Stewart in Foyle's War. In the series, Sam serves as driver and assistant to Detective Chief Superintendent Christopher Foyle, helping him solve crimes in wartime Britain.

Our architecture mirrors this partnership:

- **Sam** (OpenAI Realtime) — Like her namesake, Sam is the capable, quick-thinking assistant who handles real-time interaction. She manages the voice interface, stays alert for interruptions (barge-in), and keeps the conversation flowing naturally.

- **Foyle** (Claude Agent SDK) — Like the detective, Foyle does the deep thinking. He investigates your email and calendar, reasons through complex requests, and decides what actions to take. Methodical, thorough, and precise.

Together, they form a split-brain architecture: Sam handles the fast conversational loop while Foyle handles the slow reasoning loop.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                             │
│                                                                     │
│  ┌──────────────────────┐      ┌──────────────────────────────┐    │
│  │         Sam          │      │           Foyle              │    │
│  │   (OpenAI Realtime)  │─────▶│    (Claude Agent SDK)        │    │
│  │                      │      │                              │    │
│  │  • Speech-to-speech  │      │  • Deep reasoning            │    │
│  │  • VAD (barge-in)    │      │  • gday CLI (email/calendar) │    │
│  │  • Natural flow      │      │  • Tool execution            │    │
│  └──────────────────────┘      └──────────────────────────────┘    │
│             │                              │                        │
│             └──────────────┬───────────────┘                        │
│                            ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  SessionManager (Supervisor)                  │  │
│  │                                                               │  │
│  │  • Orchestrates Sam ↔ Foyle handoff                           │  │
│  │  • Injects ambient audio during thinking                      │  │
│  │  • Manages voice-based approval flow                          │  │
│  │  • Handles barge-in cancellation                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

**Backend:** Python 3.11+, FastAPI, Claude Agent SDK, OpenAI Realtime API, WebSockets
**Frontend:** React, Vite, TypeScript, Tailwind CSS
**Tools:** `gday` CLI for Gmail/Calendar operations
**Observability:** Arize Phoenix for LLM tracing

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (or Bun)
- OpenAI API key with Realtime API access
- [`gday`](https://github.com/jdcloud/gday) CLI installed and authenticated

### Setup

```bash
# Backend
cd backend
cp .env.example .env  # Edit with your API keys
uv sync
uv run uvicorn honeysuckle.main:app --reload

# Frontend (in another terminal)
cd frontend
bun install
bun run dev
```

Open http://localhost:3000, click Connect, then Start Mic to begin talking.

## Project Structure

```
backend/
├── src/honeysuckle/
│   ├── main.py              # FastAPI app with WebSocket endpoint
│   ├── session/             # Session orchestration
│   ├── sam/                 # OpenAI Realtime client (formerly receptionist/)
│   ├── foyle/               # Claude Agent SDK client (formerly professor/)
│   └── observability/       # Phoenix tracing
frontend/
├── src/
│   ├── App.tsx              # Main UI
│   ├── contexts/            # Session state management
│   └── components/          # UI components
```

## Documentation

- [INITIAL-PROMPT.md](./INITIAL-PROMPT.md) - Full architecture specification
- [WORKLOG.md](./WORKLOG.md) - Development log with decisions and lessons learned
- [CLAUDE.md](./CLAUDE.md) - Claude Code configuration

## Status

**Milestone 1: Voice Core MVP** - Complete ✅

Working end-to-end voice flow with barge-in support and Phoenix observability.

## License

MIT
