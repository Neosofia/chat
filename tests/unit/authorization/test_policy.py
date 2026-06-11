from pathlib import Path

import pytest
from authorization_in_the_middle import CedarEvaluator, FilesystemPolicySetSource
from authorization_in_the_middle.entities import build_entity_payload, entity_uid

pytestmark = pytest.mark.unit

PATIENT = "00000000-0000-7000-8000-000000000001"
TENANT = "00000000-0000-7000-8000-000000000010"
CHAT_CATALOG = entity_uid("chat::ChatCatalog", "chat-catalog")


@pytest.fixture
def cedar():
    root = Path(__file__).resolve().parents[3]
    return CedarEvaluator(policy_source=FilesystemPolicySetSource(root / "policies"))


def _chat_catalog(**attrs):
    return build_entity_payload("chat::ChatCatalog", "chat-catalog", attrs)


def test_patient_own_messages(cedar):
    ok = cedar.is_authorized(
        entity_uid("chat::User", PATIENT),
        'Action::"message:list"',
        CHAT_CATALOG,
        [
            build_entity_payload("chat::User", PATIENT, {"uuid": PATIENT, "actors": ["patient"]}),
            _chat_catalog(userUuid=PATIENT),
        ],
        {},
    )
    assert ok is True


def test_patient_not_other_messages(cedar):
    ok = cedar.is_authorized(
        entity_uid("chat::User", PATIENT),
        'Action::"message:list"',
        CHAT_CATALOG,
        [
            build_entity_payload("chat::User", PATIENT, {"uuid": PATIENT, "actors": ["patient"]}),
            _chat_catalog(userUuid="00000000-0000-7000-8000-000000000099"),
        ],
        {},
    )
    assert ok is False


def test_clinician_same_tenant(cedar):
    ok = cedar.is_authorized(
        entity_uid("chat::User", "00000000-0000-7000-8000-000000000099"),
        'Action::"message:create"',
        CHAT_CATALOG,
        [
            build_entity_payload(
                "chat::User",
                "00000000-0000-7000-8000-000000000099",
                {"actors": ["clinician"], "tenantId": TENANT},
            ),
            _chat_catalog(tenantId=TENANT),
        ],
        {},
    )
    assert ok is True


def test_clinician_other_tenant(cedar):
    ok = cedar.is_authorized(
        entity_uid("chat::User", "00000000-0000-7000-8000-000000000099"),
        'Action::"message:create"',
        CHAT_CATALOG,
        [
            build_entity_payload(
                "chat::User",
                "00000000-0000-7000-8000-000000000099",
                {"actors": ["clinician"], "tenantId": TENANT},
            ),
            _chat_catalog(tenantId="00000000-0000-7000-8000-000000000011"),
        ],
        {},
    )
    assert ok is False


def test_patient_own_interactions(cedar):
    ok = cedar.is_authorized(
        entity_uid("chat::User", PATIENT),
        'Action::"interaction:list"',
        CHAT_CATALOG,
        [
            build_entity_payload("chat::User", PATIENT, {"uuid": PATIENT, "actors": ["patient"]}),
            _chat_catalog(userUuid=PATIENT),
        ],
        {},
    )
    assert ok is True
