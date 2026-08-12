"""
WebSocket endpoint for real-time dashboard updates.

Clients subscribe to dashboard channels and receive push updates
when underlying data changes or when dashboards are modified.

Protocol:
    Client -> Server: {"action": "subscribe", "dashboard_id": "123"}
    Server -> Client: {"type": "data_update", "dashboard_id": "123", "timestamp": "..."}
    Server -> Client: {"type": "kpi_update", "dashboard_id": "123", "kpi": {...}}
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("gost_bi.websocket")


class DashboardChannel:
    """Manages subscribers for a single dashboard."""

    def __init__(self, dashboard_id: str):
        self.dashboard_id = dashboard_id
        self.subscribers: dict[str, WebSocket] = {}
        self.last_data: dict[str, Any] = {}

    async def subscribe(self, client_id: str, ws: WebSocket) -> None:
        self.subscribers[client_id] = ws
        logger.info(f"Client {client_id} subscribed to dashboard {self.dashboard_id} ({len(self.subscribers)} total)")

        if self.last_data:
            await ws.send_json({
                "type": "initial_state",
                "dashboard_id": self.dashboard_id,
                "data": self.last_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    async def unsubscribe(self, client_id: str) -> None:
        self.subscribers.pop(client_id, None)
        logger.info(f"Client {client_id} unsubscribed from dashboard {self.dashboard_id} ({len(self.subscribers)} remaining)")

    async def broadcast(self, message: dict[str, Any]) -> None:
        self.last_data = message.get("data", self.last_data)
        disconnected: list[str] = []
        for client_id, ws in self.subscribers.items():
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(client_id)
        for cid in disconnected:
            self.subscribers.pop(cid, None)


class DashboardHub:
    """Central hub managing all dashboard channels."""

    def __init__(self):
        self.channels: dict[str, DashboardChannel] = {}

    def get_channel(self, dashboard_id: str) -> DashboardChannel:
        if dashboard_id not in self.channels:
            self.channels[dashboard_id] = DashboardChannel(dashboard_id)
        return self.channels[dashboard_id]

    async def handle_client(self, ws: WebSocket, client_id: str) -> None:
        await ws.accept()
        logger.info(f"WebSocket connected: {client_id}")

        subscribed: list[str] = []

        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await ws.send_json({"type": "error", "message": "Invalid JSON"})
                    continue

                action = msg.get("action", "")

                if action == "subscribe":
                    dash_id = msg.get("dashboard_id", "")
                    if dash_id:
                        channel = self.get_channel(dash_id)
                        await channel.subscribe(client_id, ws)
                        subscribed.append(dash_id)

                elif action == "unsubscribe":
                    dash_id = msg.get("dashboard_id", "")
                    if dash_id in self.channels:
                        await self.channels[dash_id].unsubscribe(client_id)

                elif action == "ping":
                    await ws.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {client_id}")
        finally:
            for dash_id in subscribed:
                if dash_id in self.channels:
                    await self.channels[dash_id].unsubscribe(client_id)

    async def push_update(self, dashboard_id: str, data: dict[str, Any]) -> None:
        """Push a data update to all subscribers of a dashboard."""
        channel = self.get_channel(dashboard_id)
        await channel.broadcast({
            "type": "data_update",
            "dashboard_id": dashboard_id,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def push_kpi(self, dashboard_id: str, kpi: dict[str, Any]) -> None:
        channel = self.get_channel(dashboard_id)
        await channel.broadcast({
            "type": "kpi_update",
            "dashboard_id": dashboard_id,
            "kpi": kpi,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


hub = DashboardHub()
