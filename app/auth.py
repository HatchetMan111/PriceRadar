"""HTTP Basic Auth for the PriceRadar web UI and API.

PriceRadar has no user accounts - it's a single-user, self-hosted tool. HTTP
Basic Auth is deliberately chosen over a session/cookie login:

- it's trivial to set up for a single admin user via environment variables,
- it works transparently behind a reverse proxy, and
- browsers only attach the Authorization header to same-origin requests, so
  a classic cross-site <form> POST cannot forward stored credentials the way
  it can forward cookies. That gives the mutating POST routes meaningful CSRF
  resistance without a separate token scheme.

If PRICERADAR_AUTH_USER / PRICERADAR_AUTH_PASSWORD are not both set, auth is
disabled for convenient local development, but a warning is logged at startup.
"""
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import AUTH_PASSWORD, AUTH_USER

_security = HTTPBasic(auto_error=False)


def auth_enabled() -> bool:
    return bool(AUTH_USER and AUTH_PASSWORD)


def require_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> None:
    if not auth_enabled():
        return
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Basic"},
    )
    if credentials is None:
        raise unauthorized
    user_ok = secrets.compare_digest(credentials.username, AUTH_USER)
    pass_ok = secrets.compare_digest(credentials.password, AUTH_PASSWORD)
    if not (user_ok and pass_ok):
        raise unauthorized
