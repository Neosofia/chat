from __future__ import annotations

import httpx
from werkzeug.exceptions import BadRequest, ServiceUnavailable

from src.bootstrap.config import inference_configured, settings
from src.models.chat_channel import parse_chat_channel
from src.services.interaction_service import require_interaction
from src.services.message_service import create_message, has_intervention, list_messages

INFERENCE_TIMEOUT_SECONDS = 60.0
INFERENCE_MAX_COMPLETION_TOKENS = 1024
COMPLETION_HISTORY_LIMIT = 200

AGENT_CONTEXT_START = "<<<NEOSOFIA_AGENT_CONTEXT_START>>>"
AGENT_CONTEXT_END = "<<<NEOSOFIA_AGENT_CONTEXT_END>>>"


def require_assistant_available() -> None:
    if not inference_configured():
        raise ServiceUnavailable("AI assistant is not available")


def format_agent_context_block(context: dict | None) -> str:
    if not context:
        return ""

    lines: list[str] = []
    for key in sorted(context):
        value = context[key]
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        lines.append(f"{key}: {text}")

    if not lines:
        return ""

    body = "\n".join(lines)
    return f"{AGENT_CONTEXT_START}\n{body}\n{AGENT_CONTEXT_END}"


def build_system_prompt(context: dict | None) -> str:
    context_block = format_agent_context_block(context)
    if not context_block:
        return settings.agent_instructions
    return f"{settings.agent_instructions}\n\n{context_block}"


def to_agent_messages(messages: list[dict], *, context: dict | None = None) -> list[dict]:
    agent_messages: list[dict] = [{"role": "system", "content": build_system_prompt(context)}]
    for item in messages:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        if role == "user" or role == settings.completion_user_sender_type:
            agent_messages.append({"role": "user", "content": content})
        elif role == "assistant" or role in {
            settings.completion_assistant_sender_type,
            *settings.intervention_sender_types,
        }:
            agent_messages.append({"role": "assistant", "content": content})
    if not any(message["role"] == "user" for message in agent_messages[1:]):
        raise BadRequest("messages must include at least one user turn")
    return agent_messages


def completion_reply(messages: list[dict], *, context: dict | None = None) -> str:
    require_assistant_available()

    payload = {
        "model": settings.inference_model,
        "messages": to_agent_messages(messages, context=context),
        "temperature": settings.inference_temperature,
        "max_completion_tokens": INFERENCE_MAX_COMPLETION_TOKENS,
    }

    try:
        response = httpx.post(
            settings.inference_completions_url,
            headers={
                "Authorization": f"Bearer {settings.inference_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=INFERENCE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ServiceUnavailable("AI assistant is temporarily unavailable") from exc

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ServiceUnavailable("AI assistant returned an invalid response") from exc

    reply = str(content).strip()
    if not reply:
        raise ServiceUnavailable("AI assistant returned an empty response")
    return reply


def db_messages_to_completion_messages(rows: list[dict]) -> list[dict]:
    mapped: list[dict] = []
    for row in rows:
        content = str(row.get("content", "")).strip()
        if not content:
            continue
        sender_type = str(row.get("sender_type", "")).strip().lower()
        role = "user" if sender_type == settings.completion_user_sender_type else "assistant"
        mapped.append({"role": role, "content": content})
    return mapped


def start_chat_session(db, payload: dict) -> dict:
    chat_interaction_uuid = str(payload.get("chat_interaction_uuid", "")).strip()
    if not chat_interaction_uuid:
        raise BadRequest("chat_interaction_uuid is required")

    interaction = require_interaction(db, chat_interaction_uuid)
    channel = parse_chat_channel(payload.get("channel"))
    history = list_messages(db, chat_interaction_uuid, limit=1)
    if history:
        raise BadRequest("session_start is only allowed for empty chat interactions")

    require_assistant_available()
    reply = completion_reply(
        [{"role": "user", "content": settings.agent_priming_prompt}],
        context=interaction.context,
    )

    assistant_message = create_message(
        db,
        {
            "chat_interaction_uuid": chat_interaction_uuid,
            "channel": int(channel),
            "sender_type": settings.completion_assistant_sender_type,
            "content": reply,
        },
    )

    return {
        "message": reply,
        "assistant_message": assistant_message,
    }


def complete_user_turn(db, payload: dict) -> dict:
    chat_interaction_uuid = str(payload.get("chat_interaction_uuid", "")).strip()
    content = str(payload.get("content", "")).strip()
    if not chat_interaction_uuid or not content:
        raise BadRequest("chat_interaction_uuid and content are required")

    interaction = require_interaction(db, chat_interaction_uuid)
    user_uuid = str(interaction.user_uuid)
    channel = parse_chat_channel(payload.get("channel"))

    existing_history = list_messages(
        db,
        chat_interaction_uuid,
        limit=COMPLETION_HISTORY_LIMIT,
    )
    if has_intervention(existing_history):
        user_message = create_message(
            db,
            {
                "chat_interaction_uuid": chat_interaction_uuid,
                "channel": int(channel),
                "sender_type": settings.completion_user_sender_type,
                "sender_uuid": payload.get("sender_uuid") or user_uuid,
                "content": content,
            },
        )
        return {
            "message": None,
            "user_message": user_message,
            "intervention": True,
        }

    require_assistant_available()
    reply = completion_reply(
        db_messages_to_completion_messages(
            [
                *existing_history,
                {
                    "sender_type": settings.completion_user_sender_type,
                    "content": content,
                },
            ],
        ),
        context=interaction.context,
    )

    user_message = create_message(
        db,
        {
            "chat_interaction_uuid": chat_interaction_uuid,
            "channel": int(channel),
            "sender_type": settings.completion_user_sender_type,
            "sender_uuid": payload.get("sender_uuid") or user_uuid,
            "content": content,
        },
    )

    assistant_message = create_message(
        db,
        {
            "chat_interaction_uuid": chat_interaction_uuid,
            "channel": int(channel),
            "sender_type": settings.completion_assistant_sender_type,
            "content": reply,
        },
    )

    return {
        "message": reply,
        "user_message": user_message,
        "assistant_message": assistant_message,
        "intervention": False,
    }
