from __future__ import annotations

from authorization_in_the_middle.security import with_security
from flask import Blueprint, Response, jsonify, request
from werkzeug.exceptions import BadRequest

from src.authorization.entities import message_catalog_entities, message_catalog_resource_uid
from src.bootstrap.capabilities import Capabilities
from src.bootstrap.config import settings
from src.db.engine import SessionLocal
from src.services.completion_service import complete_patient_turn, start_chat_session
from src.services.message_service import create_message, list_last_message_times, list_messages

bp = Blueprint("messages", __name__, url_prefix="/api/v1/messages")


def init_message_routes(app, cedar_evaluator):
    app.extensions["cedar_evaluator"] = cedar_evaluator
    app.register_blueprint(bp)


@bp.get("")
@with_security(
    action=Capabilities.MESSAGE_READ,
    resource_fn=message_catalog_resource_uid,
    entities_fn=message_catalog_entities,
    rate_limit=settings.message_read_rate_limit,
)
def get_messages() -> Response:
    chat_interaction_uuid = request.args.get("chat_interaction_uuid")
    if not chat_interaction_uuid:
        raise BadRequest("chat_interaction_uuid is required")
    limit = max(1, min(int(request.args.get("limit", "200")), 500))
    with SessionLocal() as db:
        return jsonify({"items": list_messages(db, chat_interaction_uuid, limit)})


@bp.post("/last-activity")
@with_security(
    action=Capabilities.MESSAGE_READ,
    resource_fn=message_catalog_resource_uid,
    entities_fn=message_catalog_entities,
    rate_limit=settings.message_read_rate_limit,
)
def post_last_activity() -> Response:
    payload = request.get_json(silent=True) or {}
    items = payload.get("items")
    if not isinstance(items, list):
        raise BadRequest("items must be a list")
    with SessionLocal() as db:
        return jsonify({"items": list_last_message_times(db, items)})


@bp.post("")
@with_security(
    action=Capabilities.MESSAGE_CREATE,
    rate_limit=settings.message_write_rate_limit,
)
def post_message() -> Response:
    payload = request.get_json(silent=True) or {}
    with SessionLocal() as db:
        item = create_message(db, payload)
    return jsonify(item), 201


@bp.post("/completions")
@with_security(
    action=Capabilities.MESSAGE_CREATE,
    rate_limit=settings.message_write_rate_limit,
)
def create_completion() -> Response:
    payload = request.get_json(silent=True) or {}
    with SessionLocal() as db:
        if payload.get("session_start"):
            result = start_chat_session(db, payload)
        else:
            result = complete_patient_turn(db, payload)
    return jsonify(result)
