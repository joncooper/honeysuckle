---
# honeysuckle-rch4
title: OpenAI Realtime client
status: completed
type: task
priority: normal
created_at: 2026-01-10T18:16:12Z
updated_at: 2026-01-10T18:36:54Z
parent: honeysuckle-lrb4
---

Implement OpenAI Realtime API client for speech-to-speech.

## Requirements
- Persistent WebSocket to OpenAI Realtime API
- Bidirectional audio streaming
- Handle VAD (server-side voice activity detection)
- Parse events (audio, transcripts, function calls)
- Support barge-in via response.cancel

## Files
- backend/src/honeysuckle/receptionist/client.py (already stubbed)