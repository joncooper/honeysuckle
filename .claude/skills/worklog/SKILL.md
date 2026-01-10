---
name: worklog
description: Update the WORKLOG.md with session progress, architectural decisions, lessons learned, and next steps
---

# Worklog Update Skill

Use this skill at the end of a work session to update the project worklog.

## Instructions

1. **Read the current WORKLOG.md** to understand the format and recent entries

2. **Review this session's work** by examining:
   - Git diff to see what changed
   - Any beans tasks that were completed
   - Conversations and decisions made during the session

3. **Create a new entry** at the top of the log (after the header) with today's date and a brief title describing the session's focus

4. **Fill in the sections:**

   **Achieved:**
   - List concrete accomplishments
   - Reference specific files created or modified
   - Note any tasks completed

   **Architectural Decisions:** (if any were made)
   - DECISION: State what was decided
   - REASON: Explain the rationale
   - Only include significant design choices, not routine implementation details

   **Lessons Learned:** (if any)
   - Important insights discovered during the session
   - Clarifications from user conversations
   - Gotchas, edge cases, or non-obvious behaviors encountered
   - Things that should be remembered for future sessions
   - Corrections to earlier assumptions

   **Next:**
   - List immediate next steps for the following session
   - Be specific and actionable

5. **Update beans tasks:**
   - Run `beans done <id>` for completed tasks
   - Run `beans add "..."` for new tasks identified
   - Run `beans list` to verify current state

6. **Commit the changes** with message: "docs: update worklog for [date]"

## Example Entry

```markdown
## [2025-01-15] WebSocket Audio Pipeline

**Achieved:**
- Implemented bidirectional WebSocket in `backend/src/honeysuckle/main.py`
- Created audio buffer management in `backend/src/honeysuckle/receptionist/audio.py`
- Added basic VAD detection hook

**Architectural Decisions:**
- DECISION: Use raw websockets library instead of FastAPI WebSocket
- REASON: Need lower-level control for audio streaming and buffer management

**Lessons Learned:**
- OpenAI Realtime API expects PCM 16-bit audio at 24kHz, not 16kHz like whisper
- The `response.cancel` event must be sent before clearing local buffers, otherwise audio continues playing
- User clarified: Bluetooth car mics are actually higher quality than expected, don't over-engineer noise handling

**Next:**
- Connect to OpenAI Realtime API
- Implement audio encoding/decoding (PCM 16-bit, 24kHz)
- Add connection health monitoring
```
