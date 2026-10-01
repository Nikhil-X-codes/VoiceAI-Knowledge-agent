from __future__ import annotations

from typing import Any

NUDGE_TEMPLATES = {
    "missed_cross_sell": "Ask about the customer's second vehicle needs.",
    "compliance_gap": "Give the required disclosure before continuing.",
    "frustration": "Acknowledge the customer's frustration and slow down.",
    "payment_difficulty": "Offer a payment plan or callback.",
    "callback_need": "Offer to schedule a callback.",
}

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def generate_nudges(signals: list[dict[str, Any]], max_active: int = 2) -> list[dict[str, Any]]:
    ranked = sorted(signals, key=lambda item: (PRIORITY_ORDER.get(item.get("priority", "medium"), 1), -float(item.get("confidence", 0))))
    nudges: list[dict[str, Any]] = []
    seen: set[str] = set()
    for signal in ranked:
        name = signal.get("signal")
        if name in seen or name not in NUDGE_TEMPLATES or float(signal.get("confidence", 0)) < 0.7:
            continue
        text = NUDGE_TEMPLATES[name]
        nudges.append({
            "text": text,
            "signal": name,
            "priority": signal.get("priority", "medium"),
            "confidence": signal.get("confidence", 0),
            "topic": signal.get("topic", name),
        })
        seen.add(name)
        if len(nudges) >= max_active:
            break
    return nudges
