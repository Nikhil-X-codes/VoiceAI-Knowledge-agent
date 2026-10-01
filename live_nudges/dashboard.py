from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse
except Exception:  # pragma: no cover
    FastAPI = None
    WebSocket = Any
    WebSocketDisconnect = Exception


class NudgeHub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.clients.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.clients.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        message = json.dumps(payload)
        stale = []
        for client in self.clients:
            try:
                await client.send_text(message)
            except Exception:
                stale.append(client)
        for client in stale:
            self.disconnect(client)


hub = NudgeHub()
app = FastAPI(title="Live Nudge Dashboard") if FastAPI is not None else None
_producer = None
STATIC_PAGE = Path(__file__).resolve().parent / "static" / "index.html"

if app is not None:
    @app.get("/")
    async def dashboard() -> FileResponse:
        return FileResponse(STATIC_PAGE, media_type="text/html")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/publish")
    async def publish(payload: dict[str, Any]) -> dict[str, Any]:
        global _producer
        if _producer is None or payload.get("reset"):
            from live_nudges.pipeline import LiveNudgeProducer
            _producer = LiveNudgeProducer(payload.get("call_state"))
        elif payload.get("call_state"):
            _producer.call_state.update(payload["call_state"])
        return await _producer.ingest(
            payload.get("speaker", "customer"),
            payload.get("transcript", ""),
            asr_confidence=float(payload.get("asr_confidence", 1.0)),
            dashboard_hub=hub,
        )

    @app.websocket("/ws/nudges")
    async def nudges(websocket: WebSocket) -> None:
        await hub.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            hub.disconnect(websocket)
