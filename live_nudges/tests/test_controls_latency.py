import tempfile
import unittest
from pathlib import Path

from live_nudges.controls import NudgeController
from live_nudges.latency import latency_report, write_latency_row


class ControlLatencyTests(unittest.TestCase):
    def test_controller_applies_cooldown_expiry_and_duplicate_suppression(self):
        controller = NudgeController(cooldown_seconds=30, expiry_seconds=20)
        signal = {"signal": "callback_need", "confidence": 0.9, "priority": "medium", "topic": "callback", "evidence": "customer wants a callback"}
        self.assertEqual(len(controller.accept([signal], now=0)), 1)
        self.assertEqual(len(controller.accept([signal], now=10)), 0)
        self.assertEqual(len(controller.accept([signal], now=31)), 0)
        changed = {**signal, "evidence": "customer explicitly requested a callback tomorrow"}
        self.assertEqual(len(controller.accept([changed], now=61)), 1)

    def test_controller_requires_two_noisy_frustration_turns(self):
        controller = NudgeController()
        signal = {"signal": "frustration", "confidence": 0.9, "priority": "high", "topic": "de-escalation", "evidence": "frustrated"}
        one = [{"speaker": "customer", "text": "I am frustrated", "asr_confidence": 0.4}]
        two = one + [{"speaker": "customer", "text": "This is ridiculous", "asr_confidence": 0.4}]
        self.assertEqual(controller.accept([signal], 0, one, {"noisy": True}), [])
        self.assertEqual(len(controller.accept([signal], 1, two, {"noisy": True})), 1)

    def test_compliance_nudge_stops_after_disclosure(self):
        controller = NudgeController()
        signal = {"signal": "compliance_gap", "confidence": 0.9, "priority": "high", "topic": "disclosure", "evidence": "missing disclosure"}
        self.assertEqual(len(controller.accept([signal], 0, [], {"required_disclosure_spoken": False})), 1)
        self.assertEqual(controller.accept([signal], 31, [], {"required_disclosure_spoken": True}), [])

    def test_latency_report_calculates_percentiles(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latency.csv"
            for index in range(1, 4):
                write_latency_row(path, "call", index, 0, index, index + 1, index + 2, index + 3)
            report = latency_report(path)
            self.assertEqual(report["asr_ms"]["p50_ms"], 2000.0)
            self.assertIn("end_to_end_ms", report)


if __name__ == "__main__":
    unittest.main()
