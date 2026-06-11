"""Cedar principal and scoped catalog resources for chat routes."""
from __future__ import annotations

from typing import Any

import httpx
from authorization_in_the_middle import extract_jwt_principal_entity, request_scoped_uuid
from authorization_in_the_middle.entities import build_entity_payload
from flask import request

from src.bootstrap.config import settings

NAMESPACE = "chat"
CHAT_CATALOG_ID = "chat-catalog"


def resolve_principal() -> dict[str, Any]:
    return extract_jwt_principal_entity(NAMESPACE, default_type="User")


def _user_service_request_headers() -> dict[str, str]:
    """Passthrough auth headers for User registry lookups (same session as the chat request)."""
    headers: dict[str, str] = {}
    auth = request.headers.get("Authorization")
    if auth:
        headers["Authorization"] = auth
    active_actor = request.headers.get("X-Active-Actor", "").strip()
    if active_actor:
        headers["X-Active-Actor"] = active_actor
    return headers


def _tenant_for(user_uuid: str) -> str:
    """Resolve tenant for Cedar resource.tenantId (clinician permit only)."""
    principal = resolve_principal()
    if user_uuid == str(principal["attrs"].get("uuid", "")):
        return str(principal["attrs"].get("tenantId") or "").strip()
    base = settings.user_service_base_url.strip()
    headers = _user_service_request_headers()
    if not base or "Authorization" not in headers:
        return ""
    try:
        response = httpx.get(
            f"{base.rstrip('/')}/api/v1/users/{user_uuid}",
            headers=headers,
            timeout=5.0,
        )
        if response.status_code == 200:
            return str(response.json().get("tenant_uuid") or "").strip()
    except httpx.HTTPError:
        pass
    return ""


def _user_scoped_catalog_attrs() -> dict[str, str]:
    attrs: dict[str, str] = {}
    if user_uuid := request_scoped_uuid("user_uuid"):
        attrs["userUuid"] = user_uuid
        if tenant := _tenant_for(user_uuid):
            attrs["tenantId"] = tenant
    return attrs


def build_chat_catalog_resource() -> dict[str, Any]:
    """Cedar resource for interaction and message list/create under a user."""
    return build_entity_payload(
        f"{NAMESPACE}::ChatCatalog",
        CHAT_CATALOG_ID,
        _user_scoped_catalog_attrs(),
    )
