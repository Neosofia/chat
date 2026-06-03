"""
Cedar principal and catalog resources for ``@with_security`` on message routes.

| Route | Action | Resource |
|-------|--------|----------|
| GET /api/v1/messages | message:read | chat::MessageCatalog |
| POST /api/v1/messages | message:create | chat::MessageCatalog |
| POST /api/v1/messages/last-activity | message:read | chat::MessageCatalog |
| POST /api/v1/messages/completions | message:create | chat::MessageCatalog |
"""
from __future__ import annotations

from typing import Any

from authorization_in_the_middle import extract_jwt_principal_entity
from authorization_in_the_middle.entities import build_entity_payload, entity_uid

NAMESPACE = "chat"
MESSAGE_CATALOG_ID = "message-catalog"


def resolve_principal() -> dict[str, Any]:
    return extract_jwt_principal_entity(NAMESPACE, default_type="User")


def build_message_catalog_entity() -> dict[str, Any]:
    return build_entity_payload(f"{NAMESPACE}::MessageCatalog", MESSAGE_CATALOG_ID, {})


def message_catalog_resource_uid() -> str:
    return entity_uid(f"{NAMESPACE}::MessageCatalog", MESSAGE_CATALOG_ID)


def message_catalog_entities() -> list[dict[str, Any]]:
    return [resolve_principal(), build_message_catalog_entity()]
