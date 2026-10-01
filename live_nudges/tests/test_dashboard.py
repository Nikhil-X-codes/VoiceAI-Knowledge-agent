import unittest

from fastapi.testclient import TestClient

from live_nudges.dashboard import app


class DashboardTests(unittest.TestCase):
    def test_health_endpoint(self):
        response = TestClient(app).get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_dashboard_page_is_served(self):
        response = TestClient(app).get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Live call nudges", response.text)

    def test_publish_runs_producer(self):
        response = TestClient(app).post("/publish", json={
            "speaker": "customer",
            "transcript": "I also have a second vehicle.",
            "call_state": {"required_disclosure_spoken": True},
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["nudges"][0]["signal"], "missed_cross_sell")

    def test_websocket_accepts_nudge_client(self):
        with TestClient(app).websocket_connect("/ws/nudges") as websocket:
            websocket.send_text("ready")


if __name__ == "__main__":
    unittest.main()
