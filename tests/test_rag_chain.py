from langchain_core.documents import Document

from src.rag_chain import Intent, RagChain


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeStructuredLLM:
    def __init__(self, value):
        self._value = value

    def invoke(self, _messages):
        return self._value


class _FakeLLM:
    def __init__(self, intent_label="static_info", answer_text="42"):
        self._intent_label = intent_label
        self._answer_text = answer_text

    def with_structured_output(self, _schema):
        return _FakeStructuredLLM(Intent(label=self._intent_label))

    def invoke(self, _messages):
        return _FakeMessage(self._answer_text)


class _FakeRetriever:
    def invoke(self, _query):
        return [Document(page_content="Downtown garage opens at 6am.", metadata={"id": "doc_hours_1"})]


def test_classify_intent():
    rag = RagChain(retriever=_FakeRetriever(), llm=_FakeLLM(intent_label="dynamic_info"))
    assert rag.classify_intent("What's the price right now?") == "dynamic_info"


def test_answer_static_returns_sources_and_answer():
    rag = RagChain(retriever=_FakeRetriever(), llm=_FakeLLM(answer_text="It opens at 6am."))
    result = rag.answer_static("When does downtown garage open?")
    assert result["sources"] == ["doc_hours_1"]
    assert "6am" in result["answer"]

def test_classify_intent_status_check():
    rag = RagChain(retriever=_FakeRetriever(), llm=_FakeLLM(intent_label="status_check"))
    assert rag.classify_intent("What's the status of my reservation?") == "status_check"