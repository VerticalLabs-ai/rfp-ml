"""
WebSocket endpoints for real-time updates.
"""
import asyncio
import json
import logging
from typing import Dict, List

from app.core.database import get_db
from app.services.rfp_processor import processor
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for general updates and specific document editing."""

    def __init__(self):
        self.active_connections: List[WebSocket] = [] # For general pipeline updates
        self.document_connections: Dict[str, List[WebSocket]] = {} # For document-specific editing

    async def connect(self, websocket: WebSocket, doc_id: str | None = None):
        """Accept and store new WebSocket connection.
        If doc_id is provided, connection is for document editing.
        """
        await websocket.accept()
        if doc_id:
            if doc_id not in self.document_connections:
                self.document_connections[doc_id] = []
            self.document_connections[doc_id].append(websocket)
            logger.info("WebSocket connected for document %s. Total connections: %d", doc_id, len(self.document_connections[doc_id]))
        else:
            self.active_connections.append(websocket)
            logger.info("General WebSocket connected. Total connections: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket, doc_id: str | None = None):
        """Remove WebSocket connection.
        If doc_id is provided, remove from document connections, otherwise from general.
        """
        if doc_id and doc_id in self.document_connections:
            if websocket in self.document_connections[doc_id]:
                self.document_connections[doc_id].remove(websocket)
            if not self.document_connections[doc_id]:
                del self.document_connections[doc_id]
            logger.info("WebSocket disconnected for document %s.", doc_id)
        elif websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("General WebSocket disconnected.")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific client."""
        await websocket.send_text(message)

    async def broadcast(self, message: dict):
        """Broadcast message to all general connected clients."""
        message_str = json.dumps(message)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning("Error broadcasting to a general connection: %s. Removing.", e)
                dead_connections.append(connection)
        for conn in dead_connections:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

    async def broadcast_document_update(self, doc_id: str, message: dict, exclude_websocket: WebSocket | None = None):
        """Broadcast message to all clients connected to a specific document, excluding sender if specified."""
        if doc_id not in self.document_connections:
            return

        message_str = json.dumps(message)
        dead_connections = []
        for connection in self.document_connections[doc_id]:
            if connection != exclude_websocket:
                try:
                    await connection.send_text(message_str)
                except Exception as e:
                    logger.warning("Error broadcasting to document connection (%s): %s. Removing.", doc_id, e)
                    dead_connections.append(connection)
        for conn in dead_connections:
            if conn in self.document_connections.get(doc_id, []):
                self.document_connections[doc_id].remove(conn)


manager = ConnectionManager()


@router.websocket("/pipeline")
async def websocket_pipeline_updates(websocket: WebSocket):
    """WebSocket endpoint for pipeline updates with heartbeat support."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()

            if data:
                try:
                    message = json.loads(data)
                    msg_type = message.get("type", "")

                    # Handle heartbeat ping
                    if msg_type == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": message.get("timestamp")
                        })
                    else:
                        # Echo back or handle other client messages
                        await websocket.send_json({
                            "type": "ack",
                            "message": "Message received"
                        })
                except json.JSONDecodeError:
                    # Handle non-JSON messages
                    await websocket.send_json({
                        "type": "ack",
                        "message": "Message received"
                    })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected from pipeline")


@router.websocket("/edit/{bid_document_id}")
async def websocket_document_edit(websocket: WebSocket, bid_document_id: str, db: Session = Depends(get_db)):
    """WebSocket endpoint for real-time collaborative document editing."""
    await manager.connect(websocket, doc_id=bid_document_id)
    try:
        # On connect, send the current document content to the new client
        bid_doc_content = processor.get_bid_document(bid_document_id)
        if bid_doc_content:
            await manager.send_personal_message(json.dumps({"type": "initial_content", "content": bid_doc_content["content"]["markdown"]}), websocket)
        else:
            await manager.send_personal_message(json.dumps({"type": "error", "message": "Document not found"}), websocket)

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "document_update":
                # This is a simplified approach: client sends full content, server broadcasts.
                # For true OT/CRDT, changes would be operational transforms.
                updated_content = message["content"]
                # Optional: Persist update to DB (or periodically save)
                # Update the in-memory processor as well
                processor.update_bid_document_content(bid_document_id, updated_content)

                # Broadcast to other clients for this document
                await manager.broadcast_document_update(
                    bid_document_id,
                    {"type": "document_update", "content": updated_content},
                    exclude_websocket=websocket
                )
            # Add other message types if needed (e.g., cursor position, comments)

    except WebSocketDisconnect:
        manager.disconnect(websocket, doc_id=bid_document_id)


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


async def broadcast_pipeline_update(event: str, rfp_data: dict = None, stages: dict = None):
    """Broadcast pipeline update to all connected clients.

    Args:
        event: Type of pipeline event (rfp_added, rfp_moved, rfp_removed, stages_updated)
        rfp_data: Data about the affected RFP
        stages: Updated stage counts
    """
    message = {
        "type": "pipeline_update",
        "event": event,
        "rfp": rfp_data or {},
        "stages": stages or {},
        "timestamp": str(asyncio.get_event_loop().time())
    }
    await manager.broadcast(message)
