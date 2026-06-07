from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import hashlib
import hmac
import json
import time
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings, get_settings


security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    username: str
    role: str
    exp: int


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_token(username: str, role: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    payload = {
        "sub": username,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + settings.token_ttl_seconds,
    }
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.app_secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64encode(signature)}"


def decode_token(token: str, settings: Settings | None = None) -> Principal:
    settings = settings or get_settings()
    try:
        body, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token no valido") from exc

    expected = hmac.new(settings.app_secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    received = _b64decode(signature)
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firma de token no valida")

    try:
        payload = json.loads(_b64decode(body).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Payload de token no valido") from exc

    exp = int(payload.get("exp", 0))
    if datetime.now(timezone.utc).timestamp() > exp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token caducado")

    role = payload.get("role")
    if role not in {"admin", "user"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rol no permitido")

    return Principal(username=str(payload.get("sub", "anonymous")), role=role, exp=exp)


def current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> Principal:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falta token bearer")
    return decode_token(credentials.credentials)


def require_admin(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
    if principal.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operacion solo para administradores")
    return principal
