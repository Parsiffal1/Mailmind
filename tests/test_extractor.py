from pydantic import ValidationError

from mailmind.extractor import MockExtractor, load_system_prompt
from mailmind.models import EmailRecord, ExtractionResult


def test_schema_validates_llm_shape():
    result = ExtractionResult.from_llm_json(
        {
            "has_action": True,
            "tasks": [
                {
                    "description": "Submit application",
                    "due_at": "2026-05-12T23:59:00Z",
                    "priority": "high",
                    "requires_reply": False,
                    "needs_review": False,
                }
            ],
            "deadlines": [],
            "priority": "high",
            "requires_reply": False,
            "reason": "Deadline present.",
        }
    )

    assert result.has_action is True
    assert result.tasks[0].priority == "high"


def test_schema_rejects_empty_task_description():
    try:
        ExtractionResult.from_llm_json(
            {
                "has_action": True,
                "tasks": [{"description": "", "priority": "medium"}],
                "deadlines": [],
                "priority": "medium",
                "requires_reply": False,
                "reason": "",
            }
        )
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError")


def test_mock_extractor_marks_vague_deadline_for_review():
    email = EmailRecord(id="msg-1", sender="a@example.com", subject="Action required", body="Please reply ASAP.")

    result = MockExtractor().extract(email)

    assert result.has_action is True
    assert result.tasks[0].needs_review is True
    assert result.tasks[0].requires_reply is True


def test_system_prompt_is_conservative_and_forbids_generic_task_titles():
    prompt = load_system_prompt()

    assert "Be conservative" in prompt
    assert "Do Not Create Tasks For" in prompt
    assert "Review and act on" in prompt
    assert "Optional opportunities should usually produce `has_action=false`" in prompt
