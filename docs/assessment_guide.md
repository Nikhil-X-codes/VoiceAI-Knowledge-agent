# AI Engineer Assessment: Free-Stack Implementation Guide (Groq + Open Source)

**Rule for this plan:** every tool is free (no credit card). Groq provides speech-to-text and the LLM; everything else is open source or runs locally.

> Free-tier limits change. Before you start, open **console.groq.com → Limits** and confirm the numbers below for your own account. Those pages are the source of truth.

---

## 1. Free Tech Stack

| Layer | Tool | Cost | Notes |
| --- | --- | --- | --- |
| LLM (voice agent) | Groq `llama-3.3-70b-versatile` | Free | Best quality, but small daily token cap (about 100K tokens/day) |
| LLM (signals, nudges, classifiers) | Groq `llama-3.1-8b-instant` | Free | Highest daily limits (about 14,400 requests/day, 500K tokens/day); fast, good for Q4 |
| ASR (speech-to-text) | Groq `whisper-large-v3` / `whisper-large-v3-turbo` | Free | Supports English, Tagalog (`tl`), Indonesian (`id`), Javanese (`jw`) |
| ASR fallback | `faster-whisper` (local, `small` model) | Free | Use when Groq limit is hit; runs on CPU |
| TTS | `edge-tts` (Python) | Free | Native voices: `fil-PH-BlessicaNeural`, `fil-PH-AngeloNeural`, `id-ID-GadisNeural`, `id-ID-ArdiNeural`, `en-US-*` |
| TTS fallback | `gTTS` or browser `speechSynthesis` | Free | Supports `tl` and `id`; lower quality |
| Voice platform | **Self-built web voice agent** (FastAPI + browser mic) | Free | Paid platforms (Vapi/Retell) not needed. The brief allows a web calling interface |
| Embeddings | `sentence-transformers`: `intfloat/multilingual-e5-small` | Free, local | Handles English, Tagalog, Bahasa |
| Vector DB | ChromaDB (local, persistent) | Free |  |
| Keyword search | `rank_bm25` | Free | For hybrid search |
| Scraping / parsing | `trafilatura`, `BeautifulSoup`, `pdfplumber`, `PyMuPDF`, `pytesseract` | Free |  |
| PII | Microsoft Presidio + regex | Free |  |
| Dedup | `datasketch` (MinHash) or embedding cosine | Free |  |
| Backend | Python 3.11, FastAPI, WebSockets, `uvicorn` | Free |  |
| Dashboard | Single HTML page + WebSocket | Free |  |
| Hosting | Run locally; share web demo with `cloudflared` tunnel or ngrok free | Free |  |
| Diagrams | Mermaid / draw.io | Free |  |

### Groq free-tier budgeting (important)

| Concern | Plan |
| --- | --- |
| 70B model has a small daily token cap | Use 70B **only** for the live voice agent calls. Use 8B for everything else (Q4 signals, classification, QA) |
| Whisper has a per-minute request cap (about 20 req/min) | In Q4, send chunks every 3 s or longer, or use local `faster-whisper` |
| Rate limits are per organization, not per API key | Do not create many keys to work around them |
| Hitting a 429 error | Add retry with backoff, then fall back to the 8B model or local Whisper |
| Repeated system prompts | Keep the prompt identical across calls so caching helps |
| Keep prompts short | The KB is retrieved, not pasted, which also saves tokens |

---

## 2. Final Architecture

```
                    ┌───────────────────────────┐
 Browser mic ──────▶│  FastAPI voice server      │
 (web call page)    │  1. VAD / utterance blob   │
                    │  2. Groq Whisper (ASR)     │
                    │  3. LLM agent (Groq)       │──▶ tool: search_kb ──▶ Chroma + BM25
                    │     tools: search_kb,      │                         (local embeddings)
 Browser speaker ◀──│     escalate, save_lead    │──▶ tool: save_lead → leads.json
                    │  4. edge-tts (TTS)         │
                    └───────────────────────────┘

 Recorded call WAV (replayed in real time, chunks)
        │
        ▼
 Streaming ASR ─▶ Signal extractor (8B) ─▶ Nudge engine (thresholds,
 (Groq/faster-whisper)                      dedupe, cooldown, expiry) ─▶ WebSocket ─▶ Dashboard
        └────────── timestamps at every stage ─▶ latency.csv ─▶ P50/P95 report
```

---

## 3. Repository Layout

