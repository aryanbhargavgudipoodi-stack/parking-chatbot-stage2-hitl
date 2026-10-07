"""
PDF ingestion pipeline:
  1. Load each PDF under data/pdfs/ (one Document per page).
  2. Merge pages into one continuous text per source file.
  3. Semantically chunk that text (meaning-based splits, not fixed-size).
  4. Persist chunk + document metadata to the metadata DB (source of truth).
  5. Rebuild the vector store from the metadata DB.

Usage:
    python -m data.ingest            # only (re)processes new/changed PDFs
    python -m data.ingest --force    # reprocesses everything
"""
import glob
import os
import sys

from langchain_core.documents import Document

from src.config import settings
from src.metadata_store import file_hash, init_db, is_already_ingested, list_chunks, save_document_with_chunks
from src.pdf_loader import load_pdf_pages, merge_pages_to_full_text
from src.semantic_chunker import chunk_pdf_text
from src.vector_store import build_vector_store, get_embeddings


def ingest_all(force: bool = False, pdf_dir: str = None):
    pdf_dir = pdf_dir or settings.PDF_DIR
    init_db()
    embeddings = get_embeddings()
    embedding_backend = os.getenv("EMBEDDING_BACKEND", "openai")

    pdf_paths = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))
    if not pdf_paths:
        raise FileNotFoundError(
            f"No PDFs found in {pdf_dir}. Run `python -m data.generate_sample_pdfs` "
            "to create demo PDFs, or add your own files there."
        )

    any_changes = False
    for path in pdf_paths:
        filename = os.path.basename(path)
        digest = file_hash(path)

        if not force and is_already_ingested(filename, digest):
            print(f"[ingest] {filename} unchanged, skipping.")
            continue

        any_changes = True
        print(f"[ingest] Processing {filename} ...")
        pages = load_pdf_pages(path)
        full_text, page_offsets = merge_pages_to_full_text(pages)

        chunk_docs = chunk_pdf_text(full_text, source=filename, page_offsets=page_offsets, embeddings=embeddings)
        print(f"[ingest]  -> {len(chunk_docs)} semantic chunks")

        save_document_with_chunks(
            filename=filename, file_hash_=digest, num_pages=len(pages),
            chunk_docs=chunk_docs, embedding_model=embedding_backend,
        )

    if not any_changes and not force:
        print("[ingest] No changed PDFs detected; vector store left untouched. Use --force to rebuild anyway.")
        return

    print("[ingest] Rebuilding vector store from the metadata DB (single source of truth) ...")
    stored_chunks = list_chunks()
    docs = [
        Document(
            page_content=c.content,
            metadata={
                "id": c.id, "source": c.source_file, "page": c.page,
                "chunk_index": c.chunk_index, "splitter": c.splitter,
            },
        )
        for c in stored_chunks
    ]
    build_vector_store(docs, embeddings=embeddings, force_rebuild=True)
    print(f"[ingest] Done. Vector store now holds {len(docs)} chunks across {len(pdf_paths)} source PDFs.")


if __name__ == "__main__":
    ingest_all(force="--force" in sys.argv)