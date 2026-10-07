from src.semantic_chunker import chunk_pdf_text
from tests.fakes import DeterministicFakeEmbeddings


def test_chunk_pdf_text_produces_documents_with_metadata():
    text = (
        "Downtown Garage is open from six in the morning until eleven at night. "
        "It is located two blocks from the train station. "
        "Pricing is three dollars and fifty cents per hour. "
        "Airport Parking operates all day and all night without closing. "
        "It costs five dollars per hour due to the extra services offered."
    )
    page_offsets = [(0, len(text), 1)]
    chunks = chunk_pdf_text(text, source="demo.pdf", page_offsets=page_offsets, embeddings=DeterministicFakeEmbeddings())

    assert len(chunks) >= 1
    for c in chunks:
        assert c.metadata["source"] == "demo.pdf"
        assert "id" in c.metadata
        assert c.metadata["page"] == 1


def test_chunk_pdf_text_ids_are_unique_and_indexed():
    text = "Sentence one is here. Sentence two is here. Sentence three is here. Sentence four is here."
    page_offsets = [(0, len(text), 1)]
    chunks = chunk_pdf_text(text, source="demo.pdf", page_offsets=page_offsets, embeddings=DeterministicFakeEmbeddings())

    ids = [c.metadata["id"] for c in chunks]
    indices = [c.metadata["chunk_index"] for c in chunks]
    assert len(ids) == len(set(ids))
    assert indices == sorted(indices)