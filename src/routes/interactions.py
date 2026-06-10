from __future__ import annotations

from authorization_in_the_middle.security import with_security
from flask import Blueprint, Response, jsonify, request
from werkzeug.exceptions import BadRequest

from src.bootstrap.config import settings
from src.bootstrap.request_telemetry import log_request_handled
from src.db.engine import SessionLocal
from src.services.interaction_service import create_interaction, list_interactions

bp = Blueprint("interactions", __name__, url_prefix="/api/v1/interactions")


def init_interaction_routes(app, cedar_evaluator):
    app.extensions["cedar_evaluator"] = cedar_evaluator
    app.register_blueprint(bp)


@bp.get("")
@with_security(action='Action::"message:list"', rate_limit=settings.message_read_rate_limit)
def get_interactions() -> Response:
    patient_uuid = request.args.get("patient_uuid")
    care_episode_uuid = request.args.get("care_episode_uuid")
    if not patient_uuid:
        raise BadRequest("patient_uuid is required")
    if not care_episode_uuid:
        raise BadRequest("care_episode_uuid is required")
    with SessionLocal() as db:
        response = jsonify({"items": list_interactions(db, patient_uuid, care_episode_uuid)})
    log_request_handled("interaction_list", 200)
    return response


@bp.post("")
@with_security(action='Action::"message:create"', rate_limit=settings.message_write_rate_limit)
def post_interaction() -> Response:
    payload = request.get_json(silent=True) or {}
    patient_uuid = str(payload.get("patient_uuid", "")).strip()
    care_episode_uuid = str(payload.get("care_episode_uuid", "")).strip()
    if not patient_uuid or not care_episode_uuid:
        raise BadRequest("patient_uuid and care_episode_uuid are required")
    with SessionLocal() as db:
        item = create_interaction(
            db,
            patient_uuid,
            care_episode_uuid,
            context=payload.get("context"),
        )
    log_request_handled("interaction_create", 201, care_episode_uuid=care_episode_uuid)
    return jsonify(item), 201
