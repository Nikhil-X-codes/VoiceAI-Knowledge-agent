from __future__ import annotations

import json
import os
import re
from collections import deque
from typing import Any

SIGNAL_NAMES = {
    "missed_cross_sell",
    "compliance_gap",
    "frustration",
    "payment_difficulty",
    "callback_need",
}

SIGNAL_PROMPT = """Extract only these call signals from the last customer and agent turns:
missed_cross_sell, compliance_gap, frustration, payment_difficulty, callback_need.
Return a JSON array. Each item must contain exactly signal, confidence, evidence, priority, topic.
confidence is 0 to 1; priority is low, medium, or high. Do not invent evidence.
"""


def _signal(signal: str, confidence: float, evidence: str, priority: str, topic: str) -> dict[str, Any]:
    return {
        "signal": signal,
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "evidence": evidence,
        "priority": priority,
        "topic": topic,
    }


def _heuristic_signals(turns: list[dict[str, Any]], call_state: dict[str, Any]) -> list[dict[str, Any]]:
    customer_turns = [turn for turn in turns if turn.get("speaker") == "customer"]
    recent_text = " ".join(str(turn.get("text", "")) for turn in turns[-4:]).lower()
    customer_text = " ".join(str(turn.get("text", "")) for turn in customer_turns[-3:]).lower()
    agent_after_customer = any(
        turn.get("speaker") == "agent" and index > max(
            (index for index, item in enumerate(turns) if item.get("speaker") == "customer" and any(
                phrase in str(item.get("text", "")).lower() for phrase in ("second vehicle", "another car", "second car", "vehicle")
            )),
            default=-1,
        )
        for index, turn in enumerate(turns)
    )
    signals: list[dict[str, Any]] = []

    if any(phrase in customer_text for phrase in ("second vehicle", "another car", "second car")) and not agent_after_customer:
        signals.append(_signal("missed_cross_sell", 0.91, "Customer mentioned another vehicle without a follow-up.", "medium", "cross-sell"))

    if not call_state.get("required_disclosure_spoken", False) and customer_turns:
        signals.append(_signal("compliance_gap", 0.86, "Required disclosure is not marked as spoken.", "high", "disclosure"))

    frustration_terms = ("angry", "frustrated", "upset", "ridiculous", "not fair", "terrible")
    frustration_count = sum(customer_text.count(term) for term in frustration_terms)
    if frustration_count >= 2:
        signals.append(_signal("frustration", 0.88, "Repeated frustration language occurred across recent customer turns.", "high", "de-escalation"))
    elif frustration_count == 1:
        signals.append(_signal("frustration", 0.72, "Customer used frustration language.", "medium", "de-escalation"))

    difficulty_terms = ("cannot pay", "can't pay", "no money", "salary", "gaji belum", "wala akong pambayad", "hirap magbayad")
    if any(term in customer_text for term in difficulty_terms):
        signals.append(_signal("payment_difficulty", 0.9, "Customer indicated difficulty making payment.", "high", "payment support"))

    callback_terms = ("call me back", "callback", "tawag pabalik", "panggilan balik", "later", "next week")
    if any(term in recent_text for term in callback_terms):
        signals.append(_signal("callback_need", 0.84, "Customer requested or implied a later callback.", "medium", "callback"))
    return signals


def _parse_llm_signals(content: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return []
    candidates = parsed if isinstance(parsed, list) else parsed.get("signals", [])
    valid = []
    for item in candidates:
        if not isinstance(item, dict) or item.get("signal") not in SIGNAL_NAMES:
            continue
        valid.append(_signal(
            item["signal"],
            float(item.get("confidence", 0)),
            str(item.get("evidence", "")),
            str(item.get("priority", "medium")),
            str(item.get("topic", item["signal"])),
        ))
    return valid


def extract_signals(
    turns: list[dict[str, Any]],
    call_state: dict[str, Any] | None = None,
    client: Any = None,
) -> list[dict[str, Any]]:
    call_state = call_state or {}
    window = turns[-4:]
    if client is not None:
        messages = [
            {"role": "system", "content": SIGNAL_PROMPT},
            {"role": "user", "content": json.dumps({"turns": window, "call_state": call_state})},
        ]
        response = client.chat.completions.create(
            model=os.getenv("GROQ_FAST_MODEL", "openai/gpt-oss-20b"),
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
        )
        llm_signals = _parse_llm_signals(response.choices[0].message.content or "[]")
        if llm_signals:
            return llm_signals
    return _heuristic_signals(window, call_state)


class SignalWindow:
    def __init__(self, max_turns: int = 4) -> None:
        self.turns: deque[dict[str, Any]] = deque(maxlen=max_turns)

    def add(self, speaker: str, text: str) -> list[dict[str, Any]]:
        self.turns.append({"speaker": speaker, "text": text})
        return list(self.turns)

    def extract(self, call_state: dict[str, Any] | None = None, client: Any = None) -> list[dict[str, Any]]:
        return extract_signals(list(self.turns), call_state, client)
