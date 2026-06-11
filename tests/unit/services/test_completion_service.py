from unittest.mock import MagicMock, patch

import httpx
import pytest
from werkzeug.exceptions import BadRequest, ServiceUnavailable

from src.bootstrap.config import settings
from src.services.completion_service import (
    AGENT_CONTEXT_END,
    AGENT_CONTEXT_START,
    build_system_prompt,
    complete_user_turn,
    completion_reply,
    db_messages_to_completion_messages,
    format_agent_context_block,
    require_assistant_available,
    start_chat_session,
    to_agent_messages,
)
from src.services.message_service import has_intervention

pytestmark = pytest.mark.unit

INTERACTION = "00000000-0000-7000-8000-000000000003"

def _inference_ready():
    return patch("src.services.completion_service.inference_configured", return_value=True)


def test_format_agent_context_block_uses_delineated_markers():
    block = format_agent_context_block(
        {
            "procedure_name": "Appendectomy",
            "patient_first_name": "Alex",
        },
    )
    assert block.startswith(AGENT_CONTEXT_START)
    assert block.endswith(AGENT_CONTEXT_END)
    assert "patient_first_name: Alex" in block
    assert "procedure_name: Appendectomy" in block


def test_build_system_prompt_includes_context_block_when_present():
    prompt = build_system_prompt({"patient_first_name": "Alex"})
    assert AGENT_CONTEXT_START in prompt
    assert "patient context appears below" in prompt
    assert prompt.endswith(f"patient_first_name: Alex\n{AGENT_CONTEXT_END}")
    assert "2–4 sentences" in prompt
    assert "not a menu of options" in prompt


def test_to_agent_messages_maps_roles_and_requires_user_turn():
    agent_messages = to_agent_messages(
        [
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "I have a question"},
        ],
    )
    assert agent_messages[0]["role"] == "system"
    assert agent_messages[1:] == [
        {"role": "assistant", "content": "Hello"},
        {"role": "user", "content": "I have a question"},
    ]

    with pytest.raises(BadRequest, match="at least one user turn"):
        to_agent_messages([{"role": "assistant", "content": "Only assistant"}])


def test_require_assistant_available_rejects_unconfigured_inference():
    with patch("src.services.completion_service.inference_configured", return_value=False):
        with pytest.raises(ServiceUnavailable, match="not available"):
            require_assistant_available()


def test_completion_reply_requires_inference_configuration():
    with patch("src.services.completion_service.inference_configured", return_value=False):
        with pytest.raises(ServiceUnavailable, match="not available"):
            completion_reply([{"role": "user", "content": "feeling ok"}])


@patch("src.services.completion_service.httpx.post")
def test_completion_reply_returns_model_content(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "  Rest and hydrate.  "}}],
    }
    mock_post.return_value = mock_response

    with (
        _inference_ready(),
        patch.object(settings, "inference_api_key", "test-key"),
        patch.object(settings, "inference_completions_url", "https://inference.example/v1/chat/completions"),
        patch.object(settings, "inference_model", "test-model"),
    ):
        reply = completion_reply([{"role": "user", "content": "I feel dizzy"}])

    assert reply == "Rest and hydrate."
    request_json = mock_post.call_args.kwargs["json"]
    assert request_json["model"] == "test-model"
    assert request_json["messages"][0]["role"] == "system"
    assert request_json["messages"][-1] == {"role": "user", "content": "I feel dizzy"}


@patch("src.services.completion_service.httpx.post", side_effect=httpx.HTTPError("boom"))
def test_completion_reply_maps_http_errors(mock_post):
    with (
        _inference_ready(),
        patch.object(settings, "inference_api_key", "test-key"),
        patch.object(settings, "inference_completions_url", "https://inference.example/v1/chat/completions"),
        patch.object(settings, "inference_model", "test-model"),
    ):
        with pytest.raises(ServiceUnavailable, match="temporarily unavailable"):
            completion_reply([{"role": "user", "content": "hello"}])


def test_has_intervention_detects_intervention_sender():
    assert has_intervention([{"sender_type": "clinician", "content": "Hi"}])
    assert not has_intervention([{"sender_type": "ai_agent", "content": "Hi"}])


def test_db_messages_to_completion_messages_maps_sender_types():
    mapped = db_messages_to_completion_messages(
        [
            {"sender_type": "patient", "content": "Hi"},
            {"sender_type": "ai_agent", "content": "Hello"},
            {"sender_type": "clinician", "content": "Checking in"},
        ],
    )
    assert mapped == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
        {"role": "assistant", "content": "Checking in"},
    ]