```
ai-assessment/
├── README.md
├── .env.example            # GROQ_API_KEY=  (no real keys committed)
├── requirements.txt
├── docs/                   # architecture, test tables, reports, limitations
├── kb/
│   ├── raw/                # (gitignored if it contains PII)
│   ├── scripts/            # scrape.py, parse_pdf.py, clean.py, dedupe.py, pii.py, build_index.py
│   ├── data/records.jsonl
│   ├── api.py              # POST /search
│   └── tests/retrieval_tests.md
├── voice_agent/            # Q1 server + web page + prompt + tools
│   ├── server.py  prompt.md  tools.py  static/index.html
│   └── calls/              # audio + transcripts
├── localized_bots/         # Q3 (ph/, id/) configs, prompts, calls
├── live_nudges/            # Q4 pipeline, dashboard, latency reports
└── samples/                # sample inputs
```

---

## 4. Phase-by-Phase Plan (48 Hours)

| Phase | Hours | Output |
| --- | --- | --- |
| 1. Setup | 0-3 | Repo, Groq key, tools installed, use case fixed |
| 2. Knowledge base (Q2) | 3-14 | Clean records, index, search API, 5+ tests |
| 3. Voice agent (Q1) | 14-24 | Web-callable bot, 5 recorded calls |
| 4. Native-language bots (Q3) | 24-34 | PH and ID bots, 4 calls, localization evidence |
| 5. Live nudges (Q4) | 34-43 | Real-time pipeline, latency report |
| 6. Packaging | 43-48 | README, diagram, video |

---

### Phase 1: Setup (Hours 0-3)

1. Create the repo and folders above. `.gitignore`: `.env`, `kb/raw/`, `*.wav` containing real voices, `chroma_db/`.
2. Get a free Groq key at console.groq.com. Put it in `.env`; commit only `.env.example`.
3. Install:

   ```bash
   pip install fastapi uvicorn groq edge-tts sentence-transformers chromadb rank_bm25 \
       trafilatura beautifulsoup4 pdfplumber pymupdf presidio-analyzer presidio-anonymizer \
       datasketch faster-whisper websockets python-dotenv pandas numpy
   python -m spacy download en_core_web_sm
   ```
4. Smoke-test: one Groq chat call, one Groq Whisper call, one `edge-tts` file for `fil-PH` and `id-ID`.
5. **Choose the use case:** *Loan pre-due reminder* (reuses naturally for the Indonesia bot).
6. Write `docs/scope.md`: customer type, script, business rules (e.g., reminder 3 days before due date; late fee rule; options: pay now, promise date, request extension; escalate if dispute or anger).
7. Collect source content: a public finance website, 2-3 PDFs (terms, fee schedule), a rules table, a form. Include duplicates and some PII-like text on purpose so you can show cleaning.

**Done when:** all three APIs respond and sources are saved.

---

### Phase 2: Knowledge Base, Q2 (Hours 3-14)

**2.1 Extraction**

- Websites: `trafilatura.fetch_url` + `extract` (removes menus/footers); fall back to BeautifulSoup. JS-heavy pages: save the HTML manually or use Playwright (free).
- PDFs: `pdfplumber` for text/tables, PyMuPDF for speed; `pytesseract` for scanned pages.
- Log every source in `sources.csv` (ref, type, date fetched, method, status).
- Failures go in `extraction_errors.csv`: empty text, 403/404, garbled encoding, broken tables. Flag source errors, such as two documents giving different fee numbers.

**2.2 Cleaning**

- Remove nav text, headers, footers, cookie banners, repeated boilerplate (drop lines that appear on more than 50% of pages).
- Normalize: dates to `YYYY-MM-DD`; terminology map (`EMI` / `monthly payment` → `installment`); consistent category names and form field names.
- Deduplicate: exact via SHA-256, near-duplicate via MinHash (Jaccard above 0.85) or embedding cosine above 0.92. Keep one canonical record and write the rest to `duplicates_log.csv`.
- PII: Presidio plus regex (phones, emails, ID numbers, names, addresses) replaced by `[PHONE]`, `[EMAIL]`, `[NAME]`. Set `pii: true` on records that contained PII before masking. Never index raw PII.

**2.3 Schema (sample record)**

```json
{
  "record_id": "kb_policy_001",
  "title": "Late Payment Fee Rules",
  "content": "A late fee applies when an installment is unpaid after the due date...",
  "category": "policy",
  "subcategory": "late_fees",
  "source": {"type": "pdf", "ref": "loan_terms.pdf", "page": 3, "url": null},
  "language": "en",
  "market": "global",
  "version": "1.0",
  "status": "active",
  "effective_date": "2026-01-01",
  "pii": false,
  "tags": ["fees", "overdue"]
}
```

