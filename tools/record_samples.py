"""Record the scripted ASR utterances one by one.

Setup:   pip install sounddevice soundfile numpy
Run:     python tools/record_samples.py samples/asr_manifest.json
Options: --market ph|id   (record only one market)
         --only id_09     (re-record a single item)
         --missing-only   (skip recordings that already exist)
"""
import argparse
import json
import queue
import sys
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000


def record_until_enter() -> np.ndarray:
    q: "queue.Queue[np.ndarray]" = queue.Queue()

    def callback(indata, frames, time, status):
        q.put(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback):
        input("   Recording... press ENTER to stop. ")
    chunks = []
    while not q.empty():
        chunks.append(q.get())
    return np.concatenate(chunks) if chunks else np.zeros((0, 1), dtype="float32")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("manifest")
    p.add_argument("--market", choices=["ph", "id"])
    p.add_argument("--only")
    p.add_argument("--missing-only", action="store_true")
    args = p.parse_args()

    manifest_path = Path(args.manifest).resolve()
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest_data.get("items", manifest_data) if isinstance(manifest_data, dict) else manifest_data
    for item in items:
        if args.market and item["market"] != args.market:
            continue
        if args.only and item["id"] != args.only:
            continue

        out = Path(item["audio"])
        if not out.is_absolute():
            out = manifest_path.parent / out
        if args.missing_only and out.exists():
            print(f"\n[{item['id']}] already exists, skipping: {out}")
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        while True:
            print(f"\n[{item['id']}] {item['scenario']}  (speaker: {item['speaker']})")
            if item.get("accent") not in (None, "standard"):
                print(f"   >>> Must be spoken by a {item['accent']}-accent speaker <<<")
            print(f'   SAY: "{item["reference"]}"')
            try:
                cmd = input("   ENTER = start, s = skip, q = quit: ").strip().lower()
            except EOFError:
                print("\nInput closed; stopping without losing saved recordings.")
                return
            if cmd == "q":
                sys.exit(0)
            if cmd == "s":
                break
            audio = record_until_enter()
            if len(audio) < SAMPLE_RATE * 0.5:
                print("   Too short, try again.")
                continue
            sf.write(out, audio, SAMPLE_RATE)
            print(f"   Saved {out} ({len(audio) / SAMPLE_RATE:.1f}s)")
            if input("   Keep it? (ENTER = yes, r = redo): ").strip().lower() != "r":
                break
    print("\nDone. Now run the benchmark:")
    print("  python -m localized_bots.asr_benchmark samples/asr_manifest.json --output docs/asr_results.json")


if __name__ == "__main__":
    main()
