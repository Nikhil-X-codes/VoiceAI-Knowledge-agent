import unittest

from voice_agent.agent import SYSTEM_PROMPT, build_response, process_turn, summarize_call


class VoiceAgentPhase3Tests(unittest.TestCase):
    def test_build_response_handles_due_date_question(self):
        state = {"phase": "confirm_due_date", "customer_name": "Alicia"}
        output = build_response("When is my payment due?", state)
        self.assertIn("Alicia", output["reply_text"])
        self.assertIn("due date", output["reply_text"].lower())

    def test_build_response_handles_human_request(self):
        state = {"phase": "intent", "customer_name": "Alicia"}
        output = build_response("I want a human agent", state)
        self.assertTrue(output["needs_human"])
        self.assertIn("escalat", output["reply_text"].lower())

    def test_summarize_call_includes_key_details(self):
        summary = summarize_call({
            "customer_name": "Alicia",
            "due_date": "2026-10-05",
            "amount": "$240.00",
            "intent": "pay now",
            "needs_human": False,
        })
        self.assertIn("Alicia", summary)
        self.assertIn("$240.00", summary)

    def test_fee_answer_has_kb_citation_and_short_voice_reply(self):
        output = build_response("Why is there a late fee after the due date?", {"customer_name": "Ravi"})
        self.assertTrue(output["citation"])
        self.assertLessEqual(len(output["reply_text"].split(".")), 3)

    def test_out_of_scope_question_uses_safe_fallback(self):
        output = build_response("Recommend a solar panel refinancing company", {"customer_name": "Omar"})
        self.assertIn("do not have that information", output["reply_text"].lower())
        self.assertIn("callback", output["reply_text"].lower())

    def test_turn_persists_audio_and_lead_action(self):
        output = process_turn({
            "call_id": "unit-test-phase3",
            "transcript": "I will pay now",
            "audio_b64": "dGVzdC1hdWRpbw==",
            "state": {"customer_name": "Alicia"},
        })
        self.assertTrue(output["audio_b64_present"])
        self.assertTrue(any(item["tool"] == "save_lead_or_callback" for item in output["tool_calls"]))
        self.assertIn("search_kb", output["system_prompt"] or SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
