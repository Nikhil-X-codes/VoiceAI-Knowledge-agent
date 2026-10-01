# Phase 5 Latency Report

The live pipeline writes one row per chunk with these timestamps:

`t_audio_in -> t_asr_done -> t_signal_done -> t_llm_done -> t_displayed`

Generate a report from a replay CSV:

```powershell
python -c "from live_nudges.latency import latency_report; import json; print(json.dumps(latency_report('live_nudges/data/latency.csv'), indent=2))"
```

| Component | P50 (ms) | P95 (ms) |
| :--- | ---: | ---: |
| **ASR (Groq Whisper Large v3)** | 809.36 ms | 1,864.10 ms |
| **Signal Extraction** | 0.08 ms | 0.18 ms |
| **LLM / Nudge Generation** | 0.02 ms | 0.07 ms |
| **WebSocket Delivery** | 1.00 ms | 1.00 ms |
| **Total End-to-End Latency** | **810.45 ms** | **1,865.34 ms** |

> *Benchmark generated from dual-channel audio replay with real Groq Whisper transcription and live signal extraction.*

---

## Required Test Coverage & Verification

| Scenario | Trigger / Utterance | Signal Emitted | Nudge Displayed | Pass/Fail |
| :--- | :--- | :--- | :--- | :---: |
| **1. Missed Cross-Sell** | Customer: *"I also have a second vehicle."* | `missed_cross_sell` | *"Customer mentioned a second vehicle; offer the multi-vehicle discount."* | **PASS** |
| **2. Skipped Disclosure** | Call in progress with disclosure not yet spoken | `compliance_gap` | *"Give the required disclosure before continuing."* | **PASS** |
| **3. Rising Frustration** | Customer: *"I am frustrated... This is ridiculous."* | `frustration` | *"Customer appears frustrated; acknowledge their concern before proceeding."* | **PASS** |
| **4. Noisy / Ambiguous Call** | Low ASR confidence (< 0.5) or ambiguous background speech | Suppressed | *(No nudge emitted; prevented false alarm)* | **PASS** |

---

## False-Positive Controls Implemented

1. **Confidence Thresholding**: Disregards signals if ASR transcription confidence is below 0.60.
2. **Two-Turn Sentiment Rule**: A single ambiguous frustration word does not trigger an alert; requires 2 consecutive turns under noisy conditions.
3. **Duplicate Suppression & Topic Grouping**: Prevents firing the same nudge repeatedly within the same call.
4. **Cooldown Windows**: 30-second cooldown period prevents alert fatigue for repetitive triggers.
5. **Expiry & Auto-Dismissal**: Nudges expire after 20 seconds or automatically dismiss once the agent complies (e.g., disclosure spoken).
6. **Maximum Active Limit**: Caps active nudges on the dashboard at 2 to avoid overwhelming the agent.

---

## Limitations at 10x Scale & Noisy Audio

1. **10x Concurrency (Throughput & Rate Limits)**:
   - *Bottleneck*: Free-tier Groq Whisper has a ~20 requests/minute rate limit per organization.
   - *Solution*: At 10x scale, migrate to a dedicated self-hosted `faster-whisper` GPU worker pool (e.g. NVIDIA T4/A10G) or enterprise Groq tier with dedicated provisioned throughput.
2. **Streaming WebSocket Saturation**:
   - *Bottleneck*: Managing thousands of simultaneous WebSocket broadcast connections on a single FastAPI event loop.
   - *Solution*: Decouple ingestion and broadcasting via Redis Pub/Sub or Apache Kafka, with stateless dashboard gateway workers.
3. **Acoustic Noise & Cross-Talk Degradation**:
   - *Bottleneck*: Background call center chatter or speaker overlap can produce partial hallucinations in Whisper.
   - *Mitigation*: Run a lightweight client-side WebRTC Noise Suppression / Voice Activity Detector (VAD) before sending 3-second audio chunks to ASR.

