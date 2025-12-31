"""
Authentication routes for ABS-based login.
Validates credentials against Audiobookshelf server.
"""
from fastapi import APIRouter, Header, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import httpx
import logging

from config import ABS_BASE_URL, ABS_ADMIN_USER
from dependencies.abs import is_admin_user
from abs_client import get_abs_client
from settings_service import settings_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger("mam-audiofinder")


class LoginRequest(BaseModel):
    """Login request body."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response."""
    ok: bool
    token: Optional[str] = None
    user: Optional[dict] = None
    isAdmin: bool = False
    error: Optional[str] = None


class AuthStatusResponse(BaseModel):
    """Auth status response."""
    requires_auth: bool
    abs_configured: bool
    abs_url: Optional[str] = None
    authenticated: bool = False


@router.get("/status")
async def get_auth_status(
    x_abs_token: Optional[str] = Header(None, alias="X-ABS-Token")
) -> AuthStatusResponse:
    """
    Check authentication requirements and current status.
    Called on app initialization to determine if login is needed.
    """
    abs_configured = bool(ABS_BASE_URL)

    if not abs_configured:
        return AuthStatusResponse(
            requires_auth=False,
            abs_configured=False,
            authenticated=True  # No auth needed if ABS not configured
        )

    # If token provided, validate it
    authenticated = False
    if x_abs_token:
        authenticated = await _validate_token(ABS_BASE_URL, x_abs_token)

    return AuthStatusResponse(
        requires_auth=True,
        abs_configured=True,
        abs_url=ABS_BASE_URL,
        authenticated=authenticated
    )


@router.post("/login")
async def login(request: LoginRequest) -> LoginResponse:
    """
    Authenticate against ABS server.

    Flow:
    1. POST to ABS /login with username/password
    2. Extract token from response.user.token
    3. Return token to frontend for storage
    """
    if not ABS_BASE_URL:
        return LoginResponse(
            ok=False,
            error="Audiobookshelf is not configured. Set ABS_BASE_URL in your environment."
        )

    abs_url = ABS_BASE_URL

    # Step 0: Check server is reachable
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            ping_resp = await client.get(f"{abs_url}/ping")
            if ping_resp.status_code != 200:
                logger.warning(f"⚠️  ABS server not reachable at {abs_url}")
                return LoginResponse(
                    ok=False,
                    error=f"ABS server not reachable at {abs_url}"
                )
    except httpx.TimeoutException:
        logger.error(f"❌ ABS ping timeout: {abs_url}")
        return LoginResponse(
            ok=False,
            error="Connection timed out. Check the server URL."
        )
    except Exception as e:
        logger.error(f"❌ ABS ping failed: {e}")
        return LoginResponse(
            ok=False,
            error=f"Cannot connect to ABS server: {str(e)}"
        )

    # Step 1: POST /login
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            login_resp = await client.post(
                f"{abs_url}/login",
                json={"username": request.username, "password": request.password}
            )

            if login_resp.status_code == 401:
                logger.warning(f"⚠️  Invalid credentials for user '{request.username}'")
                return LoginResponse(ok=False, error="Invalid username or password")

            if login_resp.status_code != 200:
                logger.error(f"❌ ABS login failed: HTTP {login_resp.status_code}")
                return LoginResponse(
                    ok=False,
                    error=f"Login failed: HTTP {login_resp.status_code}"
                )

            data = login_resp.json()
            user = data.get("user", {})
            token = user.get("token")

            if not token:
                logger.error("❌ No token in ABS login response")
                return LoginResponse(ok=False, error="No token in response")

            username = user.get("username", "")
            user_is_admin = is_admin_user(username)

            logger.info(f"✅ User '{username}' authenticated against ABS (admin: {user_is_admin})")

            # Auto-initialize libraries on first login (non-blocking)
            await _initialize_libraries_if_needed(token)

            return LoginResponse(
                ok=True,
                token=token,
                user={
                    "username": username,
                    "type": user.get("type"),
                    "isActive": user.get("isActive")
                },
                isAdmin=user_is_admin
            )

    except httpx.TimeoutException:
        logger.error("❌ ABS login timeout")
        return LoginResponse(ok=False, error="Login request timed out")
    except Exception as e:
        logger.error(f"❌ ABS login failed: {e}")
        return LoginResponse(ok=False, error=f"Login failed: {str(e)}")


@router.post("/validate")
async def validate_token(
    x_abs_token: str = Header(..., alias="X-ABS-Token")
) -> dict:
    """
    Validate an existing token against ABS.
    Uses POST /api/authorize endpoint.
    """
    if not ABS_BASE_URL:
        return {"valid": True, "reason": "ABS not configured"}

    valid = await _validate_token(ABS_BASE_URL, x_abs_token)
    return {"valid": valid}


@router.post("/logout")
async def logout() -> dict:
    """
    Logout endpoint - frontend handles token removal.
    Backend doesn't store tokens, so this is just a confirmation endpoint.
    """
    logger.info("🚪 User logged out")
    return {"ok": True}


async def _validate_token(abs_url: str, token: str) -> bool:
    """Validate token using ABS /api/authorize endpoint."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{abs_url}/api/authorize",
                headers={"Authorization": f"Bearer {token}"}
            )
            return resp.status_code == 200
    except Exception as e:
        logger.debug(f"🔍 Token validation failed: {e}")
        return False


async def _initialize_libraries_if_needed(token: str) -> None:
    """
    Initialize libraries if not already done.

    Called after successful login to auto-enable audiobook libraries.
    This ensures library checks and cover fetching work immediately
    without requiring the user to visit Settings first.
    """
    try:
        # Check if already initialized
        if settings_service.is_libraries_initialized():
            logger.debug("📚 Libraries already initialized, skipping")
            return

        # Fetch libraries from ABS
        client = get_abs_client(user_token=token)
        libraries = await client.get_all_libraries()

        if not libraries:
            logger.warning("⚠️ No libraries found in ABS")
            return

        # Convert to dicts and initialize (auto-enables 'book' type libraries)
        lib_dicts = [
            {"id": lib.id, "name": lib.name, "media_type": lib.media_type, "icon": lib.icon}
            for lib in libraries
        ]
        settings_service.initialize_libraries(lib_dicts)

        enabled_ids = settings_service.get_enabled_libraries()
        logger.info(f"📚 Auto-initialized {len(enabled_ids)} audiobook libraries")

    except Exception as e:
        logger.warning(f"⚠️ Failed to auto-initialize libraries: {e}")
