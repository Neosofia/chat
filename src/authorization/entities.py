"""Cedar principal and scoped catalog resources for chat routes."""
from __future__ import annotations

import uuid
from typing import Any

from authorization_in_the_middle import request_scoped_uuid
from authorization_in_the_middle.entities import build_entity_payload
from authorization_in_the_middle.flask_identity import jwt_claim_principal_attributes
from flask import g, request
from werkzeug.exceptions import BadRequest

from src.bootstrap.config import settings

NAMESPACE = "chat"
CHAT_CATALOG_ID = "chat-catalog"
CARE_EPISODE_SERVICE_SLUG = "care-episode"


def _claims() -> dict[str, Any]:
    return getattr(g, "jwt_claims", {}) or {}


def _jwt_claim(name: str) -> str:
    return f"{settings.jwt_claim_namespace}:{name}"


def build_service_principal_entity(service_slug: str, claims: dict[str, Any]) -> dict[str, Any]:
    return build_entity_payload(
        f"{NAMESPACE}::Service",
        service_slug,
        {
            "serviceSlug": service_slug,
            "tokenType": str(claims.get(_jwt_claim("token_type")) or claims.get("token_type") or ""),
        },
    )


def resolve_principal() -> dict[str, Any]:
    claims = _claims()
    if not claims:
        raise BadRequest("No JWT claims available on request context")
    sub, ptype, attributes = jwt_claim_principal_attributes(claims, default_type="User")
    if attributes.get("token_type") == "service":
        return build_service_principal_entity(sub, claims)
    return build_entity_payload(f"{NAMESPACE}::{ptype}", sub, attributes)


def is_care_episode_service_token() -> bool:
    claims = _claims()
    if not claims:
        return False
    sub, _, attrs = jwt_claim_principal_attributes(claims, default_type="User")
    return attrs.get("token_type") == "service" and sub == CARE_EPISODE_SERVICE_SLUG


def _trusted_care_episode_context_tenant() -> str:
    """Organisation from CE-supplied context (same trust boundary as episode context)."""
    if not is_care_episode_service_token():
        return ""
    payload = request.get_json(silent=True) or {}
    context = payload.get("context")
    if not isinstance(context, dict):
        return ""
    return _tenant_uuid_from_context(context)


def _tenant_uuid_from_context(context: dict | None) -> str:
    if not isinstance(context, dict):
        return ""
    return str(context.get("tenant_uuid") or "").strip()


def _tenant_from_stored_interaction_context(user_uuid: str) -> str:
    """Resolve tenant from persisted interaction context (CE-authored at create)."""
    from sqlalchemy.exc import SQLAlchemyError

    from src.db.engine import SessionLocal
    from src.models.chat_interaction import ChatInteraction

    try:
        user_id = uuid.UUID(str(user_uuid))
    except ValueError:
        return ""

    view_args = request.view_args or {}
    interaction_uuid_raw = str(view_args.get("chat_interaction_uuid") or "").strip()

    try:
        with SessionLocal() as db:
            if interaction_uuid_raw:
                try:
                    interaction_id = uuid.UUID(interaction_uuid_raw)
                except ValueError:
                    return ""
                row = db.get(ChatInteraction, interaction_id)
                if row is None or row.user_uuid != user_id:
                    return ""
                return _tenant_uuid_from_context(row.context)

            rows = (
                db.query(ChatInteraction)
                .filter(ChatInteraction.user_uuid == user_id)
                .order_by(ChatInteraction.changed_at.desc())
                .all()
            )
            for row in rows:
                if tenant := _tenant_uuid_from_context(row.context):
                    return tenant
    except SQLAlchemyError:
        return ""
    return ""


def _tenant_for(user_uuid: str) -> str:
    """Resolve tenant for Cedar resource.tenantId (clinician permit only)."""
    if trusted_tenant := _trusted_care_episode_context_tenant():
        return trusted_tenant
    principal = resolve_principal()
    if user_uuid == str(principal["attrs"].get("uuid", "")):
        return str(principal["attrs"].get("tenantId") or "").strip()
    return _tenant_from_stored_interaction_context(user_uuid)


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
