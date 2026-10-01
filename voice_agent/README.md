# Phase 3 Voice Agent

This module implements the call flow for the customer reminder assistant.

## Flow

1. Browser captures microphone audio with MediaRecorder.
2. A lightweight VAD cuts the utterance after silence.
3. Audio is posted to POST /turn.
4. The server logs the call, transcribes the utterance, applies the reminder flow, and returns a reply.
5. The reply is read aloud with edge-tts and the transcript is shown live in the browser.

## Conversation flow

- Greeting and identity check
- Confirm purpose: installment due soon
- Confirm due date and installment amount using KB evidence
- Ask intent: pay now / promise date / needs help / dispute
- Handle objections and escalate if needed
- Close with summary and fallback escalation

## System prompt and tools

The short production prompt is exposed as `SYSTEM_PROMPT` in `agent.py`. It contains the role, tone, flow, business rules, KB-only fact policy, no-information fallback, escalation rules, and the two-sentence voice limit; it contains no FAQ content.

The tool contract includes:

- `search_kb(query)`: returns retrieved text and source citation.
- `escalate_to_human(reason)`: logs the escalation and returns a handoff message.
- `save_lead_or_callback(name, intent, promised_date, notes)`: writes `calls/leads.json` and `calls/mock_crm_summary.json`.

`run_groq_tool_turn` provides Groq function-calling with these schemas when a Groq client is configured. The local deterministic flow remains available for offline tests.

## Test calls

Run all five required scenarios with:

```powershell
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m voice_agent.run_test_calls
```

Results are recorded in [calls/results.md](calls/results.md). Each scenario has a JSON transcript and tool log plus a WebM audio fixture.

## Local run

```powershell
cd "d:\Projects\AI assignment\ai-assessment"
& "d:/Projects/AI assignment/.venv-1/Scripts/python.exe" -m uvicorn voice_agent.agent:app --host 0.0.0.0 --port 8001
```

Then use the browser example in web_demo.html to capture mic input.
