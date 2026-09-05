"""Application settings, loaded once from the environment.

Credentials never live in source. `.env` is gitignored; in production these come
from the hosting provider's environment settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Supabase Postgres connection string. Empty by default so the app can be
    # imported (and tested) without a database; startup fails loudly if unset.
    database_url: str = ""

    # Supabase project URL, e.g. https://<ref>.supabase.co
    #
    # Supabase signs access tokens with ES256 asymmetric keys and publishes the
    # matching public keys at a well-known endpoint, so the API verifies
    # signatures against that endpoint rather than holding a shared secret.
    # This URL must be configured rather than read from the token's own `iss`
    # claim — trusting the token to name its own key source would let anyone
    # mint tokens signed by a project they control.
    supabase_url: str = ""

    # Escape hatch for local work before Supabase Auth is wired up. When true,
    # the API trusts an X-Dev-User-Id header instead of verifying a JWT.
    # This is unsafe by design and must stay false anywhere reachable.
    allow_dev_user_header: bool = False

    # Comma-separated browser origins allowed to call this API.
    cors_origins: str = "http://localhost:3000"

    @property
    def _supabase_base(self) -> str:
        # Tolerate a trailing slash so a pasted URL works either way.
        return self.supabase_url.rstrip("/")

    @property
    def jwks_url(self) -> str:
        """Where the project publishes its token-signing public keys."""
        return f"{self._supabase_base}/auth/v1/.well-known/jwks.json"

    @property
    def issuer(self) -> str:
        """Expected `iss` claim, so another project's tokens are rejected."""
        return f"{self._supabase_base}/auth/v1"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so every request reuses one parsed Settings instance."""
    return Settings()
