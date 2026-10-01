import unittest

from live_nudges.nudges import generate_nudges
from live_nudges.signals import SignalWindow, extract_signals


class SignalTests(unittest.TestCase):
    def test_extracts_payment_and_callback_signals(self):
        turns = [
            {"speaker": "customer", "text": "I cannot pay this week, please call me back."},
        ]
        signals = extract_signals(turns, {"required_disclosure_spoken": True})
        names = {item["signal"] for item in signals}
        self.assertIn("payment_difficulty", names)
        self.assertIn("callback_need", names)
        self.assertTrue(all(set(item) == {"signal", "confidence", "evidence", "priority", "topic"} for item in signals))

    def test_signal_window_keeps_last_four_turns(self):
        window = SignalWindow()
        for index in range(6):
            window.add("customer", f"turn {index}")
        self.assertEqual(len(window.turns), 4)
        self.assertIn("turn 5", window.turns[-1]["text"])

    def test_generates_short_prioritized_nudges(self):
        signals = [
            {"signal": "callback_need", "confidence": 0.9, "priority": "medium", "topic": "callback"},
            {"signal": "compliance_gap", "confidence": 0.95, "priority": "high", "topic": "disclosure"},
            {"signal": "frustration", "confidence": 0.4, "priority": "high", "topic": "de-escalation"},
        ]
        nudges = generate_nudges(signals)
        self.assertEqual(nudges[0]["signal"], "compliance_gap")
        self.assertLessEqual(len(nudges), 2)
        self.assertTrue(all(len(item["text"].split()) < 15 for item in nudges))

    def test_detects_missed_cross_sell(self):
        signals = extract_signals([
            {"speaker": "customer", "text": "I also have a second vehicle."},
        ], {"required_disclosure_spoken": True})
        self.assertEqual(signals[0]["signal"], "missed_cross_sell")


if __name__ == "__main__":
    unittest.main()
