from __future__ import annotations

from logenvelope.flask import log_request_handled as _log_request_handled

from src.models.chat_channel import CHAT_CHANNEL_LABELS


def log_request_handled(
    operation: str,
    status_code: int,
    *,
    source: dict | None = None,
    **extra,
) -> None:
    """Chat OR-001 telemetry — channel enrichment on top of logenvelope.flask."""
    enriched = source
    if source and source.get("channel") is not None and not source.get("channel_label"):
        enriched = {**source, "channel_label": CHAT_CHANNEL_LABELS[int(source["channel"])]}
    _log_request_handled(
        operation,
        status_code,
        source=enriched,
        copy_from_source=("channel", "channel_label") if enriched else (),
        **extra,
    )
