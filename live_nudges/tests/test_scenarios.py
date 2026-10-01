import unittest

from live_nudges.run_nudge_scenarios import SCENARIOS, run_scenario


class NudgeScenarioTests(unittest.TestCase):
    def test_all_phase_five_scenarios_pass(self):
        results = [run_scenario(scenario) for scenario in SCENARIOS]
        self.assertEqual(len(results), 4)
        self.assertTrue(all(result["pass"] for result in results))

    def test_noisy_ambiguous_call_emits_no_nudge(self):
        result = run_scenario(next(item for item in SCENARIOS if item["id"] == "noisy-ambiguous"))
        self.assertEqual(result["delivered_nudges"], [])
        self.assertEqual(result["labels"], [])


if __name__ == "__main__":
    unittest.main()
