from unittest.mock import MagicMock, patch

import httpx
import pytest
from flask import Flask, g

from src.authorization import entities

pytestmark = pytest.mark.unit

PATIENT = "00000000-0000-7000-8000-000000000001"
OTHER = "00000000-0000-7000-8000-000000000099"
TENANT = "00000000-0000-7000-8000-000000000010"


def test_tenant_for_returns_principal_tenant_for_self(monkeypatch):
    monkeypatch.setattr(
        entities,
        "resolve_principal",
        lambda: {"attrs": {"uuid": PATIENT, "tenantId": TENANT}},
    )
    app = Flask(__name__)
    with app.test_request_context():
        assert entities._tenant_for(PATIENT) == TENANT


def test_tenant_for_returns_empty_without_user_service(monkeypatch):
    monkeypatch.setattr(
        entities,
        "resolve_principal",
        lambda: {"attrs": {"uuid": PATIENT, "tenantId": TENANT}},
    )
    monkeypatch.setattr(entities.settings, "user_service_base_url", "")
    app = Flask(__name__)
    with app.test_request_context(headers={"Authorization": "Bearer token"}):
        assert entities._tenant_for(OTHER) == ""


def test_tenant_for_looks_up_user_service(monkeypatch):
    monkeypatch.setattr(
        entities,
        "resolve_principal",
        lambda: {"attrs": {"uuid": PATIENT, "tenantId": TENANT}},
    )
    monkeypatch.setattr(entities.settings, "user_service_base_url", "http://user:8018")
    response = MagicMock(status_code=200)
    response.json.return_value = {"tenant_uuid": TENANT}
    app = Flask(__name__)
    with app.test_request_context(
        headers={"Authorization": "Bearer token", "X-Active-Actor": "clinician"},
    ):
        with patch("src.authorization.entities.httpx.get", return_value=response) as get:
            assert entities._tenant_for(OTHER) == TENANT
            get.assert_called_once_with(
                f"http://user:8018/api/v1/users/{OTHER}",
                headers={"Authorization": "Bearer token", "X-Active-Actor": "clinician"},
                timeout=5.0,
            )


def test_tenant_for_omits_active_actor_when_unset(monkeypatch):
    monkeypatch.setattr(
        entities,
        "resolve_principal",
        lambda: {"attrs": {"uuid": PATIENT, "tenantId": TENANT}},
    )
    monkeypatch.setattr(entities.settings, "user_service_base_url", "http://user:8018")
    response = MagicMock(status_code=200)
    response.json.return_value = {"tenant_uuid": TENANT}
    app = Flask(__name__)
    with app.test_request_context(headers={"Authorization": "Bearer token"}):
        with patch("src.authorization.entities.httpx.get", return_value=response) as get:
            assert entities._tenant_for(OTHER) == TENANT
            get.assert_called_once_with(
                f"http://user:8018/api/v1/users/{OTHER}",
                headers={"Authorization": "Bearer token"},
                timeout=5.0,
            )


def test_tenant_for_swallows_user_service_errors(monkeypatch):
    monkeypatch.setattr(
        entities,
        "resolve_principal",
        lambda: {"attrs": {"uuid": PATIENT, "tenantId": TENANT}},
    )
    monkeypatch.setattr(entities.settings, "user_service_base_url", "http://user:8018")
    app = Flask(__name__)
    with app.test_request_context(headers={"Authorization": "Bearer token"}):
        with patch(
            "src.authorization.entities.httpx.get",
            side_effect=httpx.HTTPError("down"),
        ):
            assert entities._tenant_for(OTHER) == ""


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


def test_resolve_principal_delegates_to_sdk(monkeypatch):
    sentinel = {"uid": {"__entity": {"type": "chat::User", "id": PATIENT}}, "attrs": {}}
    monkeypatch.setattr(entities, "extract_jwt_principal_entity", lambda ns, **kw: sentinel)
    app = Flask(__name__)
    with app.test_request_context():
        g.jwt_claims = {"sub": PATIENT}
        assert entities.resolve_principal() is sentinel
