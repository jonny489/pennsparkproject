"""Password hashing."""

import pytest

from app.security import hash_password, verify_password


def test_a_hash_verifies_against_its_own_password() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True


def test_a_wrong_password_does_not_verify() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("Correct horse battery staple", hashed) is False


def test_the_hash_is_not_the_password() -> None:
    assert "hunter2" not in hash_password("hunter2")


def test_the_same_password_hashes_differently_each_time() -> None:
    """Distinct salts, so identical passwords give different hashes."""
    assert hash_password("same") != hash_password("same")


def test_a_password_over_72_bytes_is_rejected() -> None:
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password("a" * 73)
