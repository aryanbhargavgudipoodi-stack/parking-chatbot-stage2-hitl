"""
Loads PDFs page-by-page and merges them into one continuous text per
document (keeping an offset→page map), so semantic chunking operates on
the whole document instead of being artificially restricted per page.
"""
from langchain_community.document_loaders import PyPDFLoader


def load_pdf_pages(pdf_path: str):
    """Returns a list of per-page Documents (metadata includes 'page', 0-indexed)."""
    return PyPDFLoader(pdf_path).load()


def merge_pages_to_full_text(page_docs):
    """
    Joins page documents into one string and records, for each page, the
    (start_char, end_char, page_number) span it occupies. page_number is 1-indexed.
    """
    parts = []
    page_offsets = []
    cursor = 0
    for doc in page_docs:
        text = doc.page_content.strip()
        if not text:
            continue
        start = cursor
        parts.append(text)
        cursor += len(text)
        page_offsets.append((start, cursor, doc.metadata.get("page", 0) + 1))
        parts.append("\n\n")
        cursor += 2
    return "".join(parts), page_offsets


def page_for_offset(offset: int, page_offsets):
    """Maps a character offset back to its 1-indexed source page number."""
    for start, end, page_num in page_offsets:
        if start <= offset <= end:
            return page_num
    return page_offsets[-1][2] if page_offsets else 1