from __future__ import annotations

import re
from typing import Any

from localized_bots.config import MarketConfig, get_market_config


def search_market_kb(query: str, config: MarketConfig) -> dict[str, Any]:
    normalized_query = query.lower().replace("gimana", "bagaimana").replace("bayar", "pembayaran")
    words = set(re.findall(r"\w+", normalized_query))
    matches = [record for record in config.records if words.intersection(record["text"].lower().split()) or record["topic"] in query.lower()]
    return {
        "found": bool(matches),
        "results": [
            {
                "record_id": record["record_id"],
                "text": record["text"],
                "source": {"ref": f"{config.market}_localized_policy.jsonl", "page": None, "version": "1.0"},
            }
            for record in matches[:3]
        ],
    }


def _short(text: str) -> str:
    return text if text.count(".") < 2 else ".".join(text.split(".")[:2]) + "."


def build_localized_response(transcript: str, market: str, state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or {}
    config = get_market_config(market, state.get("register"))
    text = (transcript or "").strip()
    lower = text.lower()
    evidence = search_market_kb(text, config)
    customer = state.get("customer_name") or ("customer" if config.market == "ph" else "nasabah")

    if any(term in lower for term in ("human", "agent", "representative", "petugas", "manusia")):
        reply = "Opo, ikokonekta ko po kayo sa isang kinatawan ngayon." if config.market == "ph" else "Baik, saya akan menghubungkan Bapak/Ibu dengan petugas kami sekarang."
        return {"reply_text": reply, "phase": "escalation", "needs_human": True, "asr_language": config.asr_language, "tts_voice": config.tts_voice, "kb": evidence, "prompt": config.system_prompt}

    if not evidence["found"]:
        reply = "Paumanhin po, wala po akong sapat na impormasyon. Maaari po akong mag-ayos ng tawag pabalik o maglipat sa isang kinatawan." if config.market == "ph" else "Maaf, informasi itu belum tersedia. Saya dapat mengatur panggilan balik atau menghubungkan Bapak/Ibu dengan petugas."
        return {"reply_text": reply, "phase": "fallback", "needs_human": False, "asr_language": config.asr_language, "tts_voice": config.tts_voice, "kb": evidence, "prompt": config.system_prompt}

    if config.market == "ph":
        if any(term in lower for term in ("premium", "policy", "beneficiary", "rider", "coverage", "gcash", "bayad")):
            if evidence["found"]:
                return {"reply_text": _short(f"Salamat po, {customer}. {evidence['results'][0]['text']}"), "phase": "policy", "needs_human": False, "asr_language": config.asr_language, "tts_voice": config.tts_voice, "kb": evidence, "prompt": config.system_prompt}
            return {"reply_text": "Paumanhin po, wala po akong sapat na impormasyon. Maaari po akong mag-ayos ng tawag pabalik o maglipat sa isang kinatawan.", "phase": "fallback", "needs_human": False, "asr_language": config.asr_language, "tts_voice": config.tts_voice, "kb": evidence, "prompt": config.system_prompt}
        if not evidence["found"]:
            return {"reply_text": "Pasensya na po, wala akong sapat na impormasyon. Maaari akong mag-ayos ng callback o maglipat sa human agent.", "phase": "fallback", "needs_human": False, "asr_language": config.asr_language, "tts_voice": config.tts_voice, "kb": evidence, "prompt": config.system_prompt}
        return {"reply_text": f"Kumusta po, {customer}. Maaari ko pong kumpirmahin ang premium at mga payment option para sa inyo.", "phase": "greeting", "needs_human": False, "asr_language": config.asr_language, "tts_voice": config.tts_voice, "kb": evidence, "prompt": config.system_prompt}

    if any(term in lower for term in ("cicilan", "angsuran", "denda", "jatuh tempo", "tenor", "transfer", "e-wallet")):
        if evidence["found"]:
            honorific = "Kak" if config.default_register == "colloquial" else "Bapak/Ibu"
            return {"reply_text": _short(f"Baik, {honorific}. {evidence['results'][0]['text']}"), "phase": "policy", "needs_human": False, "asr_language": config.asr_language, "tts_voice": config.tts_voice, "kb": evidence, "prompt": config.system_prompt}
        return {"reply_text": "Maaf, informasi itu belum tersedia. Saya bisa mengatur callback atau menghubungkan Bapak/Ibu dengan petugas.", "phase": "fallback", "needs_human": False, "asr_language": config.asr_language, "tts_voice": config.tts_voice, "kb": evidence, "prompt": config.system_prompt}
        if not evidence["found"]:
            return {"reply_text": "Maaf, informasi itu belum tersedia. Saya dapat mengatur panggilan balik atau menghubungkan Bapak/Ibu dengan petugas.", "phase": "fallback", "needs_human": False, "asr_language": config.asr_language, "tts_voice": config.tts_voice, "kb": evidence, "prompt": config.system_prompt}
    return {"reply_text": f"Baik, {customer}. Mohon jelaskan kebutuhan premi atau cicilan Anda.", "phase": "clarify", "needs_human": False, "asr_language": config.asr_language, "tts_voice": config.tts_voice, "kb": evidence, "prompt": config.system_prompt}
