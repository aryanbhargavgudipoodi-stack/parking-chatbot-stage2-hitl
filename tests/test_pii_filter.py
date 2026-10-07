from src.guardrails.pii_filter import PIIFilter


def test_detects_email():
    f = PIIFilter(entities=["EMAIL_ADDRESS"])
    entities = f.scan("Contact me at john.doe@example.com please.")
    assert any(e["entity_type"] == "EMAIL_ADDRESS" for e in entities)


def test_redacts_credit_card():
    f = PIIFilter(entities=["CREDIT_CARD"])
    text = "My card number is 4111111111111111 for payment."
    redacted, entities = f.redact(text)
    assert "4111111111111111" not in redacted
    assert len(entities) >= 1


def test_is_safe_for_clean_text():
    f = PIIFilter()
    assert f.is_safe("What are your opening hours?") is True