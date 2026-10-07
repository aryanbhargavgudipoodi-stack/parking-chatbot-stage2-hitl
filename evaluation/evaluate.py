"""
Stage 1 evaluation: runs against the auto-generated, PDF-grounded QA
dataset (see generate_qa_from_pdfs.py).

Measures:
  - Retrieval: Recall@K, Precision@K, latency.
  - Answer correctness: the chatbot's RAG pipeline answers each generated
    question; its answer is graded against the reference answer by an LLM
    judge (default) or embedding cosine-similarity (--grader embedding).
"""
import argparse
import json
import statistics
import time
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config import settings
from src.rag_chain import RagChain
from src.vector_store import get_embeddings, get_retriever, load_vector_store

DATASET_PATH = Path(__file__).parent / "generated_eval_dataset.json"
REPORT_JSON = Path(__file__).parent / "eval_results.json"
REPORT_MD = Path(__file__).parent / "REPORT.md"


class Verdict(BaseModel):
    correct: bool = Field(..., description="True if the candidate answer is factually consistent with the reference answer.")
    explanation: str = Field(..., description="One sentence justifying the verdict.")


_JUDGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are grading a chatbot's answer against a reference answer for "
            "a parking-reservation FAQ. Mark correct=True only if the candidate "
            "answer conveys the same facts as the reference (ignore wording/style "
            "differences). Mark correct=False if it adds wrong facts, contradicts "
            "the reference, or omits the key fact asked for.",
        ),
        ("human", "Question: {question}\nReference answer: {reference}\nCandidate answer: {candidate}"),
    ]
)


def load_dataset():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"{DATASET_PATH} not found. Run `python -m evaluation.generate_qa_from_pdfs` first."
        )
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def recall_at_k(retrieved_ids, relevant_ids):
    if not relevant_ids:
        return None
    return len(set(retrieved_ids) & set(relevant_ids)) / len(relevant_ids)


def precision_at_k(retrieved_ids, relevant_ids, k):
    if k == 0:
        return None
    return len(set(retrieved_ids) & set(relevant_ids)) / k


def _cosine(a, b):
    import numpy as np

    a, b = np.array(a), np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


def grade_answer_llm(judge_llm, question, reference, candidate) -> Verdict:
    structured = judge_llm.with_structured_output(Verdict)
    messages = _JUDGE_PROMPT.format_messages(question=question, reference=reference, candidate=candidate)
    return structured.invoke(messages)


def grade_answer_embedding(embeddings, reference, candidate, threshold=0.82) -> Verdict:
    score = _cosine(embeddings.embed_query(reference), embeddings.embed_query(candidate))
    return Verdict(correct=score >= threshold, explanation=f"cosine similarity={score:.3f}")


def run_evaluation(k: int = 4, grader: str = "llm", limit: int = None):
    vectorstore = load_vector_store()
    retriever = get_retriever(vectorstore, k=k)
    rag = RagChain(retriever)

    dataset = load_dataset()
    if limit:
        dataset = dataset[:limit]

    judge_llm = ChatOpenAI(model=settings.LLM_MODEL, temperature=0, api_key=settings.OPENAI_API_KEY) if grader == "llm" else None
    embeddings = get_embeddings() if grader == "embedding" else None

    latencies, recalls, precisions, correctness, details = [], [], [], [], []

    for item in dataset:
        query, relevant_ids, reference = item["query"], item["relevant_doc_ids"], item["reference_answer"]

        start = time.perf_counter()
        docs = retriever.invoke(query)
        retrieval_latency = time.perf_counter() - start

        retrieved_ids = [d.metadata.get("id") for d in docs]
        r = recall_at_k(retrieved_ids, relevant_ids)
        p = precision_at_k(retrieved_ids, relevant_ids, k)

        gen_start = time.perf_counter()
        candidate_answer = rag.answer_static(query)["answer"]
        full_latency = time.perf_counter() - gen_start

        verdict = (
            grade_answer_llm(judge_llm, query, reference, candidate_answer)
            if grader == "llm"
            else grade_answer_embedding(embeddings, reference, candidate_answer)
        )

        latencies.append(retrieval_latency)
        recalls.append(r)
        precisions.append(p)
        correctness.append(1 if verdict.correct else 0)

        details.append(
            {
                "query": query, "reference_answer": reference, "candidate_answer": candidate_answer,
                "relevant_ids": relevant_ids, "retrieved_ids": retrieved_ids,
                "recall_at_k": r, "precision_at_k": p,
                "correct": verdict.correct, "judge_explanation": verdict.explanation,
                "retrieval_latency_sec": retrieval_latency, "end_to_end_latency_sec": full_latency,
            }
        )

    summary = {
        "k": k, "grader": grader, "num_questions": len(dataset),
        "avg_recall_at_k": statistics.mean(recalls),
        "avg_precision_at_k": statistics.mean(precisions),
        "answer_accuracy": statistics.mean(correctness),
        "retrieval_latency": {
            "mean_sec": statistics.mean(latencies),
            "p50_sec": statistics.median(latencies),
            "p95_sec": sorted(latencies)[int(0.95 * (len(latencies) - 1))],
        },
    }

    output = {"summary": summary, "details": details}
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    _write_markdown_report(output)
    return output


def _write_markdown_report(output):
    s = output["summary"]
    lines = [
        "# Stage 1 Evaluation Report (PDF knowledge base, semantic chunking)",
        "",
        f"- Questions evaluated: **{s['num_questions']}** (auto-generated from ingested PDFs)",
        f"- K (top-k retrieved chunks): **{s['k']}**",
        f"- Grader: **{s['grader']}**",
        "",
        "## Retrieval quality",
        f"- Average Recall@{s['k']}: **{s['avg_recall_at_k']:.3f}**",
        f"- Average Precision@{s['k']}: **{s['avg_precision_at_k']:.3f}**",
        "",
        "## Answer correctness",
        f"- Accuracy (judged correct / total): **{s['answer_accuracy']:.1%}**",
        "",
        "## Retrieval latency (seconds)",
        f"- Mean: {s['retrieval_latency']['mean_sec']:.4f}",
        f"- P50: {s['retrieval_latency']['p50_sec']:.4f}",
        f"- P95: {s['retrieval_latency']['p95_sec']:.4f}",
        "",
        "## Failed cases",
        "",
    ]
    failed = [d for d in output["details"] if not d["correct"]]
    if not failed:
        lines.append("None — all generated questions were answered correctly.")
    else:
        for d in failed:
            lines += [
                f"**Q:** {d['query']}",
                f"- Reference: {d['reference_answer']}",
                f"- Candidate: {d['candidate_answer']}",
                f"- Judge: {d['judge_explanation']}",
                "",
            ]
    lines += [
        "## Methodology",
        "Questions are generated directly from ingested PDF chunks, so every "
        "question has a known ground-truth source chunk id and reference answer "
        "grounded in the actual knowledge base. Retrieval metrics compare "
        "retrieved chunk ids against that ground truth; answer correctness is "
        "judged by comparing the chatbot's generated answer to the reference "
        "answer.",
    ]
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--grader", choices=["llm", "embedding"], default="llm")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    results = run_evaluation(k=args.k, grader=args.grader, limit=args.limit)
    print(json.dumps(results["summary"], indent=2))