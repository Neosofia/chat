from flask import Blueprint, jsonify, Response

from src.bootstrap.config import settings
from src.bootstrap.extensions import limiter, talisman
from src.bootstrap.version import service_version
from src.services.inference_health import check_inference_health

bp = Blueprint("health", __name__)


def _health_body(status: str, detail: str | None = None) -> dict:
    body = {"status": status, "version": service_version()}
    if detail:
        body["detail"] = detail
    return body


@bp.route("/health", methods=["GET", "HEAD"])
@talisman(force_https=False)
@limiter.limit(settings.health_rate_limit)
def health() -> Response:
    llm_status, detail = check_inference_health()
    if llm_status == "ok":
        return jsonify(_health_body("ok")), 200
    return jsonify(_health_body("degraded", detail=detail)), 200
