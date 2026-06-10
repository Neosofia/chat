from __future__ import annotations

import httpx
from werkzeug.exceptions import BadRequest, ServiceUnavailable

from src.bootstrap.config import settings
from src.models.chat_channel import parse_chat_channel
from src.services.interaction_service import require_interaction
from src.services.message_service import create_message, list_messages

AGENT_CONTEXT_START = "<<<NEOSOFIA_AGENT_CONTEXT_START>>>"
AGENT_CONTEXT_END = "<<<NEOSOFIA_AGENT_CONTEXT_END>>>"

NEW_CHAT_SESSION_PRIMING_PROMPT = (
    "We're starting a new chat session. Please greet me and ask how I'm doing."
)

CARE_ASSISTANT_RESPONSE_STYLE = (
    "Keep every reply short: usually 2–4 sentences. "
    "Never write walls of text, bullet lists, or numbered lists. "
    "Offer one or two specific, actionable next steps — not a menu of options. "
    "Ask at most one focused follow-up question when you need more detail."
)

CARE_ASSISTANT_BASE_PROMPT = (
    "You are a supportive post-discharge care assistant for a patient recovery chat. "
    "Write in plain language. "
    f"{CARE_ASSISTANT_RESPONSE_STYLE} "
    "You are not a substitute for emergency care; tell the patient to contact their care "
    "team or emergency services for urgent or worsening symptoms. "
    "Use prior messages in the thread for context when the patient refers to earlier conversation."
)


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
        return CARE_ASSISTANT_BASE_PROMPT
    return (
        f"{CARE_ASSISTANT_BASE_PROMPT}\n\n"
        f"{context_block}\n\n"
        "Use the patient context above when personalizing replies. "
        "Do not repeat the context block verbatim to the patient."
    )


def to_agent_messages(messages: list[dict], *, context: dict | None = None) -> list[dict]:
    agent_messages: list[dict] = [{"role": "system", "content": build_system_prompt(context)}]
    for item in messages:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        if role in {"user", "patient"}:
            agent_messages.append({"role": "user", "content": content})
        elif role in {"assistant", "ai_agent", "clinician"}:
            agent_messages.append({"role": "assistant", "content": content})
    if not any(message["role"] == "user" for message in agent_messages[1:]):
        raise BadRequest("messages must include at least one user turn")
    return agent_messages


def stub_completion_reply(user_message: str, *, context: dict | None = None) -> str:
    lowered = user_message.lower()
    if "starting a new chat session" in lowered:
        first_name = "there"
        if context:
            raw_name = context.get("patient_first_name")
            if isinstance(raw_name, str) and raw_name.strip():
                first_name = raw_name.strip()
        return f"Hi {first_name} — how are you feeling today?"
    if "pain" in lowered:
        return (
            "I hear that your pain is getting worse. Please seek urgent in-person care now, "
            "and I will alert your care team in parallel."
        )
    return (
        "Thanks - I logged your update. Continue monitoring and contact your care team "
        "immediately if symptoms worsen."
    )


def inference_completion_reply(messages: list[dict], *, context: dict | None = None) -> str:
    if not settings.inference_api_key or not settings.inference_completions_url:
        raise ServiceUnavailable("Care assistant inference is not configured")

    payload = {
        "model": settings.inference_model,
        "messages": to_agent_messages(messages, context=context),
        "temperature": settings.inference_temperature,
        "max_completion_tokens": settings.inference_max_completion_tokens,
        "reasoning_effort": settings.inference_reasoning_effort,
    }

    try:
        response = httpx.post(
            settings.inference_completions_url,
            headers={
                "Authorization": f"Bearer {settings.inference_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=settings.inference_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ServiceUnavailable("Care assistant is temporarily unavailable") from exc

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ServiceUnavailable("Care assistant returned an invalid response") from exc

    reply = str(content).strip()
    if not reply:
        raise ServiceUnavailable("Care assistant returned an empty response")
    return reply


def completion_reply(messages: list[dict], *, context: dict | None = None) -> str:
    if settings.inference_api_key and settings.inference_completions_url:
        return inference_completion_reply(messages, context=context)

    if not messages:
        raise BadRequest("messages is required")
    user_message = str(messages[-1].get("content", "")).strip()
    if not user_message:
        raise BadRequest("messages is required")
    return stub_completion_reply(user_message, context=context)


def has_clinician_intervention(rows: list[dict]) -> bool:
    return any(str(row.get("sender_type", "")).strip().lower() == "clinician" for row in rows)


def db_messages_to_completion_messages(rows: list[dict]) -> list[dict]:
    mapped: list[dict] = []
    for row in rows:
        content = str(row.get("content", "")).strip()
        if not content:
            continue
        sender_type = str(row.get("sender_type", "")).strip().lower()
        role = "user" if sender_type == "patient" else "assistant"
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

    reply = completion_reply(
        [{"role": "user", "content": NEW_CHAT_SESSION_PRIMING_PROMPT}],
        context=interaction.context,
    )

    assistant_message = create_message(
        db,
        {
            "chat_interaction_uuid": chat_interaction_uuid,
            "channel": int(channel),
            "sender_type": "ai_agent",
            "content": reply,
        },
    )

    return {
        "message": reply,
        "assistant_message": assistant_message,
    }


def complete_patient_turn(db, payload: dict) -> dict:
    chat_interaction_uuid = str(payload.get("chat_interaction_uuid", "")).strip()
    content = str(payload.get("content", "")).strip()
    if not chat_interaction_uuid or not content:
        raise BadRequest("chat_interaction_uuid and content are required")

    interaction = require_interaction(db, chat_interaction_uuid)
    patient_uuid = str(interaction.patient_uuid)
    channel = parse_chat_channel(payload.get("channel"))

    patient_message = create_message(
        db,
        {
            "chat_interaction_uuid": chat_interaction_uuid,
            "channel": int(channel),
            "sender_type": "patient",
            "sender_uuid": payload.get("sender_uuid") or patient_uuid,
            "content": content,
        },
    )

    history = list_messages(
        db,
        chat_interaction_uuid,
        limit=settings.completion_history_limit,
    )
    if has_clinician_intervention(history):
        return {
            "message": None,
            "patient_message": patient_message,
            "ai_disabled": True,
        }

    reply = completion_reply(
        db_messages_to_completion_messages(history),
        context=interaction.context,
    )

    assistant_message = create_message(
        db,
        {
            "chat_interaction_uuid": chat_interaction_uuid,
            "channel": int(channel),
            "sender_type": "ai_agent",
            "content": reply,
        },
    )

    return {
        "message": reply,
        "patient_message": patient_message,
        "assistant_message": assistant_message,
        "ai_disabled": False,
    }
