from __future__ import annotations

from flask import Blueprint, Response, jsonify, request
from werkzeug.exceptions import BadRequest

from src.db.engine import SessionLocal
from src.services.message_service import create_message, list_last_message_times, list_messages

bp = Blueprint("messages", __name__, url_prefix="/api/v1/messages")


def init_message_routes(app, cedar_evaluator):
    app.extensions["cedar_evaluator"] = cedar_evaluator
    app.register_blueprint(bp)


@bp.get("")
def get_messages() -> Response:
    patient_uuid = request.args.get("patient_uuid")
    if not patient_uuid:
        raise BadRequest("patient_uuid is required")
    care_episode_uuid = request.args.get("care_episode_uuid")
    if not care_episode_uuid:
        raise BadRequest("care_episode_uuid is required")
    limit = max(1, min(int(request.args.get("limit", "200")), 500))
    with SessionLocal() as db:
        return jsonify({"items": list_messages(db, patient_uuid, care_episode_uuid, limit)})


@bp.post("/last-activity")
def post_last_activity() -> Response:
    payload = request.get_json(silent=True) or {}
    items = payload.get("items")
    if not isinstance(items, list):
        raise BadRequest("items must be a list")
    with SessionLocal() as db:
        return jsonify({"items": list_last_message_times(db, items)})


@bp.post("")
def post_message() -> Response:
    payload = request.get_json(silent=True) or {}
    with SessionLocal() as db:
        item = create_message(db, payload)
    return jsonify(item), 201


@bp.post("/completions")
def create_completion() -> Response:
    payload = request.get_json(silent=True) or {}
    messages = payload.get("messages") or []
    if not isinstance(messages, list) or not messages:
        raise BadRequest("messages is required")
    user_message = str(messages[-1].get("content", "")).strip()
    response = (
        "Thanks - I logged your update. Continue monitoring and contact your care team "
        "immediately if symptoms worsen."
    )
    if "pain" in user_message.lower():
        response = (
            "I hear that your pain is getting worse. Please seek urgent in-person care now, "
            "and I will alert your care team in parallel."
        )
    return jsonify({"message": response})
