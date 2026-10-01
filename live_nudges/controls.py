from __future__ import annotations

import re
from typing import Any

from live_nudges.nudges import NUDGE_TEMPLATES, PRIORITY_ORDER


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _similar_evidence(left: str, right: str, threshold: float = 0.6) -> bool:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return False
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens) >= threshold


class NudgeController:
    def __init__(
        self,
        confidence_threshold: float = 0.7,
        cooldown_seconds: float = 30.0,
        expiry_seconds: float = 20.0,
        max_active: int = 2,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.cooldown_seconds = cooldown_seconds
        self.expiry_seconds = expiry_seconds
        self.max_active = max_active
        self.active: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []

    def _prune(self, now: float) -> None:
        self.active = [item for item in self.active if item["expires_at"] > now]

    def _sentiment_supported(self, signal: dict[str, Any], turns: list[dict[str, Any]], call_state: dict[str, Any]) -> bool:
        if signal.get("signal") != "frustration":
            return True
        low_confidence = bool(call_state.get("noisy")) or any(
            turn.get("speaker") == "customer" and float(turn.get("asr_confidence", 1.0)) < 0.7
            for turn in turns[-3:]
        )
        if not low_confidence:
            return True
        frustration_terms = ("angry", "frustrated", "upset", "ridiculous", "not fair", "terrible")
        supporting_turns = sum(
            any(term in str(turn.get("text", "")).lower() for term in frustration_terms)
            for turn in turns[-3:]
            if turn.get("speaker") == "customer"
        )
        return supporting_turns >= 2

    def accept(
        self,
        signals: list[dict[str, Any]],
        now: float,
        turns: list[dict[str, Any]] | None = None,
        call_state: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        turns = turns or []
        call_state = call_state or {}
        self._prune(now)
        ranked = sorted(signals, key=lambda item: (PRIORITY_ORDER.get(item.get("priority", "medium"), 1), -float(item.get("confidence", 0))))
        accepted: list[dict[str, Any]] = []
        for signal in ranked:
            name = signal.get("signal")
            topic = signal.get("topic", name)
            confidence = float(signal.get("confidence", 0))
            if name not in NUDGE_TEMPLATES or confidence < self.confidence_threshold:
                continue
            if name == "compliance_gap" and call_state.get("required_disclosure_spoken"):
                continue
            if not self._sentiment_supported(signal, turns, call_state):
                continue
            if any(item.get("topic") == topic for item in self.active + accepted):
                continue
            previous = next((item for item in reversed(self.history) if item.get("topic") == topic), None)
            if previous:
                if now - previous["emitted_at"] < self.cooldown_seconds:
                    continue
                if _similar_evidence(previous.get("evidence", ""), signal.get("evidence", "")):
                    continue
            item = {
                "text": NUDGE_TEMPLATES[name],
                "signal": name,
                "priority": signal.get("priority", "medium"),
                "confidence": confidence,
                "topic": topic,
                "evidence": signal.get("evidence", ""),
                "emitted_at": now,
                "expires_at": now + self.expiry_seconds,
            }
            self.active.append(item)
            self.history.append(item)
            accepted.append(item)
            if len(self.active) >= self.max_active:
                break
        return accepted
