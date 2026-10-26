"""Local accounts, plus introspection for proxy and dev auth."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request

from echo.adapters.auth.cookies import COOKIE_NAME
from echo.adapters.auth.passwords import (
    dummy_password_hash,
    hash_password,
    verify_password,
)
from echo.adapters.db.users import (
    UserRecord,
    count_users,
    create_session,
    delete_session,
    get_user_by_email,
    get_user_by_id,
    insert_user,
    lock_registration,
)
from echo.api.deps.auth import CurrentUser
from echo.api.routes.entries import DbSession
from echo.config import AuthBackend, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthConfigResponse(BaseModel):
    auth_backend: str
    needs_setup: bool
    oidc_enabled: bool
    oidc_display_name: str


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=200)
    name: str = Field(min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or email.startswith("@") or email.endswith("@") or " " in email:
            raise ValueError("Invalid email")
        return email

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name is required")
        return stripped


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class WhoamiResponse(BaseModel):
    user_id: UUID
    email: str | None = None
    name: str | None = None
    is_admin: bool = False


class AccountResponse(BaseModel):
    user_id: UUID
    email: str
    name: str
    is_admin: bool

    @classmethod
    def from_user(cls, user: UserRecord) -> "AccountResponse":
        return cls(user_id=user.id, email=user.email, name=user.name, is_admin=user.is_admin)


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        path="/",
    )


async def _start_session(session: DbSession, user_id: UUID, response: Response) -> None:
    settings = get_settings()
    token = await create_session(session, user_id, settings.session_ttl_days)
    await session.commit()
    _set_session_cookie(response, token)


@router.get("/config", response_model=AuthConfigResponse)
async def auth_config(session: DbSession) -> AuthConfigResponse:
    """Tell the UI which login to show. Public: no session required."""
    settings = get_settings()
    needs_setup = False
    if settings.auth_backend == AuthBackend.LOCAL:
        needs_setup = await count_users(session) == 0
    return AuthConfigResponse(
        auth_backend=settings.auth_backend.value,
        needs_setup=needs_setup,
        oidc_enabled=settings.oidc_enabled,
        oidc_display_name=settings.oidc_display_name,
    )


@router.post("/register", response_model=AccountResponse)
async def register(
    body: RegisterRequest,
    session: DbSession,
    response: Response,
) -> AccountResponse:
    """Create the first admin account and sign them in. Closed after that."""
    settings = get_settings()
    if settings.auth_backend != AuthBackend.LOCAL:
        raise HTTPException(status_code=404, detail="Local accounts are not enabled")

    await lock_registration(session)
    if await count_users(session) > 0:
        raise HTTPException(status_code=403, detail="Registration is closed")

    user = await insert_user(
        session,
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
        is_admin=True,
    )
    await _start_session(session, user.id, response)
    return AccountResponse.from_user(user)


@router.post("/login", response_model=AccountResponse)
async def login(
    body: LoginRequest,
    session: DbSession,
    response: Response,
) -> AccountResponse:
    """Sign in with email and password."""
    settings = get_settings()
    if settings.auth_backend != AuthBackend.LOCAL:
        raise HTTPException(status_code=404, detail="Local accounts are not enabled")

    user = await get_user_by_email(session, body.email)
    password_hash = user.password_hash if user and user.password_hash else dummy_password_hash()
    if user is None or not user.password_hash or not verify_password(password_hash, body.password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    await _start_session(session, user.id, response)
    return AccountResponse.from_user(user)


@router.post("/logout", status_code=204)
async def logout(request: Request, session: DbSession, response: Response) -> None:
    """Clear the local session cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        await delete_session(session, token)
        await session.commit()
    response.delete_cookie(COOKIE_NAME, path="/")


@router.post("/users", response_model=AccountResponse)
async def create_user(
    body: RegisterRequest,
    user_id: CurrentUser,
    session: DbSession,
) -> AccountResponse:
    """Admin-only: add another local account. Does not start a session for them."""
    caller = await get_user_by_id(session, user_id)
    if caller is None or not caller.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    try:
        user = await insert_user(
            session,
            email=body.email,
            name=body.name,
            password_hash=hash_password(body.password),
            is_admin=False,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="An account with that email already exists",
        ) from exc
    return AccountResponse.from_user(user)


@router.get("/whoami", response_model=WhoamiResponse)
async def whoami(user_id: CurrentUser, session: DbSession) -> WhoamiResponse:
    """Return the resolved user id for the current request."""
    user = await get_user_by_id(session, user_id)
    if user is None:
        return WhoamiResponse(user_id=user_id)
    return WhoamiResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        is_admin=user.is_admin,
    )
