"""WebSocket router for dispatching live agent execution updates to clients."""

import json
from typing import Dict, List, Any
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSockets"])


class ConnectionManager:
    """Manages active WebSocket connections for real-time progress updates."""

    def __init__(self):
        # Maps session_id str to list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Register a new websocket connection for a session topic."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"WebSocket client connected to session room: {session_id}")

    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove a websocket connection from a session topic."""
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"WebSocket client disconnected from session room: {session_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a direct message to a specific connection."""
        await websocket.send_text(message)

    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """Broadcast live agent updates to all listening connections for a session."""
        if session_id not in self.active_connections:
            return

        json_msg = json.dumps(message)
        logger.debug(f"Broadcasting to room {session_id}: {json_msg}")
        
        # Gather stale connections to clean up
        stale = []
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_text(json_msg)
            except Exception as e:
                logger.warning(f"Failed to send websocket message, connection likely closed: {e}")
                stale.append(connection)

        for conn in stale:
            self.disconnect(conn, session_id)


# Global WebSocket connection manager instance
ws_manager = ConnectionManager()


@router.websocket("/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    Subscribes a client to real-time status and logs stream for a tailoring session.
    """
    await ws_manager.connect(websocket, session_id)
    try:
        # Keep connection open and listen for client heartbeats or messages
        while True:
            data = await websocket.receive_text()
            # Simple heartbeat ping/pong response
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error in room {session_id}: {e}")
        ws_manager.disconnect(websocket, session_id)

