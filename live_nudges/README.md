# Phase 5 Streaming Input

The streaming foundation replays separate customer and agent audio channels, preserving exact speaker labels without diarization. It chunks PCM/WAV-compatible bytes into 3-second windows with 0.5-second overlap, sends chunks to Groq Whisper, and writes per-chunk ASR timing rows.

## Run a stream

```python
from live_nudges.streaming import run_stream

rows = run_stream(
    {"customer": customer_wav_bytes, "agent": agent_wav_bytes},
    "live_nudges/data/latency.csv",
    language_by_channel={"customer": "id", "agent": "id"},
)
```

The default interval is 3 seconds between chunks. For a live replay, provide real recorded WAV/PCM audio; the test suite injects a no-network transcriber.

## Fallback

If Groq Whisper reaches a rate limit, pass a local `faster-whisper` adapter as `transcriber`. The adapter must accept `(audio_bytes, language)` and return transcript text.

## Signal extraction and nudges

`signals.py` keeps the last four turns and extracts:

- missed cross-sell
- compliance gap
- frustration trend
- payment difficulty
- callback need

When a Groq client is supplied, the rolling window is sent to the configured fast model with JSON output. Without a client, deterministic phrase and call-state rules provide an offline fallback.

```python
from live_nudges.nudges import generate_nudges
from live_nudges.signals import SignalWindow

window = SignalWindow()
window.add("customer", "I cannot pay this week, please call me back.")
signals = window.extract({"required_disclosure_spoken": False})
nudges = generate_nudges(signals)
```

Nudges are template-first, confidence-gated, priority-sorted, deduplicated per response, limited to two active items, and fewer than 15 words.

## Anti-spam controls

`controls.py` applies the Phase 5.5 rules:

- confidence threshold of `0.7`
- same-topic and similar-evidence suppression
- 30-second topic cooldown
- two active nudges maximum
- 20-second expiry
- compliance nudges stop once the disclosure is spoken
- noisy frustration requires two supporting customer turns

## Delivery dashboard

Start the WebSocket dashboard with:

```powershell
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m uvicorn live_nudges.dashboard:app --port 8002
```

Connect a producer to `ws://localhost:8002/ws/nudges` and broadcast payloads through `hub.broadcast(...)`. The page is [static/index.html](static/index.html) and displays transcript text plus high/medium/low priority nudge colors.

The production-facing adapter is [pipeline.py](pipeline.py):

```python
from live_nudges.pipeline import LiveNudgeProducer

producer = LiveNudgeProducer({"required_disclosure_spoken": False})
payload = await producer.ingest("customer", transcript, asr_confidence=0.92)
```

`ingest()` updates the rolling window, extracts signals, applies anti-spam controls, and broadcasts the transcript, signals, and accepted nudges to connected dashboard clients.

## Latency report

`latency.py` writes all five stage timestamps and calculates P50/P95 with `numpy.percentile`. The report format is documented in [docs/latency_report.md](../docs/latency_report.md).

## Scenario evaluation

Run the Phase 5.8 and 5.9 evaluation with:

```powershell
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m live_nudges.run_nudge_scenarios
```

The four scenario verdicts are stored in [data/nudge_results.md](data/nudge_results.md), with machine-readable records in `data/nudge_scenario_results.json` and `data/false_positive_analysis.json`. The report includes hand labels, precision, suppression counts for each anti-spam control, and a noisy-call false-alarm example.

## Current limitation

The browser's WebM blobs are suitable for single-turn upload, but independent streaming chunks should be decoded to PCM/WAV first. This keeps every chunk valid for Whisper and avoids cutting a WebM container at arbitrary byte offsets.
