# Real ASR Recordings

This is the canonical directory for the 20 WAV recordings referenced by `samples/asr_manifest.json`.

Expected files:

```text
ph_01.wav through ph_10.wav
id_01.wav through id_10.wav
```

Record them from the repository root:

```powershell
cd "d:\Projects\AI assignment\ai-assessment"
& ".venv-1/Scripts/python.exe" tools/record_samples.py samples/asr_manifest.json --market ph --missing-only
& ".venv-1/Scripts/python.exe" tools/record_samples.py samples/asr_manifest.json --market id --missing-only
```

Recommended format: PCM WAV, 16 kHz, mono, 16-bit. WAV files are intentionally ignored by Git because recordings may contain personal data.
