import time
import jwt
from .utils_cfg import get_cfg

def create_token(payload: dict) -> str:
    secret = get_cfg("JWT_SECRET") or "dev_secret"
    exp_in = int(get_cfg("JWT_EXPIRES_IN") or "604800")
    data = dict(payload)
    data["exp"] = int(time.time()) + exp_in
    return jwt.encode(data, secret, algorithm="HS256")

def decode_token(token: str) -> dict:
    secret = get_cfg("JWT_SECRET") or "dev_secret"
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        return {}

