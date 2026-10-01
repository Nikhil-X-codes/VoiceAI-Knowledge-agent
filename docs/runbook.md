# Application Runbook: Real-Data Verification

This runbook explains how to run the application on Windows and confirm that each phase is working with real input rather than synthetic test fixtures.

## 1. Prerequisites

- Windows PowerShell
- Python 3.13 or a compatible Python 3.11+
- A newly rotated Groq API key
- A microphone for browser testing
- Optional: two uncompressed PCM WAV recordings for streaming tests

Do not paste the Groq key into chat, source files, or terminal output.

## 2. Install and configure

Open PowerShell:

```powershell
cd "d:\Projects\AI assignment\ai-assessment"
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m pip install -r requirements.txt
```

Create or update `.env`:

```env
GROQ_API_KEY=your_rotated_key
GROQ_MODEL=openai/gpt-oss-120b
GROQ_FAST_MODEL=openai/gpt-oss-20b
ASR_MODEL=whisper-large-v3
TTS_VOICE=en-US-JennyNeural
APP_ENV=development
```

Confirm the key is loaded without printing it:

```powershell
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -c "import os; from voice_agent.agent import _groq_client; print('key_present=' + str(bool(os.getenv('GROQ_API_KEY')))); _groq_client(); print('groq_client=created')"
```

Expected:

```text
key_present=True
groq_client=created
```

## 3. Run the services

Use three PowerShell terminals.

### Terminal A: Knowledge base API

```powershell
cd "d:\Projects\AI assignment\ai-assessment"
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m uvicorn kb.api:app --host 127.0.0.1 --port 8000
```

### Terminal B: Voice agent API

```powershell
cd "d:\Projects\AI assignment\ai-assessment"
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m uvicorn voice_agent.agent:app --host 127.0.0.1 --port 8001
```

Wait for this startup to finish before opening the browser. The server builds the KB, loads `intfloat/multilingual-e5-small` once, and runs a warm-up policy search. That one-time model download belongs to startup; it should not happen after the first customer clicks Start.

### Terminal C: Live nudge dashboard

```powershell
cd "d:\Projects\AI assignment\ai-assessment"
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m uvicorn live_nudges.dashboard:app --host 127.0.0.1 --port 8002
```

Open the dashboard at:

```text
http://127.0.0.1:8002/
```

## 4. Verify the knowledge-base API

Run this in a fourth PowerShell terminal:

```powershell
$body = @{ query = "What happens when an installment is unpaid after the due date?"; category = "policy" } | ConvertTo-Json
$result = Invoke-RestMethod -Uri http://127.0.0.1:8000/search -Method Post -ContentType "application/json" -Body $body
$result | ConvertTo-Json -Depth 8
```

Pass criteria:

- HTTP request succeeds
- `found` is `True`
- `results` is not empty
- each result contains `record_id`, `text`, `score`, and `source`
- `source.ref` is present

Failure meanings:

- Connection refused: KB API is not running on port 8000.
- `found=False` for this query: rebuild the KB with `kb/scripts/build_kb.py` and rerun the request.

## 5. Verify the live voice turn with real text

This confirms Groq LLM, tool calling, KB access, and Edge TTS without using a fixture transcript file.

```powershell
$body = @{
  transcript = "Why is there a late fee after the due date?"
  use_groq = $true
  state = @{ customer_name = "Real User" }
} | ConvertTo-Json -Depth 6
$result = Invoke-RestMethod -Uri http://127.0.0.1:8001/turn -Method Post -ContentType "application/json" -Body $body
$result | Select-Object call_id, transcript, reply_text, live_mode, reply_audio_b64, live_error, tts_error | Format-List
```

Pass criteria:

- `live_mode` is `True`
- `reply_text` is non-empty
- `reply_audio_b64` is non-empty
- `live_error` is empty or null
- `tts_error` is empty or null
- the response includes a `search_kb` tool call

Never judge success only by HTTP 200. A response with `live_error` or `tts_error` is a failed live turn.

## 6. Verify real microphone input

Serve the browser page from a local HTTP server:

```powershell
cd "d:\Projects\AI assignment\ai-assessment"
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m http.server 8080 --directory voice_agent
```

Open:

```text
http://127.0.0.1:8080/web_demo.html
```

Then:

1. Allow microphone permission.
2. Click `Start call`.
3. Speak a real sentence, for example: `When is my payment due?`.
4. Click `Stop`.
5. Confirm the page shows a transcript that matches your speech.
6. Confirm the assistant reply is spoken through the browser.
7. Confirm a new JSON call log and audio file exist under `voice_agent/calls`.

Pass criteria:

- Transcript is not the old hardcoded sentence.
- `audio_b64_present` is `True` in the JSON log.
- `live_mode` is `True`.
- `reply_audio_b64` is present in the API response.
- The browser plays the response audio.

## 7. Verify localized real turns

