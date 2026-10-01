import unittest

from localized_bots.agent import build_localized_response
from localized_bots.config import get_market_config
from voice_agent.agent import process_turn


class LocalizedBotTests(unittest.TestCase):
    def test_philippines_config_uses_tagalog_and_filipino_voice(self):
        config = get_market_config("ph", "taglish")
        self.assertIsNone(config.asr_language)
        self.assertEqual(config.tts_voice, "fil-PH-BlessicaNeural")

    def test_philippines_policy_reply_is_respectful(self):
        result = build_localized_response("Can I pay premium with GCash?", "ph")
        self.assertIn("po", result["reply_text"].lower())
        self.assertIn("GCash", result["reply_text"])
        self.assertEqual(result["asr_language"], "tl")

    def test_indonesia_formal_and_colloquial_registers(self):
        formal = build_localized_response("Bagaimana pembayaran cicilan?", "id")
        colloquial = build_localized_response("Bagaimana pembayaran cicilan?", "id", {"register": "colloquial"})
        self.assertIn("Bapak/Ibu", formal["reply_text"])
        self.assertIn("Kak", colloquial["reply_text"])
        self.assertEqual(colloquial["tts_voice"], "id-ID-ArdiNeural")

    def test_localized_unknown_uses_local_fallback(self):
        result = build_localized_response("Apa kabar sepak bola?", "id")
        self.assertIn("belum tersedia", result["reply_text"])
        self.assertIn("panggilan balik", result["reply_text"])
        self.assertFalse(result["kb"]["found"])

    def test_native_fallback_and_handoff_lines(self):
        ph_fallback = build_localized_response("What is the weather?", "ph")
        ph_handoff = build_localized_response("I want a human agent", "ph")
        id_handoff = build_localized_response("Saya ingin bicara dengan petugas manusia", "id")
        self.assertIn("tawag pabalik", ph_fallback["reply_text"])
        self.assertIn("kinatawan", ph_handoff["reply_text"])
        self.assertIn("petugas", id_handoff["reply_text"])

    def test_shared_turn_endpoint_selects_market(self):
        result = process_turn({
            "call_id": "unit-test-ph-market",
            "market": "ph",
            "register": "taglish",
            "transcript": "Can I pay my premium with GCash?",
        })
        self.assertEqual(result["market"], "ph")
        self.assertEqual(result["asr_language"], None)
        self.assertEqual(result["tts_voice"], "fil-PH-BlessicaNeural")

    def test_indonesia_can_override_asr_for_javanese(self):
        result = process_turn({
            "call_id": "unit-test-id-jw",
            "market": "id",
            "language": "jw",
            "transcript": "Bagaimana pembayaran cicilan?",
        })
        self.assertEqual(result["asr_language"], "jw")


if __name__ == "__main__":
    unittest.main()
