import uuid
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, g

from src.authorization import entities
from src.models.chat_interaction import ChatInteraction

pytestmark = pytest.mark.unit

PATIENT = "00000000-0000-7000-8000-000000000001"
OTHER = "00000000-0000-7000-8000-000000000099"
INTERACTION = "00000000-0000-7000-8000-000000000003"
TENANT = "00000000-0000-7000-8000-000000000010"


def _session_local_mock(db: MagicMock) -> MagicMock:
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=db)
    session.__exit__ = MagicMock(return_value=False)
    return session


def test_tenant_for_returns_principal_tenant_for_self(monkeypatch):
    monkeypatch.setattr(
        entities,
        "resolve_principal",
        lambda: {"attrs": {"uuid": PATIENT, "tenantId": TENANT}},
    )
    app = Flask(__name__)
    with app.test_request_context():
        assert entities._tenant_for(PATIENT) == TENANT


def test_tenant_for_reads_tenant_from_interaction_in_path(monkeypatch):
    monkeypatch.setattr(
        entities,
        "resolve_principal",
        lambda: {"attrs": {"uuid": PATIENT, "tenantId": TENANT}},
    )
    row = MagicMock()
    row.user_uuid = uuid.UUID(OTHER)
    row.context = {"tenant_uuid": TENANT}
    db = MagicMock()
    db.get.return_value = row
    monkeypatch.setattr(
        "src.db.engine.SessionLocal",
        lambda: _session_local_mock(db),
    )
    app = Flask(__name__)
    with app.test_request_context(
        f"/api/v1/users/{OTHER}/interactions/{INTERACTION}/messages",
    ):
        from flask import request

        request.view_args = {
            "user_uuid": OTHER,
            "chat_interaction_uuid": INTERACTION,
        }
        assert entities._tenant_for(OTHER) == TENANT
    db.get.assert_called_once_with(ChatInteraction, uuid.UUID(INTERACTION))


def test_tenant_for_reads_tenant_from_latest_interaction_for_list_routes(monkeypatch):
    monkeypatch.setattr(
        entities,
        "resolve_principal",
        lambda: {"attrs": {"uuid": PATIENT, "tenantId": TENANT}},
    )
    older = MagicMock(context=None)
    current = MagicMock(context={"tenant_uuid": TENANT})
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        current,
        older,
    ]
    monkeypatch.setattr(
        "src.db.engine.SessionLocal",
        lambda: _session_local_mock(db),
    )
    app = Flask(__name__)
    with app.test_request_context(f"/api/v1/users/{OTHER}/interactions"):
        assert entities._tenant_for(OTHER) == TENANT


def test_tenant_for_returns_empty_when_no_stored_tenant(monkeypatch):
    monkeypatch.setattr(
        entities,
        "resolve_principal",
        lambda: {"attrs": {"uuid": PATIENT, "tenantId": TENANT}},
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    monkeypatch.setattr(
        "src.db.engine.SessionLocal",
        lambda: _session_local_mock(db),
    )
    app = Flask(__name__)
    with app.test_request_context(f"/api/v1/users/{OTHER}/interactions"):
        assert entities._tenant_for(OTHER) == ""


def test_tenant_for_uses_trusted_care_episode_context_tenant(monkeypatch):
    monkeypatch.setattr(entities, "request_scoped_uuid", lambda _name: PATIENT)
    app = Flask(__name__)
    with app.test_request_context(
        "/api/v1/users/{}/interactions".format(PATIENT),
        method="POST",
        json={"context": {"tenant_uuid": TENANT, "procedure_name": "scope"}},
    ):
        g.jwt_claims = {
            "sub": "care-episode",
            "neosofia:token_type": "service",
        }
        assert entities._tenant_for(PATIENT) == TENANT


def test_build_chat_catalog_resource_scopes_user_and_tenant(monkeypatch):
    monkeypatch.setattr(entities, "request_scoped_uuid", lambda _name: PATIENT)
    monkeypatch.setattr(entities, "_tenant_for", lambda _uuid: TENANT)
    app = Flask(__name__)
    with app.test_request_context():
        resource = entities.build_chat_catalog_resource()

    assert resource["uid"]["__entity"]["type"] == "chat::ChatCatalog"
    assert resource["uid"]["__entity"]["id"] == entities.CHAT_CATALOG_ID
    assert resource["attrs"]["userUuid"] == PATIENT
    assert resource["attrs"]["tenantId"] == TENANT


def test_resolve_principal_builds_user_entity():
    app = Flask(__name__)
    with app.test_request_context():
        g.jwt_claims = {
            "sub": PATIENT,
            "neosofia:actors": ["patient"],
            "neosofia:tenant_uuid": TENANT,
            "neosofia:token_type": "human",
        }
        principal = entities.resolve_principal()

    assert principal["uid"]["__entity"]["type"] == "chat::User"
    assert principal["uid"]["__entity"]["id"] == PATIENT
    assert principal["attrs"]["uuid"] == PATIENT


def test_resolve_principal_builds_service_entity():
    app = Flask(__name__)
    with app.test_request_context():
        g.jwt_claims = {
            "sub": "care-episode",
            "neosofia:token_type": "service",
        }
        principal = entities.resolve_principal()

    assert principal["uid"]["__entity"]["type"] == "chat::Service"
    assert principal["uid"]["__entity"]["id"] == "care-episode"
    assert principal["attrs"]["serviceSlug"] == "care-episode"
    assert principal["attrs"]["tokenType"] == "service"
