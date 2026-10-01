import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from localized_bots.asr_benchmark import run, word_error_rate


class AsrBenchmarkTests(unittest.TestCase):
    def test_word_error_rate(self):
        self.assertEqual(word_error_rate("pay my premium", "pay my premium"), 0.0)
        self.assertGreater(word_error_rate("pay my premium", "pay premium"), 0.0)

    def test_supplied_items_manifest_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "sample.wav"
            audio.write_bytes(b"audio")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"items": [{
                "id": "ph_01",
                "audio": "sample.wav",
                "language": "tl",
                "reference": "hello",
            }]}), encoding="utf-8")
            with patch("localized_bots.asr_benchmark.transcribe_audio", return_value="hello"):
                results = run(manifest, root / "results.json")
            self.assertEqual(results[0]["id"], "ph_01")
            self.assertEqual(results[0]["wer"], 0.0)


if __name__ == "__main__":
    unittest.main()
