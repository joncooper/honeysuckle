---
# honeysuckle-8ku5
title: Basic SessionManager handoff
status: completed
type: task
priority: normal
created_at: 2026-01-10T18:16:12Z
updated_at: 2026-01-10T18:36:54Z
parent: honeysuckle-lrb4
---

Implement Receptionist → Professor handoff in SessionManager.

## Requirements
- Route ask_professor function call to Professor
- Stream Professor events to frontend
- Speak Professor result via Receptionist
- Handle basic state transitions

## Files
- backend/src/honeysuckle/session/manager.py (already stubbed)