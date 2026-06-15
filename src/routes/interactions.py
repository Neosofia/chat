from __future__ import annotations

import uuid as _uuid

from authorization_in_the_middle.security import with_security
from flask import Blueprint, Response, jsonify, request
from werkzeug.exceptions import BadRequest

from src.authorization.entities import is_care_episode_service_token
from src.bootstrap.config import settings
from src.bootstrap.request_telemetry import log_request_handled
from src.db.engine import SessionLocal
from src.services.completion_service import complete_user_turn, start_chat_session
from src.services.context_service import normalize_interaction_context
from src.services.interaction_service import create_interaction, list_interactions, require_interaction_for_user
from src.services.message_service import (
    create_message,
    list_last_message_times,
    list_messages,
    list_tenant_last_message_times,
)

bp = Blueprint("user_interactions", __name__, url_prefix="/api/v1/users")
tenant_bp = Blueprint("tenant_chat", __name__, url_prefix="/api/v1/tenants")


def _parse_tenant_uuid(tenant_uuid: str) -> str | None:
    try:
        return str(_uuid.UUID(str(tenant_uuid)))
    except ValueError:
        return None


def init_interaction_routes(app, cedar_evaluator):
    app.extensions["cedar_evaluator"] = cedar_evaluator
    app.register_blueprint(bp)
    app.register_blueprint(tenant_bp)


def _interaction_context_from_payload(payload: dict):
    if "context" not in payload or payload.get("context") is None:
        raise BadRequest("interaction context is required")
    if not is_care_episode_service_token():
        raise BadRequest("interaction context may only be supplied by care episode service")
    context = normalize_interaction_context(payload["context"])
    if context is None:
        raise BadRequest("interaction context is required")
    return context


@tenant_bp.get("/<tenant_uuid>/last-activity")
@with_security(
    action='Action::"message:list"',
    rate_limit=settings.message_read_rate_limit,
    resource_type="InteractionCatalog",
)
def get_tenant_last_activity(tenant_uuid: str) -> Response:
    parsed_tenant = _parse_tenant_uuid(tenant_uuid)
    if parsed_tenant is None:
        return jsonify({"error": "invalid_request", "message": "tenant_uuid must be a UUID"}), 400
    with SessionLocal() as db:
        items = list_tenant_last_message_times(db, parsed_tenant)
    log_request_handled("tenant_message_last_activity", 200)
    return jsonify({"tenant_uuid": parsed_tenant, "items": items})


@bp.get("/<user_uuid>/last-activity")
@with_security(
    action='Action::"message:list"',
    rate_limit=settings.message_read_rate_limit,
    resource_type="InteractionCatalog",
)
def get_last_activity(user_uuid: str) -> Response:
    with SessionLocal() as db:
        item = list_last_message_times(db, [{"user_uuid": user_uuid}])[0]
    log_request_handled("message_last_activity", 200)
    return jsonify(item)


@bp.get("/<user_uuid>/interactions")
@with_security(rate_limit=settings.message_read_rate_limit)
def get_interactions(user_uuid: str) -> Response:
    with SessionLocal() as db:
        response = jsonify({"items": list_interactions(db, user_uuid)})
    log_request_handled("interaction_list", 200)
    return response


@bp.post("/<user_uuid>/interactions")
@with_security(rate_limit=settings.message_write_rate_limit)
def post_interaction(user_uuid: str) -> Response:
    payload = request.get_json(silent=True) or {}
    with SessionLocal() as db:
        item = create_interaction(
            db,
            user_uuid,
            context=_interaction_context_from_payload(payload),
        )
    log_request_handled("interaction_create", 201)
    return jsonify(item), 201


@bp.get("/<user_uuid>/interactions/<chat_interaction_uuid>/messages")
@with_security(rate_limit=settings.message_read_rate_limit)
def get_messages(user_uuid: str, chat_interaction_uuid: str) -> Response:
    limit = max(1, min(int(request.args.get("limit", "200")), 500))
    with SessionLocal() as db:
        require_interaction_for_user(db, user_uuid, chat_interaction_uuid)
        response = jsonify({"items": list_messages(db, chat_interaction_uuid, limit)})
    log_request_handled("message_list", 200)
    return response


@bp.post("/<user_uuid>/interactions/<chat_interaction_uuid>/messages")
@with_security(rate_limit=settings.message_write_rate_limit)
def post_message(user_uuid: str, chat_interaction_uuid: str) -> Response:
    payload = request.get_json(silent=True) or {}
    payload = {**payload, "chat_interaction_uuid": chat_interaction_uuid}
    with SessionLocal() as db:
        require_interaction_for_user(db, user_uuid, chat_interaction_uuid)
        item = create_message(db, payload)
    log_request_handled("message_create", 201, source=item)
    return jsonify(item), 201


@bp.post("/<user_uuid>/interactions/<chat_interaction_uuid>/completions")
@with_security(
    action='Action::"message:create"',
    rate_limit=settings.message_write_rate_limit,
)
def create_completion(user_uuid: str, chat_interaction_uuid: str) -> Response:
    payload = request.get_json(silent=True) or {}
    payload = {**payload, "chat_interaction_uuid": chat_interaction_uuid}
    with SessionLocal() as db:
        require_interaction_for_user(db, user_uuid, chat_interaction_uuid)
        if payload.get("session_start"):
            result = start_chat_session(db, payload)
            operation = "completion_session_start"
        else:
            result = complete_user_turn(db, payload)
            operation = "completion_user_turn"
    log_request_handled(
        operation,
        200,
        source=result.get("user_message") or result.get("assistant_message"),
        session_start=bool(payload.get("session_start")),
        intervention=bool(result.get("intervention")),
    )
    return jsonify(result)
