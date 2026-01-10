---
# honeysuckle-6toj
title: Claude Agent SDK cancel scope error
status: todo
type: bug
priority: normal
created_at: 2026-01-10T19:54:57Z
updated_at: 2026-01-10T19:54:57Z
---

## Problem
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in

This happens when the Professor query completes. It's an internal SDK issue with async task management.

## Possible Causes
- The `query()` async generator is being consumed in a different task context
- Task spawning/cancellation not matching SDK expectations

## Investigation Needed
- Check SDK source for proper usage patterns
- May need to run SDK query in same task context
- Consider using `ClaudeSDKClient` instead of `query()` function

## Files
- backend/src/honeysuckle/professor/client.py