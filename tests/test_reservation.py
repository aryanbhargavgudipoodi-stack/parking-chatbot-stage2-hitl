from src.reservation import ReservationAgent, ReservationDetails


class _FakeStructuredLLM:
    def __init__(self, responses):
        self._responses = list(responses)

    def invoke(self, _messages):
        return self._responses.pop(0)


class _FakeLLM:
    def __init__(self, responses):
        self._responses = responses

    def with_structured_output(self, _schema):
        return _FakeStructuredLLM(self._responses)


def test_missing_fields_detected_initially():
    details = ReservationDetails()
    assert set(details.missing_fields()) == {
        "first_name", "last_name", "car_number", "period_start", "period_end"
    }
    assert details.is_complete() is False


def test_update_merges_new_information():
    agent = ReservationAgent(
        llm=_FakeLLM([
            ReservationDetails(first_name="Jane"),
            ReservationDetails(last_name="Doe", car_number="ABC123"),
        ])
    )
    agent.update_from_message("My name is Jane")
    assert agent.state.first_name == "Jane"

    agent.update_from_message("Doe, car ABC123")
    assert agent.state.first_name == "Jane"
    assert agent.state.last_name == "Doe"
    assert agent.state.car_number == "ABC123"


def test_next_question_progresses_to_missing_field():
    agent = ReservationAgent(llm=_FakeLLM([]))
    agent.state = ReservationDetails(first_name="Jane", last_name="Doe", car_number="ABC123")
    question = agent.next_question()
    assert "start" in question.lower()