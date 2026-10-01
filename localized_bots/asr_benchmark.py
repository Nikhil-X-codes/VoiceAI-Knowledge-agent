from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from voice_agent.agent import transcribe_audio


def normalize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def word_error_rate(reference: str, hypothesis: str) -> float:
    expected = normalize(reference)
    actual = normalize(hypothesis)
    previous = list(range(len(actual) + 1))
    for row, expected_word in enumerate(expected, start=1):
        current = [row]
        for column, actual_word in enumerate(actual, start=1):
            substitution = previous[column - 1] + (expected_word != actual_word)
            insertion = current[column - 1] + 1
            deletion = previous[column] + 1
            current.append(min(substitution, insertion, deletion))
        previous = current
    return previous[-1] / max(1, len(expected))


def run(
    manifest_path: Path,
    output_path: Path,
    market: str | None = None,
    only: str | None = None,
) -> list[dict[str, Any]]:
    manifest_path = manifest_path.resolve()
    output_path = output_path.resolve()
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = manifest_data.get("items", manifest_data) if isinstance(manifest_data, dict) else manifest_data
    results = []
    for item in manifest:
        if market and item.get("market") != market:
            continue
        if only and item.get("id") != only:
            continue
        audio_path = Path(item["audio"])
        if not audio_path.is_absolute():
            candidate = manifest_path.parent / audio_path
            if candidate.exists():
                audio_path = candidate
            elif (manifest_path.parent.parent / audio_path).exists():
                audio_path = manifest_path.parent.parent / audio_path
            else:
                audio_path = candidate
        if not audio_path.exists():
            raise FileNotFoundError(f"Missing recording for {item['id']}: {audio_path}")
        hypothesis = transcribe_audio(audio_path.read_bytes(), item.get("language"))
        result = {
            **item,
            "hypothesis": hypothesis,
            "wer": round(word_error_rate(item["reference"], hypothesis), 4),
            "error": word_error_rate(item["reference"], hypothesis) > 0,
        }
        results.append(result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate real localized recordings with Groq Whisper.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, default=Path("docs/asr_results.json"))
    parser.add_argument("--market", choices=["ph", "id"])
    parser.add_argument("--only")
    args = parser.parse_args()
    results = run(args.manifest, args.output, market=args.market, only=args.only)
    errors = sum(item["error"] for item in results)
    mean_wer = sum(item["wer"] for item in results) / max(1, len(results))
    print(f"utterances={len(results)} errors={errors} mean_wer={mean_wer:.4f} output={args.output}")


if __name__ == "__main__":
    main()
