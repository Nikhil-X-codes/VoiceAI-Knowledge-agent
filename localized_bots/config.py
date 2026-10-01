from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class MarketConfig:
    market: Literal["ph", "id"]
    sector: str
    asr_language: str | None
    tts_voice: str
    default_register: str
    system_prompt: str
    records: tuple[dict[str, str], ...]


PH_PROMPT = """You are a Philippines life-insurance premium reminder assistant.
Speak warmly and respectfully using po or opo when natural. Keep every reply under two short sentences.
Flow: verify identity, confirm the premium and policy concern, offer GCash, bank, or Bayad options,
then save a callback or escalate. Use policy and product facts only from the Philippines KB evidence.
If evidence is not found, say you do not have that information and offer a callback or human agent.
Escalate disputes, repeated anger, or a human request. Never guess."""

ID_PROMPT = """Anda adalah asisten pengingat cicilan multifinance di Indonesia.
Gunakan bahasa yang hangat dan sopan; pilih Bapak/Ibu untuk formal atau Kak untuk santai.
Setiap jawaban maksimal dua kalimat pendek. Gunakan hanya bukti dari KB Indonesia untuk fakta produk.
Jika bukti tidak ditemukan, katakan informasi belum tersedia dan tawarkan callback atau petugas manusia.
Eskalasi untuk sengketa, kemarahan berulang, atau permintaan petugas manusia. Jangan menebak."""

PH_RECORDS = (
    {"record_id": "ph_policy_001", "topic": "premium", "text": "Pembayaran premi dapat dilakukan melalui GCash, bank, atau Bayad centers."},
    {"record_id": "ph_policy_002", "topic": "coverage", "text": "Perubahan beneficiary atau rider harus dikonfirmasi melalui layanan resmi."},
    {"record_id": "ph_policy_003", "topic": "lapse", "text": "Untuk risiko lapse, nasabah perlu meminta bantuan layanan resmi mengenai opsi pemulihan polis."},
)

ID_RECORDS = (
    {"record_id": "id_policy_001", "topic": "payment", "text": "Pembayaran cicilan dapat dilakukan melalui transfer, minimarket, atau e-wallet."},
    {"record_id": "id_policy_002", "topic": "late_fee", "text": "Denda dan tanggal jatuh tempo mengikuti jadwal pembiayaan yang berlaku."},
    {"record_id": "id_policy_003", "topic": "tenor", "text": "Perubahan tenor atau angsuran perlu dikonfirmasi melalui layanan resmi."},
)

MARKETS = {
    "ph": MarketConfig("ph", "life insurance premium reminder", "tl", "fil-PH-BlessicaNeural", "respectful", PH_PROMPT, PH_RECORDS),
    "id": MarketConfig("id", "multifinance installment reminder", "id", "id-ID-GadisNeural", "formal", ID_PROMPT, ID_RECORDS),
}


def get_market_config(market: str, register: str | None = None) -> MarketConfig:
    key = (market or "").lower()
    if key not in MARKETS:
        raise ValueError(f"Unsupported market: {market}")
    config = MARKETS[key]
    if register in (None, config.default_register):
        return config
    if key == "id" and register == "colloquial":
        return MarketConfig(config.market, config.sector, config.asr_language, "id-ID-ArdiNeural", register, config.system_prompt, config.records)
    if key == "ph" and register in ("taglish", "english"):
        language = None if register == "taglish" else "en"
        voice = "en-US-JennyNeural" if register == "english" else config.tts_voice
        return MarketConfig(config.market, config.sector, language, voice, register, config.system_prompt, config.records)
    raise ValueError(f"Unsupported register '{register}' for market '{market}'")
