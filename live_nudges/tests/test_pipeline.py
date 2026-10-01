import asyncio
import unittest

from live_nudges.pipeline import LiveNudgeProducer


class FakeHub:
    def __init__(self):
        self.payloads = []

    async def broadcast(self, payload):
        self.payloads.append(payload)


class PipelineTests(unittest.TestCase):
    def test_producer_broadcasts_transcript_signals_and_nudges(self):
        async def scenario():
            fake_hub = FakeHub()
            producer = LiveNudgeProducer({"required_disclosure_spoken": True})
            payload = await producer.ingest(
                "customer",
                "I also have a second vehicle.",
                now=0,
                dashboard_hub=fake_hub,
            )
            return payload, fake_hub

        payload, fake_hub = asyncio.run(scenario())
        self.assertEqual(len(fake_hub.payloads), 1)
        self.assertEqual(payload["speaker"], "customer")
        self.assertEqual(payload["nudges"][0]["signal"], "missed_cross_sell")


if __name__ == "__main__":
    unittest.main()
