from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import edge_tts
import numpy as np
import scipy.signal
import soundfile as sf

MANIFEST_PATH = Path(__file__).resolve().parent.parent / "samples" / "asr_manifest.json"
AUDIO_DIR = Path(__file__).resolve().parent.parent / "samples" / "asr_audio"

VOICE_MAP = {
    "ph_01": "en-US-JennyNeural",
    "ph_02": "fil-PH-BlessicaNeural",
    "ph_03": "fil-PH-AngeloNeural",
    "ph_04": "fil-PH-BlessicaNeural",
    "ph_05": "fil-PH-AngeloNeural",
    "ph_06": "fil-PH-BlessicaNeural",
    "ph_07": "fil-PH-AngeloNeural",
    "ph_08": "fil-PH-BlessicaNeural",
    "ph_09": "fil-PH-AngeloNeural",
    "ph_10": "fil-PH-BlessicaNeural",
    "id_01": "id-ID-GadisNeural",
    "id_02": "id-ID-ArdiNeural",
    "id_03": "id-ID-GadisNeural",
    "id_04": "id-ID-ArdiNeural",
    "id_05": "id-ID-GadisNeural",
    "id_06": "id-ID-ArdiNeural",
    "id_07": "id-ID-GadisNeural",
    "id_08": "id-ID-ArdiNeural",
    "id_09": "id-ID-ArdiNeural",
    "id_10": "id-ID-GadisNeural",
}


async def synthesize_item(item_id: str, text: str, voice: str, target_path: Path) -> None:
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_mp3 = Path(tmp.name)
    try:
        communicator = edge_tts.Communicate(text, voice)
        await communicator.save(str(tmp_mp3))
        data, sr = sf.read(str(tmp_mp3))
        # Convert to mono if multi-channel
        if len(data.shape) > 1:
            data = data.mean(axis=1)
        # Resample 24000 -> 16000
        if sr == 24000:
            resampled = scipy.signal.resample_poly(data, 2, 3)
        elif sr != 16000:
            resampled = scipy.signal.resample(data, int(len(data) * 16000 / sr))
        else:
            resampled = data
        target_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(target_path), resampled.astype(np.float32), 16000, subtype="PCM_16")
        print(f"[{item_id}] Saved 16kHz WAV ({len(resampled)/16000:.1f}s) -> {target_path.name}")
    finally:
        tmp_mp3.unlink(missing_ok=True)


async def main() -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    items = manifest.get("items", manifest)

    print(f"Synthesizing {len(items)} audio recordings for ASR manifest...")
    for item in items:
        item_id = item["id"]
        out_path = AUDIO_DIR / f"{item_id}.wav"
        voice = VOICE_MAP.get(item_id, "fil-PH-BlessicaNeural" if item["market"] == "ph" else "id-ID-GadisNeural")
        await synthesize_item(item_id, item["reference"], voice, out_path)
    print("\nAll 20 WAV files generated successfully in samples/asr_audio/!")


if __name__ == "__main__":
    asyncio.run(main())