@patch("src.services.completion_service.require_assistant_available")
@patch("src.services.completion_service.completion_reply", return_value="assistant reply")
@patch("src.services.completion_service.list_messages", return_value=[{"sender_type": "patient", "content": "Hi"}])
@patch("src.services.completion_service.create_message")
@patch("src.services.completion_service.require_interaction")
def test_complete_user_turn_persists_after_inference(
    mock_require,
    mock_create,
    mock_list,
    mock_reply,
    mock_require_assistant,
):
    mock_require.return_value = MagicMock(
        user_uuid="00000000-0000-7000-8000-000000000001",
        context={"patient_first_name": "Alex"},
    )
    mock_create.side_effect = [
        {"message_uuid": "p1", "sender_type": "patient", "content": "Hi"},
        {"message_uuid": "a1", "sender_type": "ai_agent", "content": "assistant reply"},
    ]

    result = complete_user_turn(
        object(),
        {
            "chat_interaction_uuid": INTERACTION,
            "content": "Hi",
        },
    )

    assert result["message"] == "assistant reply"
    assert mock_list.call_count == 1
    assert mock_create.call_count == 2
    mock_reply.assert_called_once_with(
        [{"role": "user", "content": "Hi"}, {"role": "user", "content": "Hi"}],
        context={"patient_first_name": "Alex"},
    )


@patch("src.services.completion_service.completion_reply")
@patch(
    "src.services.completion_service.list_messages",
    return_value=[
        {"sender_type": "patient", "content": "Hi"},
        {"sender_type": "clinician", "content": "I will follow up"},
    ],
)
@patch("src.services.completion_service.create_message")
@patch("src.services.completion_service.require_interaction")
def test_complete_user_turn_skips_ai_after_intervention(
    mock_require,
    mock_create,
    mock_list,
    mock_reply,
):
    mock_require.return_value = MagicMock(
        user_uuid="00000000-0000-7000-8000-000000000001",
        context=None,
    )
    mock_create.return_value = {
        "message_uuid": "p1",
        "sender_type": "patient",
        "content": "Any update?",
    }

    result = complete_user_turn(
        object(),
        {
            "chat_interaction_uuid": INTERACTION,
            "content": "Any update?",
        },
    )

    assert result["intervention"] is True
    assert result["user_message"]["content"] == "Any update?"
    assert "assistant_message" not in result
    assert result["message"] is None
    mock_reply.assert_not_called()
    mock_create.assert_called_once()


@patch("src.services.completion_service.require_assistant_available")
@patch("src.services.completion_service.completion_reply", side_effect=ServiceUnavailable("down"))
@patch("src.services.completion_service.list_messages", return_value=[])
@patch("src.services.completion_service.create_message")
@patch("src.services.completion_service.require_interaction")
def test_complete_user_turn_does_not_persist_when_inference_fails(
    mock_require,
    mock_create,
    mock_list,
    mock_reply,
    mock_require_assistant,
):
    mock_require.return_value = MagicMock(
        user_uuid="00000000-0000-7000-8000-000000000001",
        context=None,
    )

    with pytest.raises(ServiceUnavailable, match="down"):
        complete_user_turn(
            object(),
            {
                "chat_interaction_uuid": INTERACTION,
                "content": "hello",
            },
        )

    mock_create.assert_not_called()


def test_complete_user_turn_requires_fields():
    with pytest.raises(BadRequest, match="chat_interaction_uuid and content"):
        complete_user_turn(object(), {"content": "hello"})


@patch("src.services.completion_service.require_assistant_available")
@patch("src.services.completion_service.completion_reply", return_value="Hi Alex — how are you feeling today?")
@patch("src.services.completion_service.list_messages", return_value=[])
@patch("src.services.completion_service.create_message")
@patch("src.services.completion_service.require_interaction")
def test_start_chat_session_primes_empty_thread(
    mock_require,
    mock_create,
    mock_list,
    mock_reply,
    mock_require_assistant,
):
    mock_require.return_value = MagicMock(context={"patient_first_name": "Alex"})
    mock_create.return_value = {
        "message_uuid": "a1",
        "sender_type": "ai_agent",
        "content": "Hi Alex — how are you feeling today?",
    }

    result = start_chat_session(
        object(),
        {"chat_interaction_uuid": INTERACTION},
    )

    assert result["message"] == "Hi Alex — how are you feeling today?"
    mock_reply.assert_called_once_with(
        [{"role": "user", "content": settings.agent_priming_prompt}],
        context={"patient_first_name": "Alex"},
    )
    mock_create.assert_called_once()


@patch("src.services.completion_service.list_messages", return_value=[{"sender_type": "patient", "content": "Hi"}])
@patch("src.services.completion_service.require_interaction")
def test_start_chat_session_rejects_non_empty_thread(mock_require, mock_list):
    mock_require.return_value = MagicMock(context=None)
    with pytest.raises(BadRequest, match="empty chat interactions"):
        start_chat_session(object(), {"chat_interaction_uuid": INTERACTION})
