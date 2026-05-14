import hashlib
from typing import Optional
import bcrypt


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def hash_value(value: str, salt: Optional[str] = None) -> str:
    """SHA-256 hash of value + salt. Never stores raw values.

    The salt is sourced from settings.ip_hash_salt (env var IP_HASH_SALT) so
    it stays out of source code. An explicit salt may be passed for testing.
    """
    if salt is None:
        from app.config import settings
        salt = settings.ip_hash_salt
    return hashlib.sha256(f"{value}{salt}".encode()).hexdigest()


def mask_email(email: str) -> str:
    """Return a privacy-safe masked form of an email address for DB storage.

    Keeps the first character of the local part and the full domain so the
    document owner can still recognise who accessed their document, while
    preventing a DB dump from harvesting full viewer email addresses.

    Examples:
        user@example.com       → u***@example.com
        student@psgtech.ac.in  → s***@psgtech.ac.in
        a@b.com                → a***@b.com

    If the value contains no '@' it is returned unchanged (malformed inputs
    are stored as-is so the log entry is not silently lost).
    """
    if not email or "@" not in email:
        return email
    local, domain = email.rsplit("@", 1)
    return f"{local[0]}***@{domain}"
