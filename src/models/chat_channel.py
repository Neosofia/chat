from __future__ import annotations

from enum import IntEnum

from werkzeug.exceptions import BadRequest


class ChatChannel(IntEnum):
    WEB = 1
    MOBILE_APP = 2
    SMS = 3


CHAT_CHANNEL_LABELS: dict[int, str] = {
    ChatChannel.WEB: "web",
    ChatChannel.MOBILE_APP: "mobile_app",
    ChatChannel.SMS: "sms",
}

_LABEL_TO_CHANNEL: dict[str, ChatChannel] = {
    label: channel for channel, label in CHAT_CHANNEL_LABELS.items()
}

_ALLOWED_CHANNEL_VALUES: frozenset[int] = frozenset(CHAT_CHANNEL_LABELS)


def parse_chat_channel(value: object | None, *, default: ChatChannel = ChatChannel.WEB) -> ChatChannel:
    if value is None:
        return default
    if isinstance(value, bool):
        raise BadRequest("channel must be an integer or label")
    if isinstance(value, int):
        if value not in _ALLOWED_CHANNEL_VALUES:
            raise BadRequest("channel must be one of web, mobile_app, or sms")
        return ChatChannel(value)
    if isinstance(value, str):
        label = value.strip().lower()
        if not label:
            return default
        channel = _LABEL_TO_CHANNEL.get(label)
        if channel is None:
            raise BadRequest("channel must be one of web, mobile_app, or sms")
        return channel
    raise BadRequest("channel must be an integer or label")
