import pytest
from werkzeug.exceptions import BadRequest

from src.models.chat_channel import ChatChannel, parse_chat_channel

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, ChatChannel.WEB),
        ("web", ChatChannel.WEB),
        ("WEB", ChatChannel.WEB),
        (1, ChatChannel.WEB),
        ("mobile_app", ChatChannel.MOBILE_APP),
        (2, ChatChannel.MOBILE_APP),
        ("sms", ChatChannel.SMS),
        (3, ChatChannel.SMS),
    ],
)
def test_parse_chat_channel_accepts_valid_values(value, expected):
    assert parse_chat_channel(value) == expected


@pytest.mark.parametrize("value", [0, 4, "app", True])
def test_parse_chat_channel_rejects_invalid_values(value):
    with pytest.raises(BadRequest, match="channel"):
        parse_chat_channel(value)
