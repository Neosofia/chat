import pytest

from src.bootstrap.config import Settings

pytestmark = pytest.mark.unit

_BASE = dict(
    _env_file=None,
    app_database_url="postgresql://app:app@localhost/app",
    migration_database_url="postgresql://migrate:migrate@localhost/app",
    jwt_jwks_uri="http://authentication/.well-known/jwks.json",
)


def test_sender_type_defaults():
    settings = Settings(**_BASE)
    assert settings.message_sender_types == ["patient", "ai_agent", "clinician"]
    assert settings.intervention_sender_types == ["clinician"]


def test_sender_type_parses_comma_separated_lists():
    settings = Settings(
        **_BASE,
        message_sender_types="member,bot,human_agent",
        intervention_sender_types="human_agent",
        completion_user_sender_type="member",
        completion_assistant_sender_type="bot",
    )
    assert settings.message_sender_types == ["member", "bot", "human_agent"]
    assert settings.intervention_sender_types == ["human_agent"]


def test_sender_type_rejects_intervention_outside_allowed():
    with pytest.raises(ValueError, match="INTERVENTION_SENDER_TYPES"):
        Settings(
            **_BASE,
            message_sender_types=["patient", "ai_agent"],
            intervention_sender_types=["clinician"],
            completion_user_sender_type="patient",
            completion_assistant_sender_type="ai_agent",
        )
