import tempfile
import unittest
from pathlib import Path

from live_nudges.streaming import chunk_audio, run_stream


class StreamingTests(unittest.TestCase):
    def test_chunk_audio_has_overlap(self):
        audio = bytes(range(256)) * 500
        chunks = chunk_audio(audio, sample_rate=100, channels=1, sample_width=1, chunk_seconds=3, overlap_seconds=0.5)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].payload[-50:], chunks[1].payload[:50])
        self.assertEqual(chunks[0].start_seconds, 0)

    def test_stream_keeps_customer_and_agent_labels_and_writes_latency(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "latency.csv"
            rows = run_stream(
                {"customer": b"a" * 400, "agent": b"b" * 400},
                output,
                language_by_channel={"customer": "id", "agent": "id"},
                chunk_seconds=1,
                overlap_seconds=0.25,
                interval_seconds=0,
                transcriber=lambda audio, language: f"{language}:{audio[:1].decode()}",
                sleep_fn=lambda seconds: None,
            )
            self.assertEqual({row["speaker"] for row in rows}, {"customer", "agent"})
            self.assertTrue(all(row["asr_ms"] >= 0 for row in rows))
            self.assertTrue(output.exists())
            self.assertIn("speaker", output.read_text(encoding="utf-8").splitlines()[0])


if __name__ == "__main__":
    unittest.main()
