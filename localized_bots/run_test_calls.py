from __future__ import annotations

import asyncio
import json
from pathlib import Path

from localized_bots.config import get_market_config
from voice_agent.agent import process_turn, synthesize_speech

CALLS_DIR = Path(__file__).resolve().parent / "calls"

SCENARIOS = [
    {
        "id": "ph-01-cooperative",
        "market": "ph",
        "register": "taglish",
        "transcript": "I want to pay my premium with GCash, po.",
        "criteria": "Cooperative customer gets a local payment response",
        "passes": lambda result: result["kb"]["found"] and "GCash" in result["reply_text"],
    },
    {
        "id": "ph-02-sector-objection",
        "market": "ph",
        "register": "respectful",
        "transcript": "Can I update my beneficiary or rider?",
        "criteria": "Sector objection uses life-insurance KB evidence",
        "passes": lambda result: result["kb"]["found"] and "beneficiary" in result["reply_text"],
    },
    {
        "id": "id-01-mixed-finance",
        "market": "id",
        "register": "formal",
        "transcript": "Bagaimana pembayaran cicilan dengan e-wallet?",
        "criteria": "Mixed finance terms return Indonesian payment guidance",
        "passes": lambda result: result["kb"]["found"] and "e-wallet" in result["reply_text"],
    },
    {
        "id": "id-02-colloquial",
        "market": "id",
        "register": "colloquial",
        "transcript": "Kak, gimana bayar cicilan?",
        "criteria": "Colloquial customer receives Kak register",
        "passes": lambda result: result["kb"]["found"] and "Kak" in result["reply_text"],
    },
    {
        "id": "id-03-human-escalation",
        "market": "id",
        "register": "formal",
        "transcript": "Saya ingin bicara dengan petugas manusia.",
        "criteria": "Human request escalates immediately in Indonesian",
        "passes": lambda result: result["needs_human"] and "petugas" in result["reply_text"],
    },
    {
        "id": "id-04-regional-accent",
        "market": "id",
        "register": "colloquial",
        "language": "jw",
        "transcript": "Gajiku belum masuk, piye cicilane?",
        "criteria": "Javanese-hint path preserves Indonesian fallback and language metadata",
        "passes": lambda result: result["asr_language"] == "jw" and "Maaf" in result["reply_text"],
    },
]


def main() -> None:
    CALLS_DIR.mkdir(parents=True, exist_ok=True)
    rows = [
        "# Phase 4 localized test calls",
        "",
        "These are transcript and TTS fixtures. Native-speaker recordings remain pending for ASR quality measurement.",
        "",
    ]
    for scenario in SCENARIOS:
        payload = {
            "call_id": scenario["id"],
            "market": scenario["market"],
            "register": scenario["register"],
            "language": scenario.get("language"),
            "transcript": scenario["transcript"],
        }
        result = process_turn({key: value for key, value in payload.items() if value is not None})
        audio = asyncio.run(synthesize_speech(result["reply_text"], result["tts_voice"]))
        audio_path = CALLS_DIR / f"{scenario['id']}.mp3"
        audio_path.write_bytes(audio)
        result["scenario"] = scenario["criteria"]
        result["audio_path"] = audio_path.name
        result["pass"] = bool(scenario["passes"](result))
        (CALLS_DIR / f"{scenario['id']}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        rows.append(f"- **{scenario['id']}**: {'PASS' if result['pass'] else 'FAIL'} - {scenario['criteria']}. Artifacts: `{scenario['id']}.json`, `{audio_path.name}`.")
    (CALLS_DIR / "results.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
