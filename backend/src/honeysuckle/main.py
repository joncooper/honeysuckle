"""FastAPI application with WebSocket audio endpoint."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from honeysuckle.config import settings
from honeysuckle.session.manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    if settings.phoenix_enabled:
        from honeysuckle.observability.phoenix import setup_phoenix

        setup_phoenix()

    yield
    # Shutdown


app = FastAPI(
    title="Honeysuckle",
    description="Voice-first email and calendar assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):
    """
    Bidirectional audio WebSocket endpoint.

    Protocol:
    - Client sends: binary audio frames (PCM16, 24kHz, mono)
    - Client sends: JSON control messages (vad_start, vad_end, etc.)
    - Server sends: binary audio frames (PCM16, 24kHz, mono)
    - Server sends: JSON event messages (state, transcript, tool_use, etc.)
    """
    await websocket.accept()

    session = SessionManager(websocket)

    try:
        await session.run()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        # Log error and close gracefully
        print(f"WebSocket error: {e}")
    finally:
        await session.cleanup()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "honeysuckle.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
