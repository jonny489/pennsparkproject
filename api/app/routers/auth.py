"""Registration, sign-in, and Google OAuth."""

from urllib.parse import urlencode
from uuid import UUID

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.auth import get_current_user_id, unauthorized
from app.config import Settings, get_settings
from app.db import get_user_repository
from app.models import TokenResponse, UserCreate, UserLogin, UserRead, UserRecord
from app.security import hash_password, verify_password
from app.tokens import create_access_token, sign_state, verify_state
from app.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# One message for every failed sign-in, so the endpoint cannot be used to
# discover which email addresses have accounts.
_BAD_CREDENTIALS = "Incorrect email or password"


def _token_response(user: UserRecord, settings: Settings) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.email, settings),
        user=UserRead.model_validate(user),
    )


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    data: UserCreate,
    users: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    if await users.get_by_email(data.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        )
    user = await users.create_user(
        data.email, password_hash=hash_password(data.password)
    )
    return _token_response(user, settings)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    users: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = await users.get_by_email(data.email)

    # A Google-only account has no hash, and takes the same failure path as an
    # unknown email or a wrong password.
    if user is None or user.password_hash is None:
        raise unauthorized(_BAD_CREDENTIALS)
    if not verify_password(data.password, user.password_hash):
        raise unauthorized(_BAD_CREDENTIALS)

    return _token_response(user, settings)


@router.get("/me", response_model=UserRead)
async def me(
    user_id: UUID = Depends(get_current_user_id),
    users: UserRepository = Depends(get_user_repository),
) -> UserRead:
    user = await users.get_by_id(user_id)
    if user is None:
        raise unauthorized("Account no longer exists")
    return UserRead.model_validate(user)


async def exchange_code(code: str, settings: Settings) -> dict:
    """Trade an authorization code for the caller's Google identity.

    The only function here that touches the network; tests replace it wholesale.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    response.raise_for_status()
    # The id_token came straight from Google's token endpoint over TLS, so the
    # channel already establishes its authenticity.
    return jwt.decode(response.json()["id_token"], options={"verify_signature": False})


@router.get("/google")
async def google_start(settings: Settings = Depends(get_settings)) -> RedirectResponse:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email",
        "state": sign_state(settings),
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    users: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    try:
        verify_state(state, settings)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state"
        ) from exc

    identity = await exchange_code(code, settings)
    google_sub, email = identity["sub"], identity["email"]

    user = await users.get_by_google_sub(google_sub)
    if user is None:
        existing = await users.get_by_email(email)
        if existing is None:
            user = await users.create_user(email, google_sub=google_sub)
        elif identity.get("email_verified"):
            user = await users.link_google(existing.id, google_sub)
        else:
            # Linking on an unverified address would let someone claim an
            # account they do not own.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="That email is already registered. Sign in with your password.",
            )

    token = create_access_token(user.id, user.email, settings)
    # The fragment is never sent to a server, keeping the token out of access
    # logs and Referer headers.
    return RedirectResponse(f"{settings.frontend_url}/auth/callback#token={token}")
