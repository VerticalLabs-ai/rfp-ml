"""
Enhanced WebSocket channels for real-time updates.

Provides channel-based subscriptions for:
- RFP-specific updates (scoring, compliance, pricing)
- Alert notifications
- Job progress tracking
- Chat streaming
"""
import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


class MessageType(str, Enum):
    """WebSocket message types."""
    # Existing types (backwards compatible)
    RFP_UPDATE = "rfp_update"
    SUBMISSION_UPDATE = "submission_update"
    DOCUMENT_UPDATE = "document_update"

    # New enhanced types
    SCORING_UPDATE = "scoring_update"
    PRICING_UPDATE = "pricing_update"
    COMPLIANCE_UPDATE = "compliance_update"
    JOB_PROGRESS = "job_progress"
    ALERT_NOTIFICATION = "alert_notification"
    CHAT_MESSAGE = "chat_message"

    # System messages
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    ACK = "ack"


class ChannelManager:
    """
    Enhanced WebSocket manager with channel-based subscriptions.

    Channels follow naming convention:
    - rfp:{rfp_id} - RFP-specific updates
    - alerts - Global alert notifications
    - jobs:{job_id} - Job progress tracking
    - chat:{session_id} - Chat streaming

    Example usage:
        await channel_manager.subscribe(websocket, "rfp:abc123")
        await channel_manager.broadcast_to_channel("rfp:abc123", {
            "type": "scoring_update",
            "data": {"triage_score": 85}
        })
    """

    def __init__(self):
        # Channel subscriptions: channel_name -> set of websockets
        self.channels: Dict[str, Set[WebSocket]] = {}
        # Websocket to channels mapping (for cleanup)
        self.websocket_channels: Dict[WebSocket, Set[str]] = {}
        # All active connections
        self.connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.connections.add(websocket)
        self.websocket_channels[websocket] = set()
        logger.info(f"WebSocket connected. Total connections: {len(self.connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Handle WebSocket disconnection and cleanup subscriptions."""
        # Remove from all channels
        if websocket in self.websocket_channels:
            for channel in self.websocket_channels[websocket]:
                if channel in self.channels:
                    self.channels[channel].discard(websocket)
                    # Clean up empty channels
                    if not self.channels[channel]:
                        del self.channels[channel]
            del self.websocket_channels[websocket]

        self.connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.connections)}")

    async def subscribe(self, websocket: WebSocket, channel: str) -> bool:
        """Subscribe a websocket to a channel."""
        if websocket not in self.connections:
            return False

        if channel not in self.channels:
            self.channels[channel] = set()

        self.channels[channel].add(websocket)
        self.websocket_channels[websocket].add(channel)

        logger.debug(f"Subscribed to channel: {channel}. Subscribers: {len(self.channels[channel])}")
        return True

    async def unsubscribe(self, websocket: WebSocket, channel: str) -> bool:
        """Unsubscribe a websocket from a channel."""
        if channel in self.channels:
            self.channels[channel].discard(websocket)
            if not self.channels[channel]:
                del self.channels[channel]

        if websocket in self.websocket_channels:
            self.websocket_channels[websocket].discard(channel)

        logger.debug(f"Unsubscribed from channel: {channel}")
        return True

    async def broadcast_to_channel(
        self,
        channel: str,
        message: dict,
        exclude: WebSocket | None = None
    ) -> int:
        """
        Broadcast a message to all subscribers of a channel.

        Args:
            channel: Channel name to broadcast to
            message: Message dict to send (will be JSON encoded)
            exclude: Optional websocket to exclude from broadcast

        Returns:
            Number of websockets message was sent to
        """
        if channel not in self.channels:
            return 0

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        message_str = json.dumps(message)
        sent_count = 0
        dead_connections = []

        for ws in self.channels[channel]:
            if ws == exclude:
                continue
            try:
                await ws.send_text(message_str)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to channel {channel}: {e}")
                dead_connections.append(ws)

        # Clean up dead connections
        for ws in dead_connections:
            self.disconnect(ws)

        return sent_count

    async def broadcast_all(self, message: dict) -> int:
        """Broadcast a message to all connected websockets."""
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        message_str = json.dumps(message)
        sent_count = 0
        dead_connections = []

        for ws in self.connections:
            try:
                await ws.send_text(message_str)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to broadcast: {e}")
                dead_connections.append(ws)

        for ws in dead_connections:
            self.disconnect(ws)

        return sent_count

    async def send_to_websocket(self, websocket: WebSocket, message: dict) -> bool:
        """Send a message to a specific websocket."""
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        try:
            await websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.warning(f"Failed to send message: {e}")
            self.disconnect(websocket)
            return False

    def get_channel_subscribers(self, channel: str) -> int:
        """Get the number of subscribers to a channel."""
        return len(self.channels.get(channel, set()))

    def get_websocket_channels(self, websocket: WebSocket) -> Set[str]:
        """Get all channels a websocket is subscribed to."""
        return self.websocket_channels.get(websocket, set()).copy()

    def get_stats(self) -> dict:
        """Get connection and channel statistics."""
        return {
            "total_connections": len(self.connections),
            "total_channels": len(self.channels),
            "channels": {
                name: len(subs) for name, subs in self.channels.items()
            }
        }


# Singleton instance
channel_manager = ChannelManager()


