import pytest
from unittest.mock import MagicMock

import data.ingest as ingest_module


def test_ingest_all_raises_when_no_pdfs(tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest_module.ingest_all(pdf_dir=str(tmp_path))


def test_ingest_all_skips_unchanged_and_rebuilds_from_metadata_db(tmp_path, monkeypatch):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    (pdf_dir / "a.pdf").write_text("dummy")
    (pdf_dir / "b.pdf").write_text("dummy")

    monkeypatch.setattr(ingest_module, "init_db", lambda: None)
    monkeypatch.setattr(ingest_module, "get_embeddings", lambda: object())
    monkeypatch.setattr(ingest_module, "file_hash", lambda path: "same-hash")
    monkeypatch.setattr(
        ingest_module, "is_already_ingested",
        lambda filename, digest: filename == "a.pdf",
    )
    monkeypatch.setattr(ingest_module, "load_pdf_pages", lambda path: ["page"])
    monkeypatch.setattr(ingest_module, "merge_pages_to_full_text", lambda pages: ("full text", [(0, 4, 1)]))

    fake_chunk_docs = [MagicMock(metadata={"id": "c1"}, page_content="chunk")]
    monkeypatch.setattr(ingest_module, "chunk_pdf_text", lambda *args, **kwargs: fake_chunk_docs)

    save_calls = []
    monkeypatch.setattr(
        ingest_module, "save_document_with_chunks",
        lambda **kwargs: save_calls.append(kwargs["filename"]),
    )

    stored_chunk = MagicMock(id="c1", content="chunk", source_file="b.pdf", page=1, chunk_index=0, splitter="semantic")
    monkeypatch.setattr(ingest_module, "list_chunks", lambda: [stored_chunk])

    build_calls = {}
    monkeypatch.setattr(
        ingest_module, "build_vector_store",
        lambda docs, **kwargs: build_calls.setdefault("docs", docs),
    )

    ingest_module.ingest_all(pdf_dir=str(pdf_dir), force=False)

    assert save_calls == ["b.pdf"]       # only the changed file was (re)processed
    assert len(build_calls["docs"]) == 1  # vector store rebuilt from metadata DB chunks