**Taxonomy:** `product`, `policy`, `qualification`, `faq`, `objection`, `script_rule`. **IDs:** `kb_<category>_<nnn>`.

**2.4 Chunking, embeddings, index, ranking**

- Chunk by heading/section, 200-400 tokens, 10-15% overlap. Keep tables and Q&A pairs whole. Each chunk inherits record metadata plus `chunk_id`.
- Embeddings: `multilingual-e5-small` (prefix `query:` / `passage:`), stored in a persistent Chroma collection with metadata (category, language, version, status).
- Retrieval: vector top-10 + BM25 top-10 merged with reciprocal rank fusion, return top-3.
- **Threshold:** if the best score is below your tuned cutoff (tune on your test queries), return `{"found": false}`. This drives the bot's "I don't have that information" behavior.
- Citation: every result returns `record_id`, `title`, `source.ref`, `page`, `version`.
- Versioning: new content gets a new `version`; old ones get `status: superseded` and are filtered out of search. Keep a `CHANGELOG.md`.

**2.5 Search API** `POST /search` with `{query, language?, category?}` returning `{found, results:[{record_id, text, score, source}]}`.

**2.6 Retrieval test table (at least 5)**

| # | User question | Retrieved record | Source | Why relevant | Verdict |
| --- | --- | --- | --- | --- | --- |
| 1 | Product question |  |  |  | Correct |
| 2 | Policy (late fee) |  |  |  |  |
| 3 | Qualification |  |  |  |  |
| 4 | FAQ |  |  |  |  |
| 5 | Objection ("fees are too high") |  |  |  |  |
| 6 | Not in KB (negative test) | none | n/a | Threshold returns not found | Correct |

**Done when:** `curl` returns cited, correct results for all tests.

---

### Phase 3: Voice Agent, Q1 (Hours 14-24)

**3.1 How the web call works (free, self-built)**

1. Browser page captures the mic with `MediaRecorder`; a simple energy-based voice detector (or the free `@ricky0123/vad-web` library) cuts an utterance after about 0.8 s of silence.
2. Audio blob is posted to `POST /turn` (or sent via WebSocket).
3. Server: Groq Whisper → text → LLM with tools → reply text → `edge-tts` → MP3 returned.
4. Browser plays the reply. Show the live transcript on the page for the video.
5. Log everything per call: audio, transcript, tool calls, result.

**3.2 Conversation flow** Greeting and identity check → purpose (installment due soon) → confirm due date and amount (via KB/data) → ask intent (pay now / promise date / needs help / dispute) → objection handling → close with summary → fallback and escalation at any step.

**3.3 System prompt (short; no FAQs inside)** Include: role, tone, flow, business rules, and hard rules:

- Answer facts about fees, policies, products only from `search_kb` results.
- If `found: false`, say you do not have that information and offer a callback or human. Never guess.
- Escalate when the customer asks for a human, is angry twice, or raises a dispute.
- Keep each reply under 2 short sentences (voice).

**3.4 Tools (function calling via Groq)**

- `search_kb(query)` → calls Phase 2 API; return text + citation.
- `escalate_to_human(reason)` → logs and plays a handoff message.
- **Business action (choose one):** `save_lead_or_callback(name, intent, promised_date, notes)` writing to `leads.json` plus a mock CRM summary.

**3.5 Test calls (record at least 3; do all 5)**

| # | Scenario | Pass criteria |
| --- | --- | --- |
| 1 | Cooperative customer | Flow completes, action saved |
| 2 | Objection about fees | Answer matches KB, cites source |
| 3 | Conflicting or incomplete details | Bot asks clarification |
| 4 | Out-of-scope question | "I don't have that information" + offer callback |
| 5 | Asks for a human | Immediate escalation |

For each call save the audio, transcript, tool calls, and a pass/fail line in `voice_agent/calls/results.md`.

---

### Phase 4: Native-Language Bots, Q3 (Hours 24-34)

Reuse the Phase 3 server. Add a `market` parameter that selects the prompt, KB records, ASR language hint, and TTS voice.

**4.1 Philippines (life insurance / premium reminder)**

