"""Application settings, loaded once from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Empty defaults so the app imports without credentials; startup checks them.
    database_url: str = ""

    # Signs our access tokens. Generate with: openssl rand -hex 32
    jwt_secret: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://127.0.0.1:8000/auth/google/callback"

    # Where the browser is sent after a successful Google sign-in.
    frontend_url: str = "http://localhost:3000"

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def require_runtime_settings(settings: Settings) -> None:
    """Fail startup on missing configuration.

    JWT_SECRET especially: PyJWT will happily sign with an empty key, so without
    this the app would register users and issue tokens that no request can then
    verify.
    """
    missing = [
        name.upper()
        for name in ("database_url", "jwt_secret")
        if not getattr(settings, name)
    ]
    if missing:
        raise RuntimeError(
            f"Missing required settings: {', '.join(missing)}. "
            "Copy api/.env.example to api/.env, or set them in the host's environment."
        )
