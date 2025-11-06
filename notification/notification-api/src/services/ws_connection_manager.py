import logging
from typing import Dict, List

from fastapi import WebSocket, Request

logger = logging.getLogger(__name__)


class WSConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    def connect(self, user_id: str, websocket: WebSocket):
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        conns = self.active_connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: str):
        for ws in self.active_connections.get(user_id, []):
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.exception(f"Error sending push notification: {str(e)}")

    async def send_to_all_users(self, message: str):
        for _, sockets in self.active_connections.items():
            for ws in sockets:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.exception(f"Error sending push notification: {str(e)}")


def get_connection_manager(request: Request) -> WSConnectionManager:
    return request.app.state.manager
