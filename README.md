# Honeysuckle

A voice-first email and calendar assistant using a "Split-Brain" architecture.

## Architecture

Honeysuckle uses two AI systems working together:

- **Receptionist** (OpenAI Realtime): Low-latency voice interface with VAD, barge-in, and natural conversation flow
- **Professor** (Claude Agent SDK): Deep reasoning and tool execution via `gday` CLI for email/calendar operations

The Receptionist handles real-time voice interaction while delegating complex tasks to the Professor for careful reasoning.

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
│   ├── receptionist/        # OpenAI Realtime client
│   ├── professor/           # Claude Agent SDK client
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
