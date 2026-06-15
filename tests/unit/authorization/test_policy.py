from pathlib import Path

import pytest
from authorization_in_the_middle import CedarEvaluator, FilesystemPolicySetSource
from authorization_in_the_middle.entities import build_entity_payload, entity_uid

pytestmark = pytest.mark.unit

PATIENT = "00000000-0000-7000-8000-000000000001"
INTERACTION = "00000000-0000-7000-8000-000000000003"
TENANT = "00000000-0000-7000-8000-000000000010"
MESSAGE_CATALOG = entity_uid("chat::MessageCatalog", INTERACTION)
INTERACTION_CATALOG = entity_uid("chat::InteractionCatalog", PATIENT)


@pytest.fixture
def cedar():
    root = Path(__file__).resolve().parents[3]
    return CedarEvaluator(policy_source=FilesystemPolicySetSource(root / "policies"))


def _message_catalog(**attrs):
    return build_entity_payload("chat::MessageCatalog", INTERACTION, attrs)


def _interaction_catalog(**attrs):
    return build_entity_payload("chat::InteractionCatalog", PATIENT, attrs)


def test_patient_own_messages(cedar):
    ok = cedar.is_authorized(
        entity_uid("chat::User", PATIENT),
        'Action::"message:list"',
        MESSAGE_CATALOG,
        [
            build_entity_payload("chat::User", PATIENT, {"uuid": PATIENT, "actors": ["patient"]}),
            _message_catalog(userUuid=PATIENT, interactionUuid=INTERACTION),
        ],
        {},
    )
    assert ok is True


def test_patient_not_other_messages(cedar):
    ok = cedar.is_authorized(
        entity_uid("chat::User", PATIENT),
        'Action::"message:list"',
        MESSAGE_CATALOG,
        [
            build_entity_payload("chat::User", PATIENT, {"uuid": PATIENT, "actors": ["patient"]}),
            _message_catalog(userUuid="00000000-0000-7000-8000-000000000099", interactionUuid=INTERACTION),
        ],
        {},
    )
    assert ok is False


def test_clinician_same_tenant_interactions(cedar):
    ok = cedar.is_authorized(
        entity_uid("chat::User", "00000000-0000-7000-8000-000000000099"),
        'Action::"interaction:list"',
        INTERACTION_CATALOG,
        [
            build_entity_payload(
                "chat::User",
                "00000000-0000-7000-8000-000000000099",
                {"actors": ["clinician"], "tenantId": TENANT},
            ),
            _interaction_catalog(userUuid=PATIENT, tenantId=TENANT),
        ],
        {},
    )
    assert ok is True


def test_clinician_same_tenant_messages(cedar):
    ok = cedar.is_authorized(
        entity_uid("chat::User", "00000000-0000-7000-8000-000000000099"),
        'Action::"message:create"',
        MESSAGE_CATALOG,
        [
            build_entity_payload(
                "chat::User",
                "00000000-0000-7000-8000-000000000099",
                {"actors": ["clinician"], "tenantId": TENANT},
            ),
            _message_catalog(tenantId=TENANT, interactionUuid=INTERACTION),
        ],
        {},
    )
    assert ok is True


def test_clinician_other_tenant_messages(cedar):
    ok = cedar.is_authorized(
        entity_uid("chat::User", "00000000-0000-7000-8000-000000000099"),
        'Action::"message:create"',
        MESSAGE_CATALOG,
        [
            build_entity_payload(
                "chat::User",
                "00000000-0000-7000-8000-000000000099",
                {"actors": ["clinician"], "tenantId": TENANT},
            ),
            _message_catalog(tenantId="00000000-0000-7000-8000-000000000011", interactionUuid=INTERACTION),
        ],
        {},
    )
    assert ok is False


def test_patient_own_interactions(cedar):
    ok = cedar.is_authorized(
        entity_uid("chat::User", PATIENT),
        'Action::"interaction:list"',
        INTERACTION_CATALOG,
        [
            build_entity_payload("chat::User", PATIENT, {"uuid": PATIENT, "actors": ["patient"]}),
            _interaction_catalog(userUuid=PATIENT),
        ],
        {},
    )
    assert ok is True


def test_patient_last_activity_on_interaction_catalog(cedar):
    ok = cedar.is_authorized(
        entity_uid("chat::User", PATIENT),
        'Action::"message:list"',
        INTERACTION_CATALOG,
        [
            build_entity_payload("chat::User", PATIENT, {"uuid": PATIENT, "actors": ["patient"]}),
            _interaction_catalog(userUuid=PATIENT),
        ],
        {},
    )
    assert ok is True
