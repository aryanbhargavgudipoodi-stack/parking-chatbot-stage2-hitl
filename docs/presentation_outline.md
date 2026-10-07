# Presentation Outline (fallback if you can't run python-pptx)

1. Title — Parking Reservation Chatbot, Stage 2
2. Problem & Scope — parking answers plus administrator-approved reservations
3. Architecture Overview — PDF -> semantic chunks -> metadata DB -> vector DB; SQL for dynamic data; shared SQLite approval store
4. RAG & Conversation Flow — intent routing, reservation slot filling, escalation, and status checks
5. Stage 2 — Administrator Agent — LangChain tools for pending requests, approval, refusal, and status
6. Escalation & Communication — request id, generated notification, configurable channel, shared request state
7. Administrator Decision Interfaces — natural-language CLI and FastAPI endpoints
8. Guardrails — PII protection on inbound and outbound chat
9. Evaluation Methodology — generated QA, Recall@K/Precision@K, answer quality, and latency
10. Demo screenshot — static information question and grounded answer
11. Demo screenshot — reservation details collected by chatbot
12. Demo screenshot — notification and matching pending admin request
13. Demo screenshot — admin decision relayed back to user
14. Demo screenshot — sensitive input blocked by guardrail
15. Evaluation report — retrieval, answer accuracy, and latency metrics
16. Testing & CI/CD — offline tests, GitHub Actions, and Terraform
17. Current Stage & Next Steps — Stage 2 delivered; Stages 3-4 planned