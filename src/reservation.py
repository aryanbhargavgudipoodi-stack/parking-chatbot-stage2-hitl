"""
Stage 1 reservation slot-filling agent.
Collects name, surname, car number, and reservation period over multiple
conversational turns, asking for whatever is still missing.
"""
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config import settings


class ReservationDetails(BaseModel):
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    car_number: Optional[str] = Field(None, description="Car license plate number")
    period_start: Optional[str] = Field(None, description="Reservation start date/time")
    period_end: Optional[str] = Field(None, description="Reservation end date/time")
    parking_lot: Optional[str] = Field(None, description="Requested parking lot name, if mentioned")

    def missing_fields(self):
        required = ["first_name", "last_name", "car_number", "period_start", "period_end"]
        return [f for f in required if getattr(self, f) in (None, "")]

    def is_complete(self):
        return len(self.missing_fields()) == 0


FIELD_QUESTIONS = {
    "first_name": "Could you tell me your first name?",
    "last_name": "And your last name, please?",
    "car_number": "What's your car's license plate number?",
    "period_start": "When would you like the reservation to start (date & time)?",
    "period_end": "When would you like the reservation to end (date & time)?",
}

_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You extract parking reservation details from a conversation. "
            "Only fill fields that are explicitly stated or clearly implied. "
            "Never invent values. If a field isn't mentioned in the new message, "
            "leave it empty/null rather than guessing.",
        ),
        (
            "human",
            "Known details so far (JSON): {known}\n\n"
            "New user message: {message}\n\n"
            "Extract the reservation details present in the new message.",
        ),
    ]
)


class ReservationAgent:
    """Conversational slot-filling agent for reservation details."""

    def __init__(self, llm=None):
        self.llm = llm or ChatOpenAI(model=settings.LLM_MODEL, temperature=0, api_key=settings.OPENAI_API_KEY)
        self.structured_llm = self.llm.with_structured_output(ReservationDetails)
        self.state = ReservationDetails()

    def update_from_message(self, message: str) -> ReservationDetails:
        messages = _EXTRACTION_PROMPT.format_messages(
            known=self.state.model_dump_json(), message=message
        )
        extracted = self.structured_llm.invoke(messages)

        merged = self.state.model_dump()
        for field, value in extracted.model_dump().items():
            if value not in (None, ""):
                merged[field] = value
        self.state = ReservationDetails(**merged)
        return self.state

    def next_question(self) -> Optional[str]:
        missing = self.state.missing_fields()
        return FIELD_QUESTIONS[missing[0]] if missing else None

    def summary(self) -> str:
        d = self.state
        return (
            f"Name: {d.first_name} {d.last_name}\n"
            f"Car number: {d.car_number}\n"
            f"Period: {d.period_start} -> {d.period_end}\n"
            f"Parking lot: {d.parking_lot or 'not specified'}"
        )

    def reset(self):
        self.state = ReservationDetails()