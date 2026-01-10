---
# honeysuckle-j7dk
title: Claude Agent SDK integration with gday
status: completed
type: task
priority: normal
created_at: 2026-01-10T18:16:12Z
updated_at: 2026-01-10T18:36:54Z
parent: honeysuckle-lrb4
---

Integrate Claude Agent SDK for Professor reasoning with gday CLI access.

## Requirements
- ClaudeCodeClient setup with system prompt
- Bash tool access for gday CLI
- Stream tool use events
- Return final result text

## Auth Approach
- Use Claude Max subscription via OAuth (not API key)
- Need to figure out: OAuth flow or extract token from Claude Code session
- SDK repo: https://github.com/anthropics/claude-agent-sdk-python

## Files
- backend/src/honeysuckle/professor/client.py (already stubbed)
- backend/src/honeysuckle/professor/prompts.py (done)