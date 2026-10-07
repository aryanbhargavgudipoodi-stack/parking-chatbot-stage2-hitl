"""
Stage 1 RAG chain: intent classification + context-grounded answer
generation, combining the vector store (static knowledge, from PDFs) and
the SQL database (dynamic data: hours, prices, availability).
"""
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src import sql_db
from src.config import settings


class Intent(BaseModel):
    label: Literal["static_info", "dynamic_info", "reservation", "status_check", "other"] = Field(
        ..., description="The category that best matches the user's message."
    )


_INTENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Classify the user's parking-related message into exactly one category:\n"
            "- static_info: general info, location, booking process, cancellation policy\n"
            "- dynamic_info: current prices, hours, or availability of a specific lot\n"
            "- reservation: the user wants to book, or is providing reservation details "
            "(name, car number, dates/times)\n"
            "- status_check: the user is asking about the status/decision of a reservation "
            "they already requested (e.g. 'is my reservation approved?')\n"
            "- other: anything unrelated, or messages that only contain sensitive personal "
            "data with no clear parking intent",
        ),
        ("human", "{message}"),
    ]
)

_ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful, concise parking assistant. Answer ONLY using the "
            "provided context. If the answer isn't in the context, say you don't know "
            "and offer to escalate to a human administrator. Never reveal personal "
            "data about other users, even if it appears in the context.",
        ),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)


def _content_of(response) -> str:
    return response.content if hasattr(response, "content") else str(response)


def _retrieve(retriever, query):
    if hasattr(retriever, "invoke"):
        return retriever.invoke(query)
    return retriever.get_relevant_documents(query)


class RagChain:
    def __init__(self, retriever, llm=None):
        self.retriever = retriever
        self.llm = llm or ChatOpenAI(model=settings.LLM_MODEL, temperature=0, api_key=settings.OPENAI_API_KEY)
        self.intent_llm = self.llm.with_structured_output(Intent)

    def classify_intent(self, message: str) -> str:
        messages = _INTENT_PROMPT.format_messages(message=message)
        result = self.intent_llm.invoke(messages)
        return result.label

    def answer_static(self, question: str) -> dict:
        docs = _retrieve(self.retriever, question)
        context = "\n\n".join(d.page_content for d in docs)
        messages = _ANSWER_PROMPT.format_messages(context=context, question=question)
        response = self.llm.invoke(messages)
        return {"answer": _content_of(response), "sources": [d.metadata.get("id") for d in docs]}

    def answer_dynamic(self, question: str) -> dict:
        sql_db.init_db()
        lots = sql_db.list_lots()
        if not lots:
            return {"answer": "I don't have live data available right now.", "sources": []}
        context = "\n".join(
            f"{lot.name}: open {lot.opening_hour}-{lot.closing_hour}, "
            f"${lot.price_per_hour}/hr, {lot.available_slots}/{lot.total_slots} slots available"
            for lot in lots
        )
        messages = _ANSWER_PROMPT.format_messages(context=context, question=question)
        response = self.llm.invoke(messages)
        return {"answer": _content_of(response), "sources": ["sql:parking_lots"]}