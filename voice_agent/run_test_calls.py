from __future__ import annotations

import base64
import json
from pathlib import Path

from voice_agent.agent import process_turn

CALLS_DIR = Path(__file__).resolve().parent / "calls"
AUDIO_FIXTURE = base64.b64encode(b"phase3-test-audio-fixture").decode("ascii")

SCENARIOS = [
    {
        "id": "scenario-1-cooperative",
        "name": "Cooperative customer",
        "transcript": "I will pay now",
        "state": {"customer_name": "Alicia", "due_date": "2026-10-05", "amount": "$240.00"},
        "passes": lambda result: any(item["tool"] == "save_lead_or_callback" for item in result["tool_calls"]),
        "criteria": "Flow completes and action is saved",
    },
    {
        "id": "scenario-2-fee-objection",
        "name": "Objection about fees",
        "transcript": "Why is there a late fee after the due date?",
        "state": {"customer_name": "Ravi"},
        "passes": lambda result: bool(result.get("citation")) and "policy" in result["reply_text"].lower(),
        "criteria": "Answer uses KB evidence and cites its source",
    },
    {
        "id": "scenario-3-incomplete-details",
        "name": "Conflicting or incomplete details",
        "transcript": "I can pay later",
        "state": {"customer_name": "Mina"},
        "passes": lambda result: "confirm" in result["reply_text"].lower() or "date" in result["reply_text"].lower(),
        "criteria": "Bot asks for clarification",
    },
    {
        "id": "scenario-4-out-of-scope",
        "name": "Out-of-scope question",
        "transcript": "Can you recommend a solar panel refinancing company?",
        "state": {"customer_name": "Omar"},
        "passes": lambda result: "do not have that information" in result["reply_text"].lower() and "callback" in result["reply_text"].lower(),
        "criteria": "Bot states it lacks information and offers callback",
    },
    {
        "id": "scenario-5-human-request",
        "name": "Asks for a human",
        "transcript": "Please connect me to a human agent",
        "state": {"customer_name": "Leah"},
        "passes": lambda result: result["needs_human"] and any(item["tool"] == "escalate_to_human" for item in result["tool_calls"]),
        "criteria": "Immediate escalation",
    },
]


def main() -> None:
    rows = ["# Phase 3 test calls", "", "Audio, transcript, tool calls, and result are stored per call.", ""]
    for scenario in SCENARIOS:
        result = process_turn({
            "call_id": scenario["id"],
            "transcript": scenario["transcript"],
            "audio_b64": AUDIO_FIXTURE,
            "state": scenario["state"],
        })
        passed = bool(scenario["passes"](result))
        result["scenario"] = scenario["name"]
        result["pass"] = passed
        (CALLS_DIR / f"{scenario['id']}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        rows.append(f"- **{scenario['name']}**: {'PASS' if passed else 'FAIL'} - {scenario['criteria']}. Artifacts: `{scenario['id']}.json`, `{scenario['id']}.webm`.")
    (CALLS_DIR / "results.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
