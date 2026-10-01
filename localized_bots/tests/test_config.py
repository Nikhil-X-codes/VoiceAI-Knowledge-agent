import unittest

from localized_bots.config import get_market_config


class MarketConfigTests(unittest.TestCase):
    def test_indonesian_javanese_hint_can_be_selected(self):
        config = get_market_config("id")
        self.assertEqual(config.asr_language, "id")
        self.assertEqual(get_market_config("id", "colloquial").tts_voice, "id-ID-ArdiNeural")

    def test_taglish_uses_auto_detect(self):
        config = get_market_config("ph", "taglish")
        self.assertIsNone(config.asr_language)
        self.assertEqual(config.default_register, "taglish")


if __name__ == "__main__":
    unittest.main()
