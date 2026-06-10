from __future__ import annotations

from src.models.chat_channel import CHAT_CHANNEL_LABELS


def build_enum_registry() -> dict[str, object]:
    return {
        "enums": {
            "ChatChannel": {str(value): label for value, label in sorted(CHAT_CHANNEL_LABELS.items())},
        },
    }
