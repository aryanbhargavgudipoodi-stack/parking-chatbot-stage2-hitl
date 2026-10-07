from langchain_core.documents import Document

from src.pdf_loader import merge_pages_to_full_text, page_for_offset


def test_merge_pages_preserves_order():
    pages = [
        Document(page_content="Page one content.", metadata={"page": 0}),
        Document(page_content="Page two content.", metadata={"page": 1}),
    ]
    full_text, offsets = merge_pages_to_full_text(pages)
    assert full_text.index("Page one") < full_text.index("Page two")
    assert len(offsets) == 2


def test_page_for_offset_maps_correctly():
    pages = [
        Document(page_content="A" * 10, metadata={"page": 0}),
        Document(page_content="B" * 10, metadata={"page": 1}),
    ]
    _, offsets = merge_pages_to_full_text(pages)
    assert page_for_offset(0, offsets) == 1
    assert page_for_offset(offsets[-1][0], offsets) == 2