from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass


@dataclass(frozen=True)
class AudioChunk:
    index: int
    start_seconds: float
    end_seconds: float
    payload: bytes


def chunk_audio(
    audio: bytes,
    sample_rate: int = 16000,
    channels: int = 1,
    sample_width: int = 2,
    chunk_seconds: float = 3.0,
    overlap_seconds: float = 0.5,
) -> list[AudioChunk]:
    if not audio:
        return []
    if chunk_seconds <= 0 or overlap_seconds < 0 or overlap_seconds >= chunk_seconds:
        raise ValueError("overlap_seconds must be non-negative and smaller than chunk_seconds")
    bytes_per_second = sample_rate * channels * sample_width
    chunk_bytes = max(1, int(chunk_seconds * bytes_per_second))
    overlap_bytes = int(overlap_seconds * bytes_per_second)
    step_bytes = max(1, chunk_bytes - overlap_bytes)
    chunks: list[AudioChunk] = []
    start = 0
    index = 0
    while start < len(audio):
        end = min(len(audio), start + chunk_bytes)
        chunks.append(AudioChunk(
            index=index,
            start_seconds=start / bytes_per_second,
            end_seconds=end / bytes_per_second,
            payload=audio[start:end],
        ))
        if end == len(audio):
            break
        start += step_bytes
        index += 1
    return chunks


import io
import wave


def _ensure_wav(audio: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
    if audio.startswith(b"RIFF"):
        return audio
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(audio)
    return buf.getvalue()


def transcribe_chunk(audio: bytes, language: str | None = None, client: Any = None) -> str:
    if client is None:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    wav_payload = _ensure_wav(audio)
    request: dict[str, Any] = {
        "file": ("chunk.wav", wav_payload),
        "model": os.getenv("ASR_MODEL", "whisper-large-v3"),
        "response_format": "json",
    }
    if language and language != "auto":
        request["language"] = language
    result = client.audio.transcriptions.create(**request)
    return (getattr(result, "text", "") or "").strip()


def replay_chunks(
    chunks: Iterable[AudioChunk],
    interval_seconds: float = 3.0,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Iterable[AudioChunk]:
    for position, chunk in enumerate(chunks):
        if position:
            sleep_fn(interval_seconds)
        yield chunk


def run_stream(
    channels: dict[str, bytes],
    output_csv: str | Path,
    call_id: str = "stream-call",
    language_by_channel: dict[str, str | None] | None = None,
    chunk_seconds: float = 3.0,
    overlap_seconds: float = 0.5,
    sample_rate: int = 16000,
    channels_count: int = 1,
    sample_width: int = 2,
    interval_seconds: float = 3.0,
    transcriber: Callable[[bytes, str | None], str] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.perf_counter,
) -> list[dict[str, Any]]:
    language_by_channel = language_by_channel or {}
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    transcriber = transcriber or (lambda audio, language: transcribe_chunk(audio, language))

    for speaker, audio in channels.items():
        chunks = chunk_audio(
            audio,
            sample_rate=sample_rate,
            channels=channels_count,
            sample_width=sample_width,
            chunk_seconds=chunk_seconds,
            overlap_seconds=overlap_seconds,
        )
        for chunk in replay_chunks(chunks, interval_seconds=interval_seconds, sleep_fn=sleep_fn):
            audio_in = clock()
            transcript = transcriber(chunk.payload, language_by_channel.get(speaker))
            asr_done = clock()
            rows.append({
                "call_id": call_id,
                "speaker": speaker,
                "chunk_index": chunk.index,
                "chunk_start_seconds": round(chunk.start_seconds, 3),
                "chunk_end_seconds": round(chunk.end_seconds, 3),
                "t_audio_in": round(audio_in, 6),
                "t_asr_done": round(asr_done, 6),
                "asr_ms": round((asr_done - audio_in) * 1000, 3),
                "transcript": transcript,
            })

    fieldnames = [
        "call_id", "speaker", "chunk_index", "chunk_start_seconds", "chunk_end_seconds",
        "t_audio_in", "t_asr_done", "asr_ms", "transcript",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return rows
