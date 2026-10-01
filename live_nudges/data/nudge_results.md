# Phase 5.8-5.9 Nudge Evaluation

| Scenario | Expected | Delivered | Verdict |
| --- | --- | --- | --- |
| missed-cross-sell | one nudge | missed_cross_sell | PASS |
| skipped-disclosure | compliance reminder | compliance_gap | PASS |
| rising-frustration | de-escalation nudge | frustration | PASS |
| noisy-ambiguous | none or very few nudges | none | PASS |

## False-positive analysis

- Precision: 100% for delivered scenario nudges
- Delivered true positives: 5
- Delivered false positives: 0
- Suppressed by control: confidence_threshold=1, duplicate_evidence=1, cooldown=1, max_active_two=1, noisy_sentiment_two_turn_rule=1.
- False-alarm example: noisy, low-confidence frustration was suppressed because it lacked two supporting turns.
