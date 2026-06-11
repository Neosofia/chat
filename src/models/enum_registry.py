from __future__ import annotations

from src.bootstrap.config import inference_configured, settings
from src.models.chat_channel import CHAT_CHANNEL_LABELS


def build_enum_registry() -> dict[str, object]:
    return {
        "enums": {
            "ChatChannel": {str(value): label for value, label in sorted(CHAT_CHANNEL_LABELS.items())},
            "MessageSenderType": {t: t for t in sorted(settings.message_sender_types)},
            "InterventionSenderType": {t: t for t in sorted(settings.intervention_sender_types)},
        },
        "completion": {
            "user_sender_type": settings.completion_user_sender_type,
            "assistant_sender_type": settings.completion_assistant_sender_type,
        },
        "assistant": {
            "available": inference_configured(),
        },
    }
