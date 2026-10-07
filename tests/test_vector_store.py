from langchain_core.documents import Document

from tests.fakes import DeterministicFakeEmbeddings


def test_vector_store_round_trip(tmp_path):
    from langchain_community.vectorstores import Chroma

    docs = [
        Document(page_content="Downtown garage hours are 6am to 11pm.", metadata={"id": "d1"}),
        Document(page_content="Airport parking is open 24 hours.", metadata={"id": "d2"}),
    ]
    vs = Chroma.from_documents(docs, DeterministicFakeEmbeddings(), persist_directory=str(tmp_path))
    retriever = vs.as_retriever(search_kwargs={"k": 1})

    results = retriever.invoke("Downtown garage hours are 6am to 11pm.")
    assert results[0].metadata["id"] == "d1"


def test_vector_store_metadata_preserved_on_retrieval(tmp_path):
    from langchain_community.vectorstores import Chroma

    docs = [
        Document(
            page_content="Mall parking costs two dollars per hour.",
            metadata={"id": "d3", "source": "pricing.pdf", "page": 2},
        ),
    ]
    vs = Chroma.from_documents(docs, DeterministicFakeEmbeddings(), persist_directory=str(tmp_path))
    retriever = vs.as_retriever(search_kwargs={"k": 1})

    results = retriever.invoke("How much does mall parking cost?")
    assert results[0].metadata["source"] == "pricing.pdf"
    assert results[0].metadata["page"] == 2


def test_build_and_load_vector_store_round_trip(tmp_path, monkeypatch):
    """Exercises the real build_vector_store/load_vector_store wrappers
    (Chroma backend) with injected fake embeddings — no network calls."""
    monkeypatch.setenv("VECTOR_BACKEND", "chroma")
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))

    from src.vector_store import build_vector_store, get_retriever, load_vector_store

    docs = [Document(page_content="Airport parking never closes.", metadata={"id": "x1"})]
    build_vector_store(docs, embeddings=DeterministicFakeEmbeddings(), force_rebuild=True)

    vs = load_vector_store(embeddings=DeterministicFakeEmbeddings())
    retriever = get_retriever(vs, k=1)
    results = retriever.invoke("When is airport parking open?")
    assert results[0].metadata["id"] == "x1"