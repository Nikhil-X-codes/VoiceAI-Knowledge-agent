# System Architecture

```mermaid
flowchart LR
    Browser[Browser mic and speaker] --> Voice[FastAPI voice agent :8001]
    Voice --> ASR[Groq Whisper]
    ASR --> Agent[Groq tool-calling agent]
    Agent --> KB[KB search :8000]
    KB --> Retrieval[BM25 plus TF-IDF or local vector retrieval]
    Agent --> Actions[Escalate or save lead]
    Agent --> TTS[Edge TTS]
    TTS --> Browser

    CustomerWav[Customer WAV] --> Stream[Phase 5 chunk replay]
    AgentWav[Agent WAV] --> Stream
    Stream --> Whisper[Groq Whisper chunks]
    Whisper --> Signals[Rolling signal window]
    Signals --> Controls[Confidence, cooldown, dedupe, expiry]
    Controls --> Dashboard[WebSocket dashboard :8002]
    Dashboard --> Browser
    Stream --> Latency[Latency CSV and P50/P95]
```

## Runtime boundaries

- `kb.api:app` owns approved retrieval and citations.
- `voice_agent.agent:app` owns the single-turn and localized `/turn` workflow.
- `live_nudges.dashboard:app` owns dashboard delivery and `/publish` producer input.
- `live_nudges.run_real_stream` replays separate customer and agent WAV channels.
- `.env` contains local secrets and is ignored; `.env.example` is safe to share.
