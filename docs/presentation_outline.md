# Presentation Outline (fallback if you can't run python-pptx)

1. Title — Parking Reservation Chatbot, Stage 1
2. Problem & Scope
3. Architecture Overview (PDF -> semantic chunks -> metadata DB -> vector DB; SQL for dynamic data)
4. RAG & Conversation Flow (intent routing)
5. Guardrails (PII protection, inbound/outbound)
6. Evaluation Methodology (auto-generated QA, Recall@K/Precision@K, LLM-judge accuracy, latency)
7. Demo screenshot — static info Q&A
8. Demo screenshot — reservation flow
9. Demo screenshot — guardrail blocking sensitive input
10. Demo screenshot — evaluation report
11. Testing & CI/CD (pytest, GitHub Actions, Terraform)
12. Next steps — Stages 2-4