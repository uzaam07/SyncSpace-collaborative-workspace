import asyncio
from collections import defaultdict
from fastapi import WebSocket

class ConnectionManager:
    # Single-process manager; use Redis pub/sub for multi-worker production deployments.
    def __init__(self):
        self.rooms: dict[int, set[WebSocket]] = defaultdict(set)
        self.lock = asyncio.Lock()

    async def connect(self, workspace_id: int, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.rooms[workspace_id].add(websocket)

    async def disconnect(self, workspace_id: int, websocket: WebSocket):
        async with self.lock:
            room = self.rooms.get(workspace_id)
            if room:
                room.discard(websocket)
                if not room:
                    self.rooms.pop(workspace_id, None)

    async def broadcast(self, workspace_id: int, message: dict):
        async with self.lock:
            connections = list(self.rooms.get(workspace_id, set()))
        stale = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                stale.append(connection)
        for connection in stale:
            await self.disconnect(workspace_id, connection)

manager = ConnectionManager()
