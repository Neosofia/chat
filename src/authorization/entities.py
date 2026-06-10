"""Cedar principal and entity builders for SDK REST inference."""
from __future__ import annotations

from typing import Any

from authorization_in_the_middle import extract_jwt_principal_entity
from authorization_in_the_middle.entities import build_entity_payload

NAMESPACE = "chat"
MESSAGE_CATALOG_ID = "message-catalog"


def resolve_principal() -> dict[str, Any]:
    return extract_jwt_principal_entity(NAMESPACE, default_type="User")


def build_message_catalog_entity() -> dict[str, Any]:
    return build_entity_payload(f"{NAMESPACE}::MessageCatalog", MESSAGE_CATALOG_ID, {})
