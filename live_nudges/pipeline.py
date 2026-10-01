from __future__ import annotations

import time
from typing import Any

from live_nudges.controls import NudgeController
from live_nudges.dashboard import hub
from live_nudges.nudges import generate_nudges
from live_nudges.signals import SignalWindow, extract_signals


class LiveNudgeProducer:
    """Connect streaming transcripts to signal extraction, controls, and WebSocket delivery."""

    def __init__(self, call_state: dict[str, Any] | None = None, controller: NudgeController | None = None) -> None:
        self.call_state = call_state or {}
        self.window = SignalWindow(max_turns=4)
        self.controller = controller or NudgeController()

    async def ingest(
        self,
        speaker: str,
        transcript: str,
        now: float | None = None,
        asr_confidence: float = 1.0,
        client: Any = None,
        dashboard_hub: Any = hub,
    ) -> dict[str, Any]:
        turns = self.window.add(speaker, transcript)
        if asr_confidence < 1.0:
            turns[-1]["asr_confidence"] = asr_confidence
        signals = extract_signals(turns, self.call_state, client)
        nudges = self.controller.accept(signals, now if now is not None else time.monotonic(), turns, self.call_state)
        payload = {
            "speaker": speaker,
            "transcript": transcript,
            "signals": signals,
            "nudges": nudges,
            "active_nudges": self.controller.active,
        }
        await dashboard_hub.broadcast(payload)
        return payload


async def publish_transcript(
    speaker: str,
    transcript: str,
    call_state: dict[str, Any] | None = None,
    now: float | None = None,
    dashboard_hub: Any = hub,
) -> dict[str, Any]:
    producer = LiveNudgeProducer(call_state)
    return await producer.ingest(speaker, transcript, now=now, dashboard_hub=dashboard_hub)
