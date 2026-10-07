"""
Vector store integration. Tries Milvus first, falls back to a local Chroma
store if Milvus is unreachable or VECTOR_BACKEND=chroma is set.

- build_vector_store(docs, ...) is used by the ingestion pipeline to
  (re)create the store from a given set of chunks.
- load_vector_store() is used by the chatbot / evaluator to attach to an
  already-built store without re-ingesting anything.

Both accept an optional `embeddings` argument for dependency injection
(used heavily in tests to avoid real network/API calls).
"""
import os

from src.config import settings


def get_embeddings():
    backend = os.getenv("EMBEDDING_BACKEND", "openai")
    if backend == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=settings.EMBEDDING_MODEL, api_key=settings.OPENAI_API_KEY)
    from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def build_vector_store(docs, embeddings=None, force_rebuild: bool = False):
    embeddings = embeddings or get_embeddings()
    backend = os.getenv("VECTOR_BACKEND", "milvus")

    if backend == "milvus":
        try:
            from langchain_community.vectorstores import Milvus

            connection_args = {"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT}
            return Milvus.from_documents(
                docs, embeddings,
                collection_name=settings.MILVUS_COLLECTION,
                connection_args=connection_args,
                drop_old=force_rebuild,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[vector_store] Milvus unavailable ({exc}); falling back to Chroma.")

    from langchain_community.vectorstores import Chroma

    persist_dir = os.getenv("CHROMA_DIR", ".chroma_store")
    return Chroma.from_documents(docs, embeddings, persist_directory=persist_dir)


def load_vector_store(embeddings=None):
    """Attaches to an already-built vector store. Run data/ingest.py first."""
    embeddings = embeddings or get_embeddings()
    backend = os.getenv("VECTOR_BACKEND", "milvus")

    if backend == "milvus":
        try:
            from langchain_community.vectorstores import Milvus

            connection_args = {"host": settings.MILVUS_HOST, "port": settings.MILVUS_PORT}
            return Milvus(
                embedding_function=embeddings,
                collection_name=settings.MILVUS_COLLECTION,
                connection_args=connection_args,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[vector_store] Milvus unavailable ({exc}); falling back to Chroma.")

    from langchain_community.vectorstores import Chroma

    persist_dir = os.getenv("CHROMA_DIR", ".chroma_store")
    return Chroma(embedding_function=embeddings, persist_directory=persist_dir)


def get_retriever(vectorstore, k: int = None):
    return vectorstore.as_retriever(search_kwargs={"k": k or settings.TOP_K})