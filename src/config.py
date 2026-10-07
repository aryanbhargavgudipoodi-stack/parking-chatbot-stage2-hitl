import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
    MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "parking_knowledge")

    SQL_DB_PATH = os.getenv("SQL_DB_PATH", "data/parking_dynamic.db")
    METADATA_DB_PATH = os.getenv("METADATA_DB_PATH", "data/metadata.db")
    PDF_DIR = os.getenv("PDF_DIR", "data/pdfs")

    TOP_K = int(os.getenv("RAG_TOP_K", 4))

    SEMANTIC_BREAKPOINT_TYPE = os.getenv("SEMANTIC_BREAKPOINT_TYPE", "percentile")
    SEMANTIC_BREAKPOINT_AMOUNT = float(os.getenv("SEMANTIC_BREAKPOINT_AMOUNT", 90))

    ADMIN_DB_PATH = os.getenv("ADMIN_DB_PATH", "data/admin_requests.db")
    
    PII_ENTITIES_BLOCK = os.getenv(
        "PII_ENTITIES_BLOCK",
        "CREDIT_CARD,EMAIL_ADDRESS,IBAN_CODE,US_SSN,PHONE_NUMBER",
    ).split(",")


settings = Settings()