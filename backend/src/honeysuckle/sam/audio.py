"""Audio buffer management for Sam."""

import asyncio
from collections import deque


class AudioBuffer:
    """
    Thread-safe audio buffer for streaming audio data.

    Buffers audio chunks for smooth playback and handles
    clear operations for barge-in scenarios.
    """

    def __init__(self, max_chunks: int = 100):
        self._buffer: deque[bytes] = deque(maxlen=max_chunks)
        self._lock = asyncio.Lock()

    async def append(self, chunk: bytes):
        """Add audio chunk to buffer."""
        async with self._lock:
            self._buffer.append(chunk)

    async def get(self) -> bytes | None:
        """Get next audio chunk, or None if empty."""
        async with self._lock:
            if self._buffer:
                return self._buffer.popleft()
            return None

    async def get_all(self) -> bytes:
        """Get all buffered audio as single bytes object."""
        async with self._lock:
            if not self._buffer:
                return b""
            result = b"".join(self._buffer)
            self._buffer.clear()
            return result

    async def clear(self):
        """Clear all buffered audio (for barge-in)."""
        async with self._lock:
            self._buffer.clear()

    @property
    def size(self) -> int:
        """Number of chunks in buffer."""
        return len(self._buffer)

    @property
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self._buffer) == 0