@router.websocket("/rfp/{rfp_id}")
async def rfp_channel(websocket: WebSocket, rfp_id: str):
    """
    RFP-specific channel for real-time updates.

    Receives updates for:
    - scoring_update: Triage score changes
    - pricing_update: Pricing calculations
    - compliance_update: Compliance matrix changes
    - document_update: Document generation progress
    """
    await channel_manager.connect(websocket)
    channel = f"rfp:{rfp_id}"
    await channel_manager.subscribe(websocket, channel)

    # Send subscription confirmation
    await channel_manager.send_to_websocket(websocket, {
        "type": MessageType.ACK.value,
        "channel": channel,
        "message": f"Subscribed to RFP {rfp_id} updates"
    })

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == MessageType.PING.value:
                    await channel_manager.send_to_websocket(websocket, {
                        "type": MessageType.PONG.value
                    })
                elif msg_type == MessageType.SUBSCRIBE.value:
                    # Allow subscribing to additional channels
                    new_channel = message.get("channel")
                    if new_channel:
                        await channel_manager.subscribe(websocket, new_channel)
                        await channel_manager.send_to_websocket(websocket, {
                            "type": MessageType.ACK.value,
                            "channel": new_channel,
                            "message": f"Subscribed to {new_channel}"
                        })
                elif msg_type == MessageType.UNSUBSCRIBE.value:
                    old_channel = message.get("channel")
                    if old_channel:
                        await channel_manager.unsubscribe(websocket, old_channel)
                        await channel_manager.send_to_websocket(websocket, {
                            "type": MessageType.ACK.value,
                            "channel": old_channel,
                            "message": f"Unsubscribed from {old_channel}"
                        })
                else:
                    # Echo/acknowledge other messages
                    await channel_manager.send_to_websocket(websocket, {
                        "type": MessageType.ACK.value,
                        "received_type": msg_type
                    })

            except json.JSONDecodeError:
                await channel_manager.send_to_websocket(websocket, {
                    "type": MessageType.ERROR.value,
                    "message": "Invalid JSON"
                })

    except WebSocketDisconnect:
        channel_manager.disconnect(websocket)


@router.websocket("/alerts")
async def alerts_channel(websocket: WebSocket):
    """
    Global alerts channel for real-time notifications.

    Receives:
    - alert_notification: New alert triggered
    """
    await channel_manager.connect(websocket)
    await channel_manager.subscribe(websocket, "alerts")

    await channel_manager.send_to_websocket(websocket, {
        "type": MessageType.ACK.value,
        "channel": "alerts",
        "message": "Subscribed to alert notifications"
    })

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == MessageType.PING.value:
                    await channel_manager.send_to_websocket(websocket, {
                        "type": MessageType.PONG.value
                    })
                else:
                    await channel_manager.send_to_websocket(websocket, {
                        "type": MessageType.ACK.value
                    })
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        channel_manager.disconnect(websocket)


@router.websocket("/jobs/{job_id}")
async def job_channel(websocket: WebSocket, job_id: str):
    """
    Job-specific channel for progress tracking.

    Receives:
    - job_progress: Progress percentage and status updates
    """
    await channel_manager.connect(websocket)
    channel = f"jobs:{job_id}"
    await channel_manager.subscribe(websocket, channel)

    await channel_manager.send_to_websocket(websocket, {
        "type": MessageType.ACK.value,
        "channel": channel,
        "job_id": job_id,
        "message": f"Tracking job {job_id}"
    })

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == MessageType.PING.value:
                    await channel_manager.send_to_websocket(websocket, {
                        "type": MessageType.PONG.value
                    })
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        channel_manager.disconnect(websocket)


@router.get("/stats")
async def get_channel_stats():
    """Get WebSocket channel statistics."""
    return channel_manager.get_stats()


# Helper functions for broadcasting from other parts of the application

async def broadcast_scoring_update(rfp_id: str, scores: dict):
    """Broadcast scoring update to RFP channel."""
    await channel_manager.broadcast_to_channel(f"rfp:{rfp_id}", {
        "type": MessageType.SCORING_UPDATE.value,
        "rfp_id": rfp_id,
        "data": scores
    })


async def broadcast_pricing_update(rfp_id: str, pricing: dict):
    """Broadcast pricing update to RFP channel."""
    await channel_manager.broadcast_to_channel(f"rfp:{rfp_id}", {
        "type": MessageType.PRICING_UPDATE.value,
        "rfp_id": rfp_id,
        "data": pricing
    })


async def broadcast_compliance_update(rfp_id: str, compliance: dict):
    """Broadcast compliance update to RFP channel."""
    await channel_manager.broadcast_to_channel(f"rfp:{rfp_id}", {
        "type": MessageType.COMPLIANCE_UPDATE.value,
        "rfp_id": rfp_id,
        "data": compliance
    })


async def broadcast_job_progress(job_id: str, progress: int, status: str, **kwargs):
    """Broadcast job progress update."""
    await channel_manager.broadcast_to_channel(f"jobs:{job_id}", {
        "type": MessageType.JOB_PROGRESS.value,
        "job_id": job_id,
        "progress": progress,
        "status": status,
        **kwargs
    })


async def broadcast_alert_notification(notification: dict):
    """Broadcast alert notification to all subscribers."""
    await channel_manager.broadcast_to_channel("alerts", {
        "type": MessageType.ALERT_NOTIFICATION.value,
        "notification": notification
    })
