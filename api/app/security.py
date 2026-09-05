"""Password hashing."""

import bcrypt

# bcrypt ignores everything past 72 bytes. Truncating silently would make two
# different long passwords interchangeable, so the limit is enforced instead.
MAX_PASSWORD_BYTES = 72


def hash_password(plain: str) -> str:
    encoded = plain.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(f"password must be at most {MAX_PASSWORD_BYTES} bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    encoded = plain.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
