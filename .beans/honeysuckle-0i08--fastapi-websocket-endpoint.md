---
# honeysuckle-0i08
title: FastAPI WebSocket endpoint
status: completed
type: task
priority: normal
created_at: 2026-01-10T18:16:12Z
updated_at: 2026-01-10T18:36:54Z
parent: honeysuckle-lrb4
---

Create /ws/audio WebSocket endpoint for bidirectional audio streaming.

## Requirements
- Accept binary audio frames (PCM16, 24kHz, mono)
- Accept JSON control messages (vad_start, vad_end)
- Send binary audio frames to client
- Send JSON event messages (state, transcript, tool_use)

## Files
- backend/src/honeysuckle/main.py (endpoint already stubbed)