"""
WebSocket endpoints for real-time updates.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and store new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific client."""
        await websocket.send_text(message)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        message_str = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except:
                pass  # Connection may be closed


manager = ConnectionManager()


@router.websocket("/pipeline")
async def websocket_pipeline_updates(websocket: WebSocket):
    """WebSocket endpoint for pipeline updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()

            # Echo back or handle client messages if needed
            if data:
                await websocket.send_json({
                    "type": "ack",
                    "message": "Message received"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def broadcast_rfp_update(rfp_id: str, stage: str, data: dict = None):
    """Broadcast RFP stage update to all connected clients."""
    message = {
        "type": "rfp_update",
        "rfp_id": rfp_id,
        "stage": stage,
        "data": data or {},
        "timestamp": str(asyncio.get_event_loop().time())
    }
    await manager.broadcast(message)


async def broadcast_submission_update(submission_id: str, status: str, data: dict = None):
    """Broadcast submission status update to all connected clients."""
    message = {
        "type": "submission_update",
        "submission_id": submission_id,
        "status": status,
        "data": data or {},
        "timestamp": str(asyncio.get_event_loop().time())
    }
    await manager.broadcast(message)
