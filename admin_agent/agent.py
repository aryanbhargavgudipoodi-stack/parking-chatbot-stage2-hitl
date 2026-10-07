"""
AdminAgent: the LangChain-based agent for the administrator side of the
human-in-the-loop workflow.

Two responsibilities:
  1. Escalation: compose a human-readable notification from a completed
     reservation and send it to the administrator via a configurable
     channel (console/email/slack/rest).
  2. Decision handling: expose LangChain tools (list pending requests,
     approve, refuse, check status) that a conversational agent lets the
     administrator drive in natural language -- e.g. "approve request
     abc123" -- in addition to the REST API (admin_agent/api.py).

Communication between the two agents (user-facing chatbot <-> admin
agent) happens through the shared SQLite-backed RequestStore: the
chatbot writes a PENDING request, the admin agent's tools write the
decision, and the chatbot polls that same store to relay the decision
back to the user.
"""
from typing import Optional

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from admin_agent import store
from admin_agent.models import ReservationRequest, RequestStatus
from admin_agent.notifier import AdminNotifier, get_notifier
from src.config import settings

_MESSAGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You write short, clear notification messages for a parking lot "
            "administrator, summarizing a new reservation request that needs "
            "approval. Mention the requester's name, car number, requested "
            "period, and parking lot (if given). End with the request id so "
            "the admin can reference it when approving or refusing.",
        ),
        ("human", "Reservation request:\n{details}"),
    ]
)


class AdminAgent:
    def __init__(self, notifier: AdminNotifier = None, llm=None, db_path: str = None):
        self.notifier = notifier or get_notifier()
        self.llm = llm or ChatOpenAI(model=settings.LLM_MODEL, temperature=0, api_key=settings.OPENAI_API_KEY)
        self.db_path = db_path
        store.init_db(db_path)

    # ---- escalation (called by the user-facing chatbot) ----

    def escalate(self, first_name, last_name, car_number, period_start, period_end,
                 parking_lot=None) -> ReservationRequest:
        request = store.create_request(
            first_name=first_name, last_name=last_name, car_number=car_number,
            period_start=period_start, period_end=period_end, parking_lot=parking_lot,
            db_path=self.db_path,
        )
        message = self._compose_message(request)
        try:
            self.notifier.notify(request, message)
        except Exception as exc:  # noqa: BLE001
            # Notification failure must never lose the request -- it's
            # already durably stored and still visible via the REST API/CLI.
            import logging
            logging.getLogger("admin_agent").warning("Failed to notify admin: %s", exc)
        return request

    def _compose_message(self, request: ReservationRequest) -> str:
        details = (
            f"id={request.id}, name={request.first_name} {request.last_name}, "
            f"car_number={request.car_number}, period={request.period_start} -> {request.period_end}, "
            f"parking_lot={request.parking_lot or 'not specified'}"
        )
        messages = _MESSAGE_PROMPT.format_messages(details=details)
        response = self.llm.invoke(messages)
        return response.content if hasattr(response, "content") else str(response)

    # ---- read access (used by the chatbot and the REST API) ----

    def get_decision(self, request_id: str) -> Optional[ReservationRequest]:
        return store.get_request(request_id, db_path=self.db_path)

    def list_requests(self, status: RequestStatus = None):
        return store.list_requests(status, db_path=self.db_path)

    def apply_decision(self, request_id: str, approved: bool, reason: str = None):
        return store.set_decision(request_id, approved=approved, reason=reason, db_path=self.db_path)

    # ---- tools exposed to the admin-facing conversational agent ----

    def _build_tools(self):
        db_path = self.db_path

        @tool
        def list_pending_requests() -> str:
            """Lists all reservation requests currently awaiting admin approval."""
            pending = store.list_requests(RequestStatus.PENDING, db_path=db_path)
            if not pending:
                return "There are no pending reservation requests."
            return "\n".join(
                f"- {r.id}: {r.first_name} {r.last_name}, car {r.car_number}, "
                f"{r.period_start} -> {r.period_end}, lot={r.parking_lot or 'n/a'}"
                for r in pending
            )

        @tool
        def approve_request(request_id: str, reason: str = "") -> str:
            """Approves a pending reservation request by its id."""
            updated = store.set_decision(request_id, approved=True, reason=reason, db_path=db_path)
            if not updated:
                return f"No request found with id {request_id}."
            return f"Request {request_id} approved."

        @tool
        def refuse_request(request_id: str, reason: str = "") -> str:
            """Refuses a pending reservation request by its id, optionally with a reason."""
            updated = store.set_decision(request_id, approved=False, reason=reason, db_path=db_path)
            if not updated:
                return f"No request found with id {request_id}."
            return f"Request {request_id} refused."

        @tool
        def get_request_status(request_id: str) -> str:
            """Looks up the current status of a reservation request by its id."""
            req = store.get_request(request_id, db_path=db_path)
            if not req:
                return f"No request found with id {request_id}."
            return f"Request {request_id} is {req.status.value}."

        return [list_pending_requests, approve_request, refuse_request, get_request_status]

    def build_admin_chat_agent(self) -> AgentExecutor:
        """Returns a LangChain tool-calling agent the administrator can
        converse with in natural language (see admin_agent/cli.py)."""
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You help a parking lot administrator manage reservation "
                    "approvals. Use the available tools to list pending "
                    "requests, approve, refuse, or check status. Always use "
                    "the exact request id the administrator gives you.",
                ),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )
        tools = self._build_tools()
        agent = create_tool_calling_agent(self.llm, tools, prompt)
        return AgentExecutor(agent=agent, tools=tools, verbose=False)