"""
Semantic chunking: splits document text where meaning shifts (detected via
embedding distance between consecutive sentences), instead of cutting at a
fixed character count. Falls back to RecursiveCharacterTextSplitter if
langchain_experimental isn't available, or if semantic splitting fails at
runtime — ingestion should degrade gracefully rather than crash.
"""
import uuid

from langchain_core.documents import Document

from src.config import settings
from src.pdf_loader import page_for_offset


def _recursive_fallback():
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)


def _build_semantic_splitter(embeddings):
    try:
        from langchain_experimental.text_splitter import SemanticChunker

        splitter = SemanticChunker(
            embeddings,
            breakpoint_threshold_type=settings.SEMANTIC_BREAKPOINT_TYPE,
            breakpoint_threshold_amount=settings.SEMANTIC_BREAKPOINT_AMOUNT,
        )
        return splitter, True
    except Exception as exc:  # noqa: BLE001
        print(f"[semantic_chunker] SemanticChunker unavailable ({exc}); using recursive fallback.")
        return _recursive_fallback(), False


def chunk_pdf_text(full_text: str, source: str, page_offsets, embeddings=None):
    """
    Splits `full_text` into semantically coherent chunks and returns Documents
    with metadata: id (uuid), source, page, chunk_index, splitter.
    """
    from src.vector_store import get_embeddings

    embeddings = embeddings or get_embeddings()
    splitter, is_semantic = _build_semantic_splitter(embeddings)

    try:
        raw_chunks = splitter.split_text(full_text)
    except Exception as exc:  # noqa: BLE001
        print(f"[semantic_chunker] semantic split failed at runtime ({exc}); using recursive fallback.")
        splitter = _recursive_fallback()
        raw_chunks = splitter.split_text(full_text)
        is_semantic = False

    docs = []
    cursor = 0
    for idx, chunk_text in enumerate(raw_chunks):
        start = full_text.find(chunk_text, cursor)
        if start == -1:
            start = cursor
        cursor = start + len(chunk_text)
        page = page_for_offset(start, page_offsets)

        docs.append(
            Document(
                page_content=chunk_text.strip(),
                metadata={
                    "id": str(uuid.uuid4()),
                    "source": source,
                    "page": page,
                    "chunk_index": idx,
                    "splitter": "semantic" if is_semantic else "recursive_fallback",
                },
            )
        )
    return docs