from langchain_core.documents import Document

from src.metadata_store import init_db, is_already_ingested, list_chunks, list_documents, save_document_with_chunks


def _fake_chunk(idx, chunk_id):
    return Document(
        page_content=f"Chunk number {idx} content about parking.",
        metadata={"id": chunk_id, "source": "demo.pdf", "page": 1, "chunk_index": idx, "splitter": "semantic"},
    )


def test_save_and_list_chunks(tmp_path):
    db_path = str(tmp_path / "meta.db")
    init_db(db_path=db_path)

    chunks = [_fake_chunk(0, "chunk-a"), _fake_chunk(1, "chunk-b")]
    doc_id = save_document_with_chunks("demo.pdf", "hash1", 1, chunks, "openai", db_path=db_path)
    assert doc_id is not None

    stored = list_chunks(db_path=db_path)
    assert {c.id for c in stored} == {"chunk-a", "chunk-b"}

    docs = list_documents(db_path=db_path)
    assert len(docs) == 1 and docs[0].num_chunks == 2


def test_is_already_ingested_detects_change(tmp_path):
    db_path = str(tmp_path / "meta.db")
    init_db(db_path=db_path)
    save_document_with_chunks("demo.pdf", "hash1", 1, [_fake_chunk(0, "chunk-a")], "openai", db_path=db_path)

    assert is_already_ingested("demo.pdf", "hash1", db_path=db_path) is True
    assert is_already_ingested("demo.pdf", "hash2", db_path=db_path) is False