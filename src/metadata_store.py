"""
Relational metadata store for ingested documents and chunks: the auditable,
queryable source of truth for what was ingested, from which file/page, with
which splitter. The vector store is always rebuilt from this DB, so the two
can never drift apart. Also used to generate evaluation questions.
"""
import hashlib
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from src.config import settings

Base = declarative_base()


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id = Column(String, primary_key=True)
    filename = Column(String, unique=True)
    file_hash = Column(String)
    num_pages = Column(Integer)
    num_chunks = Column(Integer)
    ingested_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True)  # same id stored in vector-store metadata
    document_id = Column(String, ForeignKey("source_documents.id"))
    source_file = Column(String)
    page = Column(Integer)
    chunk_index = Column(Integer)
    char_count = Column(Integer)
    splitter = Column(String)
    content = Column(Text)
    embedding_model = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("SourceDocument", back_populates="chunks")


_engine_cache = {}


def _get_engine(db_path: str = None):
    path = db_path or settings.METADATA_DB_PATH
    if path not in _engine_cache:
        engine = create_engine(f"sqlite:///{path}", echo=False)
        Base.metadata.create_all(engine)
        _engine_cache[path] = engine
    return _engine_cache[path]


def _session(db_path: str = None):
    return sessionmaker(bind=_get_engine(db_path))()


def init_db(db_path: str = None):
    _get_engine(db_path)


def file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def is_already_ingested(filename: str, hash_: str, db_path: str = None) -> bool:
    session = _session(db_path)
    try:
        doc = session.query(SourceDocument).filter_by(filename=filename).first()
        return doc is not None and doc.file_hash == hash_
    finally:
        session.close()


def save_document_with_chunks(filename, file_hash_, num_pages, chunk_docs, embedding_model, db_path: str = None):
    session = _session(db_path)
    try:
        existing = session.query(SourceDocument).filter_by(filename=filename).first()
        if existing:
            session.delete(existing)
            session.commit()

        doc_record = SourceDocument(
            id=str(uuid.uuid4()), filename=filename, file_hash=file_hash_,
            num_pages=num_pages, num_chunks=len(chunk_docs),
        )
        session.add(doc_record)
        session.flush()  # assigns doc_record.id for FK use below

        for d in chunk_docs:
            session.add(
                DocumentChunk(
                    id=d.metadata["id"],
                    document_id=doc_record.id,
                    source_file=filename,
                    page=d.metadata.get("page"),
                    chunk_index=d.metadata.get("chunk_index"),
                    char_count=len(d.page_content),
                    splitter=d.metadata.get("splitter"),
                    content=d.page_content,
                    embedding_model=embedding_model,
                )
            )
        session.commit()
        return doc_record.id
    finally:
        session.close()


def get_chunk_by_id(chunk_id: str, db_path: str = None):
    session = _session(db_path)
    try:
        return session.query(DocumentChunk).filter_by(id=chunk_id).first()
    finally:
        session.close()


def list_chunks(db_path: str = None):
    session = _session(db_path)
    try:
        return session.query(DocumentChunk).all()
    finally:
        session.close()


def list_documents(db_path: str = None):
    session = _session(db_path)
    try:
        return session.query(SourceDocument).all()
    finally:
        session.close()