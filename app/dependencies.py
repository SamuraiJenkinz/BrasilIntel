"""
Dependency injection for BrasilIntel API.

Provides reusable dependencies for FastAPI routes.
"""
import secrets
from collections.abc import Generator
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal

# HTTP Basic authentication scheme for API access
security = HTTPBasic(auto_error=False)

# Session token storage (in-memory for simplicity)
# In production, consider using Redis or database-backed sessions
active_sessions: dict[str, str] = {}


def create_session_token(username: str) -> str:
    """Create a new session token for authenticated user."""
    token = secrets.token_urlsafe(32)
    active_sessions[token] = username
    return token


def validate_session_token(token: str) -> Optional[str]:
    """Validate session token and return username if valid."""
    return active_sessions.get(token)


def invalidate_session_token(token: str) -> None:
    """Invalidate a session token (logout)."""
    active_sessions.pop(token, None)


def verify_credentials(username: str, password: str, settings: Settings) -> bool:
    """
    Verify username and password against configured credentials.

    Uses constant-time comparison to prevent timing attacks.
    """
    if not settings.admin_password:
        return False

    username_correct = secrets.compare_digest(
        username.encode("utf-8"),
        settings.admin_username.encode("utf-8")
    )
    password_correct = secrets.compare_digest(
        password.encode("utf-8"),
        settings.admin_password.encode("utf-8")
    )

    return username_correct and password_correct


def verify_admin(
    request: Request,
    credentials: Annotated[Optional[HTTPBasicCredentials], Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
    session_token: Annotated[Optional[str], Cookie(alias="brasilintel_session")] = None
) -> str:
    """
    Verify admin access via session cookie or HTTP Basic credentials.

    Supports two authentication methods:
    1. Session cookie (from HTML form login)
    2. HTTP Basic Auth (for API/curl access)

    Args:
        request: FastAPI request object
        credentials: HTTP Basic credentials (optional)
        settings: Application settings
        session_token: Session cookie value (optional)

    Returns:
        Username on successful authentication

    Raises:
        HTTPException 401: If not authenticated (redirects to login for browsers)
    """
    # Check session cookie first
    if session_token:
        username = validate_session_token(session_token)
        if username:
            return username

    # Check HTTP Basic Auth
    if credentials:
        if verify_credentials(credentials.username, credentials.password, settings):
            return credentials.username

    # Not authenticated - check if this is a browser request
    accept_header = request.headers.get("accept", "")
    is_browser = "text/html" in accept_header

    if is_browser:
        # Redirect to login page for browser requests
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"}
        )

    # Return 401 for API requests
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Basic"},
    )


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Yields a SQLAlchemy session and ensures cleanup after request completion.
    Note: Commit happens in endpoint handlers, not here, to support
    proper transaction control per FastAPI best practices.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
