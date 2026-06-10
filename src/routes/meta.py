from __future__ import annotations

from flask import Blueprint, Response, jsonify

from src.bootstrap.config import settings
from src.bootstrap.extensions import limiter
from src.models.enum_registry import build_enum_registry

bp = Blueprint("meta", __name__, url_prefix="/meta")


def init_meta_routes(app):
    app.register_blueprint(bp)


@bp.get("/enums")
@limiter.limit(settings.meta_enums_rate_limit)
def get_enums() -> Response:
    return jsonify(build_enum_registry())
