import base64
from pathlib import Path
from typing import Annotated

from pydantic import Field, PrivateAttr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url


def _validate_database_urls(migration_database_url: str, app_database_url: str) -> None:
    migration = make_url(migration_database_url)
    app = make_url(app_database_url)
    if migration.username == app.username:
        raise ValueError(
            "MIGRATION_DATABASE_URL and APP_DATABASE_URL must use different users; "
            f"both are {migration.username!r}"
        )


_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def _read_prompt_text(path: Path, label: str) -> str:
    resolved = path.expanduser()
    if not resolved.is_file():
        raise ValueError(f"{label}: file not found: {resolved}")
    text = resolved.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{label} must be non-empty")
    return text


DEFAULT_AGENT_PRIMING_PROMPT = _read_prompt_text(_PROMPTS_DIR / "agent-priming-prompt.txt", "agent-priming-prompt.txt")
DEFAULT_AGENT_INSTRUCTIONS = _read_prompt_text(_PROMPTS_DIR / "agent-instructions.txt", "agent-instructions.txt")


def _validate_sender_taxonomy(settings: "Settings") -> None:
    allowed = frozenset(settings.message_sender_types)
    if not allowed:
        raise ValueError("MESSAGE_SENDER_TYPES must include at least one sender type")
    unknown = set(settings.intervention_sender_types) - allowed
    if unknown:
        raise ValueError(
            "INTERVENTION_SENDER_TYPES must be a subset of MESSAGE_SENDER_TYPES; "
            f"unknown: {sorted(unknown)}"
        )
    if settings.completion_user_sender_type not in allowed:
        raise ValueError("COMPLETION_USER_SENDER_TYPE must be one of MESSAGE_SENDER_TYPES")
    if settings.completion_assistant_sender_type not in allowed:
        raise ValueError("COMPLETION_ASSISTANT_SENDER_TYPE must be one of MESSAGE_SENDER_TYPES")
    if settings.completion_user_sender_type == settings.completion_assistant_sender_type:
        raise ValueError(
            "COMPLETION_USER_SENDER_TYPE and COMPLETION_ASSISTANT_SENDER_TYPE must differ"
        )


class Settings(BaseSettings):
    app_database_url: str
    migration_database_url: str

    service_name: str = "chat"
    env: str = "production"
    log_level: str = "info"
    port: int = 8001
    trusted_proxy_hops: int = 1
    max_content_length: int = 16_384

    authorization_policies_dir: Path = Path("policies")
    authorization_policy_cache_ttl: int = 60

    jwt_public_key: str | None = None
    jwt_jwks_uri: str | None = None
    jwt_audience: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["chat"])
    jwt_claim_namespace: str = "neosofia"

    rate_limit_storage_uri: str = "memory://"
    health_rate_limit: str = "600 per minute"
    meta_enums_rate_limit: str = "600 per minute"
    message_write_rate_limit: str = "300 per minute"
    message_read_rate_limit: str = "300 per minute"

    web_concurrency: int = 2
    gunicorn_threads: int = 2
    gunicorn_timeout: int = 30
    frontend_url: str = "http://localhost:5173"
    gunicorn_keepalive: int = 5

    inference_completions_url: str = ""
    inference_api_key: str | None = None
    inference_model: str = ""
    inference_temperature: float = 1.0
    agent_priming_prompt_file: Path | None = None
    agent_instructions_file: Path | None = None
    _agent_priming_prompt: str = PrivateAttr()
    _agent_instructions: str = PrivateAttr()
    user_service_base_url: str = ""

    message_sender_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["patient", "ai_agent", "clinician"]
    )
    intervention_sender_types: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["clinician"])
    completion_user_sender_type: str = "patient"
    completion_assistant_sender_type: str = "ai_agent"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    @field_validator(
        "message_sender_types",
        "intervention_sender_types",
        "jwt_audience",
        mode="before",
    )
    @classmethod
    def _csv_list(cls, value: object, info: ValidationInfo) -> list[str] | None:
        if value is None:
            return None if info.field_name == "jwt_audience" else []
        if isinstance(value, str):
            items = [part.strip() for part in value.split(",") if part.strip()]
        elif isinstance(value, (list, tuple)):
            items = [str(part).strip() for part in value if str(part).strip()]
        else:
            raise ValueError(f"{info.field_name} must be a comma-separated string or list")
        if info.field_name != "jwt_audience":
            items = [part.lower() for part in items]
        return items

    @field_validator("agent_priming_prompt_file", "agent_instructions_file", mode="before")
    @classmethod
    def _normalize_optional_prompt_file(cls, value: object) -> Path | None:
        if value is None:
            return None
        text = str(value).strip()
        return None if not text else Path(text)

    @property
    def agent_priming_prompt(self) -> str:
        return self._agent_priming_prompt

    @property
    def agent_instructions(self) -> str:
        return self._agent_instructions

    @field_validator("completion_user_sender_type", "completion_assistant_sender_type", mode="before")
    @classmethod
    def _lower_sender_type(cls, value: object) -> str:
        text = str(value).strip().lower()
        if not text:
            raise ValueError("sender type must be non-empty")
        return text

    @field_validator(
        "port",
        "trusted_proxy_hops",
        "max_content_length",
        "authorization_policy_cache_ttl",
        "web_concurrency",
        "gunicorn_threads",
        "gunicorn_timeout",
        "gunicorn_keepalive",
        mode="before",
    )
    @classmethod
    def _normalize_optional_int_env(cls, value: object, info: ValidationInfo) -> object:
        env_var = info.field_name.upper()
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError as exc:
                raise ValueError(f"{env_var} must be an integer, got {value!r}") from exc
        return value

    @field_validator("app_database_url", "migration_database_url", mode="before")
    @classmethod
    def _require_non_empty_database_url(cls, value: object, info: ValidationInfo) -> str:
        env_var = info.field_name.upper()
        if value is None or not str(value).strip():
            raise ValueError(f"{env_var} must be set")
        return str(value).strip()

    def model_post_init(self, __context: object) -> None:
        _validate_database_urls(self.migration_database_url, self.app_database_url)
        _validate_sender_taxonomy(self)

        if not self.jwt_public_key and not self.jwt_jwks_uri:
            raise ValueError("JWT_PUBLIC_KEY or JWT_JWKS_URI must be configured for token validation")

        if self.jwt_public_key and self.jwt_public_key != "DEFAULT_PUBLIC_KEY":
            try:
                decoded = base64.b64decode(self.jwt_public_key).decode("utf-8")
                object.__setattr__(self, "jwt_public_key", decoded)
            except Exception as e:
                if "BEGIN PUBLIC KEY" not in self.jwt_public_key:
                    raise ValueError(f"Failed to decode base64 jwt_public_key: {e}") from e

        priming = DEFAULT_AGENT_PRIMING_PROMPT
        instructions = DEFAULT_AGENT_INSTRUCTIONS
        if self.agent_priming_prompt_file is not None:
            priming = _read_prompt_text(self.agent_priming_prompt_file, "AGENT_PRIMING_PROMPT_FILE")
        if self.agent_instructions_file is not None:
            instructions = _read_prompt_text(self.agent_instructions_file, "AGENT_INSTRUCTIONS_FILE")
        object.__setattr__(self, "_agent_priming_prompt", priming)
        object.__setattr__(self, "_agent_instructions", instructions)


settings = Settings()  # type: ignore[call-arg]


def inference_configured() -> bool:
    return bool(
        settings.inference_api_key
        and settings.inference_completions_url
        and str(settings.inference_model).strip()
    )
