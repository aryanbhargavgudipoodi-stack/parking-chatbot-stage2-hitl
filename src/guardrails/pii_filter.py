"""
PII guardrail: detects and redacts sensitive data before it is returned to
the user or written to logs.

Primary engine: Microsoft Presidio (NLP + regex based PII detection).
Fallback: lightweight regex detection, used automatically if presidio/spacy
aren't installed, so the chatbot keeps working (with reduced accuracy).
"""
import re
from typing import List, Tuple

from src.config import settings

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine

    _PRESIDIO_AVAILABLE = True
except ImportError:
    _PRESIDIO_AVAILABLE = False


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\+?\d[\d\-\s]{7,}\d")
_CC_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

_NLP_CONFIGURATION = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}


def _build_presidio_analyzer():
    try:
        provider = NlpEngineProvider(nlp_configuration=_NLP_CONFIGURATION)
        nlp_engine = provider.create_engine()
        return AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
    except Exception:  # noqa: BLE001
        return AnalyzerEngine()


class PIIFilter:
    def __init__(self, entities=None, language: str = "en"):
        self.entities = entities or settings.PII_ENTITIES_BLOCK
        self.language = language
        if _PRESIDIO_AVAILABLE:
            self.analyzer = _build_presidio_analyzer()
            self.anonymizer = AnonymizerEngine()
        else:
            self.analyzer = None
            self.anonymizer = None

    def scan(self, text: str) -> List[dict]:
        if not text:
            return []
        if self.analyzer is None:
            return self._regex_scan(text)
        results = self.analyzer.analyze(text=text, entities=self.entities, language=self.language)
        return [
            {"entity_type": r.entity_type, "start": r.start, "end": r.end, "score": r.score}
            for r in results
        ]

    def redact(self, text: str) -> Tuple[str, List[dict]]:
        if not text:
            return text, []
        if self.analyzer is None:
            return self._regex_redact(text)
        results = self.analyzer.analyze(text=text, entities=self.entities, language=self.language)
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
        detected = [
            {"entity_type": r.entity_type, "start": r.start, "end": r.end, "score": r.score}
            for r in results
        ]
        return anonymized.text, detected

    def is_safe(self, text: str, score_threshold: float = 0.5) -> bool:
        return not any(e["score"] >= score_threshold for e in self.scan(text))

    def _regex_scan(self, text: str) -> List[dict]:
        found = []
        for name, pattern in (
            ("EMAIL_ADDRESS", _EMAIL_RE),
            ("PHONE_NUMBER", _PHONE_RE),
            ("CREDIT_CARD", _CC_RE),
        ):
            if name in self.entities:
                for m in pattern.finditer(text):
                    found.append({"entity_type": name, "start": m.start(), "end": m.end(), "score": 0.6})
        return found

    def _regex_redact(self, text: str) -> Tuple[str, List[dict]]:
        entities = self._regex_scan(text)
        redacted = text
        for e in sorted(entities, key=lambda x: x["start"], reverse=True):
            redacted = redacted[: e["start"]] + f"<{e['entity_type']}>" + redacted[e["end"]:]
        return redacted, entities