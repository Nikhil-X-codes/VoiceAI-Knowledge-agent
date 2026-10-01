# Phase 4 Native-Language Bots

The Phase 3 `/turn` endpoint now accepts `market` and `register`:

```json
{
  "market": "ph",
  "register": "taglish",
  "transcript": "Can I pay my premium with GCash?",
  "use_groq": true
}
```

Supported market settings:

- `ph`: Philippines life-insurance premium reminder, Tagalog ASR (`tl`) by default, Taglish auto-detect, `fil-PH-BlessicaNeural` TTS, respectful `po/opo` style.
- `id`: Indonesia multifinance installment reminder, Indonesian ASR (`id`), formal `Bapak/Ibu` or colloquial `Kak` register, `id-ID-GadisNeural` or `id-ID-ArdiNeural` TTS.

Market policy records are defined in [config.py](config.py) and are returned with citations by the local market KB adapter in [agent.py](agent.py).

Use the shared server:

```powershell
cd "d:\Projects\AI assignment\ai-assessment"
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m uvicorn voice_agent.agent:app --port 8001
```

The ASR comparison and localization evidence are documented in [docs/localization_report.md](../docs/localization_report.md).
