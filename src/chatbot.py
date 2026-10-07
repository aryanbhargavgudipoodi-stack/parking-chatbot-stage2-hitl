"""
Stage 1+2 orchestrator: wires together intent routing, static RAG
retrieval, dynamic SQL lookups, reservation slot-filling, the PII
guardrail, and (Stage 2) escalation to a human administrator.

Collaborators (rag, reservation_agent, pii_filter, admin_agent, retriever)
can all be injected, which keeps this class fully unit-testable without
any real LLM/vector-DB/network calls (see tests/test_chatbot.py).
"""
import logging
import time

from admin_agent.agent import AdminAgent
from admin_agent.models import RequestStatus
from src import sql_db
from src.guardrails.pii_filter import PIIFilter
from src.rag_chain import RagChain
from src.reservation import ReservationAgent
from src.vector_store import get_retriever, load_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parking_chatbot")

_BLOCKED_INPUT_ENTITIES = {"CREDIT_CARD", "US_SSN", "IBAN_CODE"}


class ParkingChatbot:
    def __init__(self, rag=None, reservation_agent=None, pii_filter=None, retriever=None,
                 admin_agent=None, skip_sql_seed=False):
        if not skip_sql_seed:
            sql_db.seed_db()

        if rag is None and retriever is None:
            vectorstore = load_vector_store()
            retriever = get_retriever(vectorstore)

        self.rag = rag or RagChain(retriever)
        self.pii_filter = pii_filter or PIIFilter()
        self.reservation_agent = reservation_agent or ReservationAgent()
        self.admin_agent = admin_agent or AdminAgent()
        self.mode = "qa"  # "qa" | "reservation"
        self.pending_request_id = None
        self.history = []

    def handle_message(self, message: str) -> str:
        start = time.time()

        if self.mode != "reservation":
            flagged = [e for e in self.pii_filter.scan(message) if e["entity_type"] in _BLOCKED_INPUT_ENTITIES]
            if flagged:
                response = (
                    "For your safety, please don't share financial or government ID "
                    "information in this chat. I only need your name, car number, "
                    "and reservation period to book a spot."
                )
                self._finish_turn(message, response, start)
                return response

        if self.mode == "reservation":
            response = self._continue_reservation(message)
        else:
            intent = self.rag.classify_intent(message)
            if intent == "static_info":
                response = self.rag.answer_static(message)["answer"]
            elif intent == "dynamic_info":
                response = self.rag.answer_dynamic(message)["answer"]
            elif intent == "reservation":
                self.mode = "reservation"
                response = self._continue_reservation(message)
            elif intent == "status_check":
                response = self._check_reservation_status()
            else:
                response = (
                    "I can help with parking info, prices, hours, availability, "
                    "location, booking a reservation, or checking a reservation's status."
                )

            if intent in ("static_info", "dynamic_info"):
                response, leaked = self.pii_filter.redact(response)
                if leaked:
                    logger.warning("Redacted %d PII entity(ies) from outbound response", len(leaked))

        self._finish_turn(message, response, start)
        return response

    def _continue_reservation(self, message: str) -> str:
        self.reservation_agent.update_from_message(message)
        next_question = self.reservation_agent.next_question()
        if next_question:
            return next_question

        details = self.reservation_agent.state
        request = self.admin_agent.escalate(
            first_name=details.first_name, last_name=details.last_name,
            car_number=details.car_number, period_start=details.period_start,
            period_end=details.period_end, parking_lot=details.parking_lot,
        )
        self.pending_request_id = request.id

        summary = self.reservation_agent.summary()
        self.mode = "qa"
        self.reservation_agent.reset()
        return (
            "Thanks! Here's what I have:\n"
            f"{summary}\n\n"
            f"Your request (id: {request.id}) has been sent to an administrator for approval. "
            "You can ask me about its status any time."
        )

    def _check_reservation_status(self) -> str:
        if not self.pending_request_id:
            return "I don't have an active reservation request for you. Would you like to make one?"

        request = self.admin_agent.get_decision(self.pending_request_id)
        if not request:
            return "I couldn't find that reservation request."

        if request.status == RequestStatus.PENDING:
            return "Your reservation request is still pending administrator approval."
        if request.status == RequestStatus.APPROVED:
            note = f" Note from admin: {request.decision_reason}" if request.decision_reason else ""
            return f"Good news! Your reservation request was approved.{note}"
        note = f" Reason: {request.decision_reason}" if request.decision_reason else ""
        return f"Unfortunately your reservation request was refused.{note}"

    def _finish_turn(self, user_msg: str, bot_msg: str, start_time: float):
        latency = time.time() - start_time
        safe_user, _ = self.pii_filter.redact(user_msg)
        logger.info("USER: %s", safe_user)
        logger.info("BOT: %s", bot_msg)
        logger.info("Latency: %.3fs", latency)
        self.history.append({"user": user_msg, "bot": bot_msg, "latency_sec": latency})