"""Startup configuration checks."""

import pytest

from app.config import Settings, require_runtime_settings


def test_a_complete_config_passes() -> None:
    require_runtime_settings(
        Settings(database_url="postgresql://x", jwt_secret="a-secret")
    )


def test_an_empty_jwt_secret_stops_startup() -> None:
    """PyJWT signs happily with an empty key, so without this the app would
    issue tokens that no request can verify."""
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        require_runtime_settings(Settings(database_url="postgresql://x", jwt_secret=""))


def test_a_missing_database_url_stops_startup() -> None:
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        require_runtime_settings(Settings(database_url="", jwt_secret="a-secret"))
