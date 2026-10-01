from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

FIELDS = [
    "call_id", "chunk_index", "t_audio_in", "t_asr_done", "t_signal_done",
    "t_llm_done", "t_displayed", "asr_ms", "signal_ms", "llm_nudge_ms",
    "delivery_ms", "end_to_end_ms",
]


def write_latency_row(
    output_csv: str | Path,
    call_id: str,
    chunk_index: int,
    t_audio_in: float,
    t_asr_done: float,
    t_signal_done: float,
    t_llm_done: float,
    t_displayed: float,
) -> dict[str, Any]:
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "call_id": call_id,
        "chunk_index": chunk_index,
        "t_audio_in": t_audio_in,
        "t_asr_done": t_asr_done,
        "t_signal_done": t_signal_done,
        "t_llm_done": t_llm_done,
        "t_displayed": t_displayed,
        "asr_ms": (t_asr_done - t_audio_in) * 1000,
        "signal_ms": (t_signal_done - t_asr_done) * 1000,
        "llm_nudge_ms": (t_llm_done - t_signal_done) * 1000,
        "delivery_ms": (t_displayed - t_llm_done) * 1000,
        "end_to_end_ms": (t_displayed - t_audio_in) * 1000,
    }
    exists = output_csv.exists()
    with output_csv.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
    return row


def latency_report(input_csv: str | Path) -> dict[str, dict[str, float]]:
    values: dict[str, list[float]] = {name: [] for name in ("asr_ms", "signal_ms", "llm_nudge_ms", "delivery_ms", "end_to_end_ms")}
    with Path(input_csv).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for name in values:
                values[name].append(float(row[name]))
    return {
        name: {
            "p50_ms": round(float(np.percentile(samples, 50)), 3) if samples else 0.0,
            "p95_ms": round(float(np.percentile(samples, 95)), 3) if samples else 0.0,
        }
        for name, samples in values.items()
    }
