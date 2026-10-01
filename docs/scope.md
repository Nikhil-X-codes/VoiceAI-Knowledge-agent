# Phase 1 Scope Definition

## Use case

Loan pre-due reminder system for customers who have an installment due soon.

## Customer profile

- Product: installment loan / consumer finance
- Customer segment: active borrower with upcoming due date
- Objective: remind the customer, confirm due date and amount, capture intent,
  and escalate when the customer disputes, becomes angry, or asks for a human.

## Business rules

- Reminder should happen 3 days before due date.
- Use the KB as the source of truth for policy, fees, schedule, and next steps.
- If the customer asks for a human, escalate immediately.
- If the customer disputes charges or becomes angry twice, escalate.
- Offer pay now, promise date, extension request, or callback.
- Never answer policy questions without KB evidence.

## Example call flow

1. Greeting and identity check
2. Confirm due date and amount
3. Offer payment methods or a promise date
4. Handle objections or fee questions from KB evidence
5. Summarize and close, or escalate

## Required artifacts

- source list for finance policy content
- extraction logs and failed-source logs
- cleaned and deduplicated KB records
- versioned metadata and citations
- pass/fail retrieval tests

## Phase 1 completion checklist

- [x] Repo created and scaffolded
- [x] `.env.example` added
- [x] project directories prepared
- [ ] dependencies installed in the selected environment
- [ ] Groq API key configured locally
- [x] scope document written
- [ ] source content plan finalized