- ASR: Groq Whisper with `language="tl"` for Tagalog and no language hint for Taglish; compare both and report. English calls use `en`.
- TTS: `fil-PH-BlessicaNeural` for Tagalog/Taglish (note that English words may sound Filipino-accented, which is acceptable and often natural); `en-PH` or `en-US` voice for English.
- Terms: premium, policy, beneficiary, rider, lapse, coverage, bank referral. Amounts in PHP; payment via GCash, bank, Bayad centers.
- Tone: respectful ("po/opo"), warm, indirect about overdue premiums.

**4.2 Indonesia (multifinance / installment reminder)**

- ASR: Groq Whisper with `language="id"`; also test `jw` for Javanese-accented clips.
- TTS: `id-ID-GadisNeural` (friendly), `id-ID-ArdiNeural`.
- Terms: cicilan, tenor, denda, DP, jatuh tempo, angsuran, pembiayaan. Amounts in Rupiah (`Rp1.500.000`); date format `15 Oktober 2026`; payment via minimarket, transfer, e-wallet.
- Register: formal (Bapak/Ibu, "Bapak berkenan...") and colloquial ("Kak", "gak apa-apa") switch based on the customer.
- **Regional accent:** record a Javanese or Sundanese-accented speaker (a friend or a free-licensed clip) and report degradation.

**4.3 Localization evidence (3+ per market)**

| Generic English | Literal translation (bad) | Localized (good) | Why |
| --- | --- | --- | --- |
| "Your payment is overdue." | Direct translation, blunt | Soft reminder with "po" / "Bapak/Ibu" and an offer to help | Direct overdue wording sounds rude |
| "Pay via credit card" | Card-first wording | GCash / minimarket / transfer options | Local channels |
| "Amount: 1500000" | Raw number | `PHP 1,500` / `Rp1.500.000` | Local number format |

Add your own, such as honorifics, date formats, and local objections ("wala po akong pambayad", "gaji belum masuk").

**4.4 ASR report template (per market)**

| Item | Philippines | Indonesia |
| --- | --- | --- |
| Provider / model | Groq whisper-large-v3 | Groq whisper-large-v3 |
| Languages tested | en, tl, Taglish | id formal, id colloquial, jw-accented |
| Code-switching behavior |  |  |
| Approx. quality (10 utterances, count errors) |  |  |
| Observed errors (numbers, loanwords, names) |  |  |
| Regional accent result | n/a |  |

**4.5 Fallback and escalation** Write fallback and handoff lines natively in each language and register. Test that they never switch to English unexpectedly.

**4.6 Test calls (2 per market):** cooperative, sector objection, mixed English/finance terms, colloquial speech, human escalation, and (Indonesia) regional accent.

**4.7 Document known gaps:** no native-speaker review yet, compliance rules (Philippine Insurance Commission, Indonesian OJK) not legally reviewed, TTS compromises.

---

### Phase 5: Live Nudges, Q4 (Hours 34-43)

**5.1 Streaming input.** Replay a recorded call (reuse Phase 3/4 audio) at real-time speed. **Free diarization trick:** keep agent audio and customer audio as separate channels and send them as separate chunk streams, so speaker labels are exact.

**5.2 Streaming ASR.** Groq Whisper does not stream natively, so use chunked pseudo-streaming: 3-5 s chunks sent every 3 s (stay under the request cap), carrying about 0.5 s of overlap. If limits bite, use local `faster-whisper` (`small`, int8). Log per-chunk latency.

**5.3 Signal extraction (Llama 3.1 8B, JSON output)** Run on a rolling window (last 3-4 turns, plus call state):

| Signal | Method |
| --- | --- |
| Missed cross-sell | LLM detects mention (e.g., "second vehicle") not followed up |
| Compliance gap | Checklist state machine (required disclosure spoken? yes/no) plus LLM confirm |
| Frustration | LLM sentiment per customer turn + trend of last 3 |
| Payment difficulty | Intent classification |
| Callback need | Intent / phrase detection |

Output: `{signal, confidence, evidence, priority, topic}`.

**5.4 Nudge generation.** Short (under 15 words), actionable. Template-driven where possible (saves LLM calls and latency); LLM only for personalization.

**5.5 Nudge control (anti-spam)**

- Confidence threshold (e.g., 0.7)
- Duplicate suppression (same topic + similar evidence)
- Cooldown per topic (e.g., 30 s)
- Max 2 active nudges; priority ordering; expiry after 20 s
- Compliance nudge repeats only until the disclosure is spoken
- Require 2 supporting turns for sentiment nudges in noisy transcripts (low ASR confidence)

