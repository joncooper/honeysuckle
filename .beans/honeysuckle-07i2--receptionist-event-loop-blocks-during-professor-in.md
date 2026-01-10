---
# honeysuckle-07i2
title: Receptionist event loop blocks during Professor invocation
status: completed
type: bug
priority: high
created_at: 2026-01-10T19:54:48Z
updated_at: 2026-01-10T19:59:09Z
---

## Problem
The `_receptionist_loop` awaits `_invoke_professor`, blocking all Receptionist event processing while Professor runs. This causes:
- Audio events queue up instead of being forwarded immediately
- 'Let me check that for you' plays AFTER Professor results appear
- Out-of-order UX

## Root Cause
```python
async for event in self.receptionist.events():
    elif isinstance(event, FunctionCall):
        await self._invoke_professor(query, event.call_id)  # BLOCKS!
```

## Fix
Spawn Professor as a background task, don't await it:
```python
asyncio.create_task(self._invoke_professor(query, event.call_id))
```

## Files
- backend/src/honeysuckle/session/manager.py