### Philippines

```powershell
$body = @{ market = "ph"; register = "taglish"; language = "tl"; transcript = "Can I pay my premium with GCash?"; use_groq = $true } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8001/turn -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 8
```

Pass criteria: `market=ph`, Filipino TTS voice, respectful `po` wording, and a local payment response.

### Indonesia

```powershell
$body = @{ market = "id"; register = "colloquial"; language = "id"; transcript = "Kak, bagaimana pembayaran cicilan?"; use_groq = $true } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8001/turn -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 8
```

Pass criteria: `market=id`, `register=colloquial`, `tts_voice=id-ID-ArdiNeural`, and Indonesian payment guidance.

## 8. Verify real WAV streaming and ASR latency

Use two separate, uncompressed PCM WAV recordings. Recommended format: 16 kHz, mono, 16-bit.

```powershell
cd "d:\Projects\AI assignment\ai-assessment"
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m live_nudges.run_real_stream `
  --customer "d:\recordings\customer.wav" `
  --agent "d:\recordings\agent.wav" `
  --language en `
  --output "live_nudges\data\real_latency.csv"
```

Pass criteria:

- `chunks` is greater than zero.
- `transcripts` is greater than zero.
- Customer and agent rows both appear in the output.
- `live_nudges/data/real_latency.csv` exists.
- Transcripts match the recordings closely enough for the call language.

This command makes real Groq Whisper requests. It may take approximately three seconds per chunk because of real-time pacing. Use `--no-sleep` only for a fast functional check.

## 9. Verify dashboard nudge delivery

With the dashboard running:

```powershell
$body = @{ speaker = "customer"; transcript = "I also have a second vehicle."; call_state = @{ required_disclosure_spoken = $true } } | ConvertTo-Json -Depth 6
Invoke-RestMethod -Uri http://127.0.0.1:8002/publish -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 8
```

Pass criteria:

- Response contains a `missed_cross_sell` signal.
- Response contains one accepted nudge.
- The same nudge appears in the dashboard browser window.
- Sending the same topic again within 30 seconds produces no new nudge.

## 10. Run the automated suite

```powershell
cd "d:\Projects\AI assignment\ai-assessment"
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m unittest discover
```

The suite validates logic without consuming Groq quota. It is not a replacement for the real-data checks above.

## 11. Inspect evidence

- Phase 3 call logs: `voice_agent/calls/`
- Phase 4 localized calls: `localized_bots/calls/`
- Phase 5 scenario results: `live_nudges/data/nudge_results.md`
- Phase 5 false-positive analysis: `live_nudges/data/false_positive_analysis.json`
- Real streaming latency: `live_nudges/data/real_latency.csv`
- Latency report format: `docs/latency_report.md`

## 12. Troubleshooting

- `GROQ_API_KEY` missing: confirm `.env` is at `ai-assessment/.env`, then restart the API process.
- Model 404: use model IDs returned by `client.models.list()` and update `.env`.
- Whisper rejects audio: use uncompressed PCM WAV for streaming; do not cut WebM bytes directly.
- No dashboard nudge: check that port 8002 is running and post to `/publish`.
- Browser microphone blocked: use `http://127.0.0.1:8080`, allow microphone permission, and avoid opening the HTML through an unsupported file context.
- Empty ASR transcript: check microphone input, WAV format, language hint, and Groq limits.

## 13. Complete native ASR evidence

The repository cannot create truthful native-speaker or regional-accent evidence. The packaged files [tools/record_samples.py](../tools/record_samples.py) and [samples/asr_manifest.json](../samples/asr_manifest.json) contain 20 prompts: 10 Philippines and 10 Indonesia, including Javanese and Sundanese speaker rows. Record them with a real microphone:

```powershell
cd "d:\Projects\AI assignment\ai-assessment"
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" tools/record_samples.py samples/asr_manifest.json --market ph --missing-only
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" tools/record_samples.py samples/asr_manifest.json --market id --missing-only
```

If the root virtual environment does not contain the recorder packages, install them from the project environment:

```powershell
cd "d:\Projects\AI assignment\ai-assessment"
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m pip install sounddevice soundfile numpy
```

The recorder saves real WAV files under `ai-assessment/samples/asr_audio/`. The reference text must match the words actually spoken. The example manifest at [asr_manifest.example.json](../samples/asr_manifest.example.json) can be used for a smaller custom set.

Run:

```powershell
cd "d:\Projects\AI assignment\ai-assessment"
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m localized_bots.asr_benchmark "samples\asr_manifest.json" --output docs/asr_results.json
```

Pass criteria:

- `utterances` equals the number of real recordings.
- `errors` and `mean_wer` are reported.
- `docs/asr_results.json` contains reference text, Whisper hypothesis, language, and WER for every recording.
- Copy the measured counts into [localization_report.md](localization_report.md), including observed number/name/loanword errors and the Indonesia accent result.
