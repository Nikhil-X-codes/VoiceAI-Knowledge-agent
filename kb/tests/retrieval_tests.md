| # | User question | Retrieved record | Source | Why relevant | Verdict |
| --- | --- | --- | --- | --- | --- |
| 1 | Product question | kb_product_001 | https://example.com/loan_terms | Product summary matches installment loan details | Correct |
| 2 | Policy (late fee) | kb_policy_001 | loan_fee_schedule.pdf | The late fee and deadline language matches the policy record | Correct |
| 3 | Qualification | kb_qualification_001 | https://example.com/faq | Reminder timing and due-date behavior are captured here | Correct |
| 4 | FAQ | kb_objection_001 | https://example.com/faq | FAQ and objection handling both cover the customer concern flow | Correct |
| 5 | Objection ("fees are too high") | kb_objection_001 | https://example.com/faq | Objection handling specifically addresses fee concerns | Correct |
| 6 | Not in KB (negative test) | none | n/a | Threshold returns not found for unrelated content | Correct |

### Notes
- Retrieval uses hybrid ranking: vector similarity + BM25 reciprocal rank fusion.
- The threshold rejects unrelated queries and preserves the safe "I don't have that information" behavior.
