import hashlib
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


def hash_value(value: str, salt: str = "securedoc_ip_salt") -> str:
    """SHA-256 hash of value + salt. Never stores raw values."""
    return hashlib.sha256(f"{value}{salt}".encode()).hexdigest()