**5.6 Delivery.** FastAPI WebSocket pushes nudges to a one-page HTML dashboard showing live transcript, signals, and nudges with priority colors.

**5.7 Latency measurement.** Timestamp each stage and write one CSV row per chunk: `t_audio_in → t_asr_done → t_signal_done → t_llm_done → t_displayed`

Report P50 and P95 with `numpy.percentile`:

| Component | P50 (ms) | P95 (ms) |
| --- | --- | --- |
| ASR |  |  |
| Signal extraction |  |  |
| LLM / nudge |  |  |
| Delivery |  |  |
| **End-to-end** |  |  |

**5.8 Test scenarios**

| Scenario | Expected |
| --- | --- |
| Missed cross-sell | One nudge |
| Skipped disclosure / risky statement | Compliance reminder |
| Rising frustration | De-escalation nudge |
| Noisy / ambiguous call | None or very few nudges |

**5.9 False-positive analysis.** Hand-label every nudge across test calls (true/false). Report precision, number suppressed by each control, and examples of false alarms.

**5.10 Limitations**

- 10x scale: free-tier rate limits would fail immediately; needs paid capacity, queues, async workers, and a smaller or self-hosted model.
- Noisy audio: ASR errors create false signals; mitigate with confidence gating, multi-turn evidence, noise suppression.
- Chunked ASR adds seconds of delay compared with true streaming engines.

---

### Phase 6: Packaging (Hours 43-48)

**README must contain:** overview, architecture diagram, setup (copy-paste commands), how to run each module, `.env.example`, sample inputs, test results, known limitations, production-improvement plan (paid capacity, true streaming ASR, native-speaker review, monitoring, evaluation sets, PII redaction in recordings, CI, caching).

**Cleanup checklist**

- [ ] No keys, secrets, or real customer data in the repo or git history
- [ ] Recordings, transcripts, and result tables saved under `docs/` or `calls/`
- [ ] README commands tested from a clean clone
- [ ] Retrieval, localization, ASR, latency, and false-positive tables complete

**Video outline (10-15 min)**

1. Overview and architecture
2. KB design and a cited retrieval
3. Live voice agent demo, including "I don't have that information" and human handoff
4. Philippines and Indonesia bots: code-switching, accent notes
5. Live nudges and latency numbers
6. Failures, limitations, production improvements

---

## 5. Master Deliverables Checklist

| Area | Item | Done |
| --- | --- | --- |
| Q1 | Web-callable agent connected to KB | \[ \] |
| Q1 | 3+ calls with audio, transcripts, results | \[ \] |
| Q1 | One business action | \[ \] |
| Q2 | Cleaned, deduped, PII-masked records | \[ \] |
| Q2 | Schema, taxonomy, chunking, versioning docs | \[ \] |
| Q2 | 5+ retrieval tests with verdicts | \[ \] |
| Q3 | PH and ID bots with separate ASR/TTS config | \[ \] |
| Q3 | 3 localization examples per market | \[ \] |
| Q3 | 2 calls per market, ASR report, accent notes, gaps | \[ \] |
| Q4 | Real-time chunked pipeline with nudges | \[ \] |
| Q4 | P50/P95 latency by component | \[ \] |
| Q4 | Nudge controls, false-positive analysis, 4 scenarios | \[ \] |
| Final | README, diagram, `.env.example`, video | \[ \] |

## 6. Free-Stack Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Groq 429 rate limit during demo | Retry/backoff, 8B fallback, local `faster-whisper` fallback; record the demo early |
| 70B daily token cap exhausted | Test with 8B; use 70B only for final recorded calls |
| No native Filipino/Indonesian TTS on Groq | Use `edge-tts` voices; document that it is an unofficial free service and a production risk |
| Groq TTS is English-focused | Use it only if you want an English voice |
| Whisper not truly streaming | Chunking plus overlap; report the resulting latency honestly |
| Taglish misrecognized when language is forced to `tl` | Compare with auto-detect and report |
| Hallucinated answers | Score threshold, "found: false" path, and a negative test on camera |
| No phone number | Web call page satisfies the requirement; mention telephony as a production step |

## 7. If You Run Short on Time (Priority)

1. Q2 KB and search API
2. Q1 voice agent with 3 calls
3. Q4 pipeline with latency numbers
4. Q3 bots (reuse Q1 code; focus on localization evidence)
5. Video and polish (record early with what works)