# Honeysuckle - Claude Code Configuration

## Project Overview

Honeysuckle is a voice-first email and calendar assistant using a "Split-Brain" architecture:
- **Receptionist** (OpenAI Realtime): Low-latency voice interface, VAD, barge-in
- **Professor** (Claude Agent SDK): Deep reasoning, tool execution via `gday` CLI

See `INITIAL-PROMPT.md` for full architecture specification.

## Session Workflow

### At Session Start (DO THIS FIRST)

1. **Run `beans prime`** to load current tasks into context
2. **Read `WORKLOG.md`** - especially the most recent entry's "Next" section
3. **Summarize** the current state and planned work to the user

### During Session

- Use `beans` CLI to manage tasks:
  - `beans add "Task description"` - Create a new task
  - `beans list` - View all tasks
  - `beans tui` - Interactive task browser
  - `beans done <id>` - Mark task complete
  - `beans show <id>` - View task details

- Keep tasks granular and actionable
- Update task status as you work

### At Session End

Run `/worklog` to update the work log, or manually:

1. **Update `WORKLOG.md`** with a new dated entry containing:
   - **Achieved:** What was accomplished this session
   - **Architectural Decisions:** Any significant design choices made (with DECISION and REASON)
   - **Lessons Learned:** Important insights, clarifications, gotchas discovered
   - **Next:** Immediate next steps for the following session

2. **Update beans tasks:**
   - Mark completed tasks as done (`beans done <id>`)
   - Create new tasks for identified work (`beans add "..."`)
   - Archive or close stale tasks

3. **Commit changes** with a meaningful message

## WORKLOG.md Format

```markdown
## [YYYY-MM-DD] Brief Title

**Achieved:**
- Bullet points of what was accomplished
- Reference specific files changed

**Architectural Decisions:** (if any)
- DECISION: What was decided
- REASON: Why this choice was made

**Lessons Learned:** (if any)
- Important insights discovered
- Clarifications from user conversations
- Gotchas or non-obvious behaviors
- Corrections to earlier assumptions

**Next:**
- Immediate next steps (specific and actionable)
```

## Key Files

| File | Purpose |
|------|---------|
| `INITIAL-PROMPT.md` | Full project specification and architecture |
| `WORKLOG.md` | Running log of sessions, decisions, lessons, progress |
| `.beans/` | Task tracking (managed by beans CLI) |
| `.beans.yml` | Beans configuration |
| `.claude/skills/worklog/` | Skill for updating worklog at session end |

## Tech Stack Reference

**Backend:** Python 3.11+, FastAPI, Claude Agent SDK, OpenAI SDK, websockets
**Frontend:** React, Vite, TypeScript, shadcn/ui, Tailwind
**Tools:** `gday` CLI at `~/.local/bin/gday` for Gmail/Calendar
**Task Management:** beans (`beans` CLI)

## External Dependencies

- `gday` CLI must be installed and authenticated (`gday auth status`)
- OpenAI API key required for Realtime API
- Anthropic API key required for Claude Agent SDK

## Development Commands

```bash
# Backend
cd backend && uv sync && uv run uvicorn honeysuckle.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Task management
beans prime          # Load context for AI session
beans list           # View tasks
beans tui            # Interactive browser
beans add "..."      # Create task
beans done <id>      # Complete task
```

## Architecture Principles

1. **Voice-first, visual-companion:** Audio is primary, UI adapts to context
2. **Context-aware deferral:** Risky/complex actions defer to high-bandwidth contexts
3. **Human-in-the-loop:** Voice-based approval for sensitive operations
4. **Split-brain:** Receptionist handles conversation flow, Professor handles reasoning
5. **Ambient feedback:** Never go silent during thinking - provide audio cues
