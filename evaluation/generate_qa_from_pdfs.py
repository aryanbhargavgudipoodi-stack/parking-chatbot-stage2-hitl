"""
Generates a grounded evaluation dataset directly from the ingested PDF
chunks: for each chunk, an LLM writes a natural question that chunk
answers, plus a reference answer. Real questions, real chunk ids, real
reference answers — all tied to the actual knowledge base content.

Usage:
    python -m evaluation.generate_qa_from_pdfs --per-chunk 1 --max-chunks 30
"""
import argparse
import json
from pathlib import Path
from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config import settings
from src.metadata_store import init_db, list_chunks

OUTPUT_PATH = Path(__file__).parent / "generated_eval_dataset.json"


class GeneratedQA(BaseModel):
    question: str = Field(..., description="A natural question a real user might ask the parking chatbot.")
    answer: str = Field(..., description="The correct, concise answer, using ONLY information in the given text.")


class GeneratedQAList(BaseModel):
    items: List[GeneratedQA]


_QA_GEN_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You write evaluation questions for a parking-reservation chatbot. "
            "Given a passage from the knowledge base, write {n} question(s) that "
            "(a) a real customer could plausibly ask, (b) are answerable using "
            "ONLY the given passage, and (c) are specific enough that a vague or "
            "wrong answer would be obviously incorrect. Provide the correct answer "
            "too, grounded strictly in the passage. Do not mention 'the passage' "
            "or 'the document' in the question itself.",
        ),
        ("human", "Passage:\n{passage}"),
    ]
)


def generate_dataset(per_chunk: int = 1, max_chunks: int = None, llm=None) -> list:
    init_db()
    chunks = list_chunks()
    if max_chunks:
        chunks = chunks[:max_chunks]

    llm = llm or ChatOpenAI(model=settings.LLM_MODEL, temperature=0.3, api_key=settings.OPENAI_API_KEY)
    structured_llm = llm.with_structured_output(GeneratedQAList)

    dataset = []
    for chunk in chunks:
        if len(chunk.content.strip()) < 40:
            continue

        messages = _QA_GEN_PROMPT.format_messages(n=per_chunk, passage=chunk.content)
        try:
            result = structured_llm.invoke(messages)
        except Exception as exc:  # noqa: BLE001
            print(f"[generate_qa] skipped chunk {chunk.id} due to error: {exc}")
            continue

        for qa in result.items:
            dataset.append(
                {
                    "query": qa.question,
                    "reference_answer": qa.answer,
                    "relevant_doc_ids": [chunk.id],
                    "source_file": chunk.source_file,
                    "page": chunk.page,
                }
            )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
    print(f"[generate_qa] wrote {len(dataset)} QA pairs to {OUTPUT_PATH}")
    return dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-chunk", type=int, default=1)
    parser.add_argument("--max-chunks", type=int, default=None)
    args = parser.parse_args()
    generate_dataset(per_chunk=args.per_chunk, max_chunks=args.max_chunks)