import pytest
from werkzeug.exceptions import BadRequest

from src.services.context_service import normalize_interaction_context

pytestmark = pytest.mark.unit


def test_normalize_interaction_context_returns_none_for_missing_value():
    assert normalize_interaction_context(None) is None
    assert normalize_interaction_context({}) is None


def test_normalize_interaction_context_accepts_scalar_fields():
    result = normalize_interaction_context(
        {
            "patient_first_name": " Alex ",
            "days_post_op": 4,
            "active": True,
            "empty": "",
            "unset": None,
        },
    )
    assert result == {
        "patient_first_name": "Alex",
        "days_post_op": 4,
        "active": True,
        "unset": None,
    }


def test_normalize_interaction_context_rejects_non_object():
    with pytest.raises(BadRequest, match="JSON object"):
        normalize_interaction_context(["bad"])


def test_normalize_interaction_context_rejects_nested_values():
    with pytest.raises(BadRequest, match="strings, numbers, booleans"):
        normalize_interaction_context({"nested": {"bad": True}})


def test_normalize_interaction_context_rejects_oversized_payload():
    with pytest.raises(BadRequest, match="maximum size"):
        normalize_interaction_context({"blob": "x" * 9000})
