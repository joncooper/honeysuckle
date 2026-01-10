---
# honeysuckle-lrb4
title: Voice Core (MVP)
status: completed
type: milestone
priority: normal
created_at: 2026-01-10T18:15:41Z
updated_at: 2026-01-10T19:59:09Z
---

Voice conversation that can read emails.

**Goal:** User can ask 'What emails do I have?' and hear the response.

## Tasks
- FastAPI WebSocket endpoint (/ws/audio)
- OpenAI Realtime client (bidirectional audio streaming)
- Claude Agent SDK integration with gday CLI
- Basic SessionManager (Receptionist → Professor handoff)
- Minimal frontend (audio visualizer + state indicator)