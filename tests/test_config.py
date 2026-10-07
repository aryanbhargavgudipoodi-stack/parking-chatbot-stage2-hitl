import importlib

from src import config as config_module


def test_default_top_k_is_positive_integer(monkeypatch):
    monkeypatch.delenv("RAG_TOP_K", raising=False)
    importlib.reload(config_module)
    assert isinstance(config_module.settings.TOP_K, int)
    assert config_module.settings.TOP_K > 0


def test_pii_entities_block_parsed_as_list(monkeypatch):
    monkeypatch.setenv("PII_ENTITIES_BLOCK", "EMAIL_ADDRESS,PHONE_NUMBER")
    importlib.reload(config_module)
    assert config_module.settings.PII_ENTITIES_BLOCK == ["EMAIL_ADDRESS", "PHONE_NUMBER"]
    monkeypatch.delenv("PII_ENTITIES_BLOCK", raising=False)
    importlib.reload(config_module)