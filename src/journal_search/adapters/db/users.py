"""Local account and session storage."""

import hashlib
import secrets
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Named so the lock is distinct from other advisory locks in this database.
# hashtext() turns the name into the integer key. The lock lasts for one
# transaction, so the key does not need to survive a Postgres upgrade.
_REGISTER_LOCK_NAME = "journal_search.user_registration"


_USER_COLUMNS = "id, email, name, password_hash, is_admin, oidc_issuer, oidc_subject"


@dataclass(frozen=True)
class UserRecord:
    """A row from the users table."""

    id: UUID
    email: str
    name: str
    password_hash: str | None
    is_admin: bool
    oidc_issuer: str | None = None
    oidc_subject: str | None = None


def hash_session_token(token: str) -> str:
    """Store a hash of the cookie value, not the cookie itself."""
    return hashlib.sha256(token.encode()).hexdigest()


def _user_from_row(row: object) -> UserRecord:
    mapping = row._mapping  # type: ignore[attr-defined]
    return UserRecord(
        id=mapping["id"],
        email=mapping["email"],
        name=mapping["name"],
        password_hash=mapping["password_hash"],
        is_admin=mapping["is_admin"],
        oidc_issuer=mapping["oidc_issuer"],
        oidc_subject=mapping["oidc_subject"],
    )


async def count_users(session: AsyncSession) -> int:
    """Return how many local accounts exist."""
    result = await session.execute(text("SELECT COUNT(*) AS count FROM users"))
    return int(result.scalar_one())


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> UserRecord | None:
    """Load an account by primary key."""
    result = await session.execute(
        text("""
            SELECT id, email, name, password_hash, is_admin, oidc_issuer, oidc_subject
            FROM users
            WHERE id = :id
        """),
        {"id": user_id},
    )
    row = result.first()
    if row is None:
        return None
    return _user_from_row(row)


async def get_user_by_email(session: AsyncSession, email: str) -> UserRecord | None:
    """Load an account by normalized email."""
    result = await session.execute(
        text("""
            SELECT id, email, name, password_hash, is_admin, oidc_issuer, oidc_subject
            FROM users
            WHERE email = :email
        """),
        {"email": email},
    )
    row = result.first()
    if row is None:
        return None
    return _user_from_row(row)


async def lock_registration(session: AsyncSession) -> None:
    """Serialize first-admin registration for the rest of this transaction."""
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_name)::bigint)"),
        {"lock_name": _REGISTER_LOCK_NAME},
    )


async def get_user_by_oidc(
    session: AsyncSession,
    issuer: str,
    subject: str,
) -> UserRecord | None:
    """Load an account already linked to this issuer and subject."""
    result = await session.execute(
        text(f"""
            SELECT {_USER_COLUMNS}
            FROM users
            WHERE oidc_issuer = :issuer AND oidc_subject = :subject
        """),
        {"issuer": issuer, "subject": subject},
    )
    row = result.first()
    if row is None:
        return None
    return _user_from_row(row)


async def link_oidc(
    session: AsyncSession,
    user_id: UUID,
    issuer: str,
    subject: str,
) -> None:
    """Attach an OIDC identity to an existing account."""
    await session.execute(
        text("""
            UPDATE users
            SET oidc_issuer = :issuer, oidc_subject = :subject
            WHERE id = :id
        """),
        {"id": user_id, "issuer": issuer, "subject": subject},
    )


async def insert_user(
    session: AsyncSession,
    *,
    email: str,
    name: str,
    password_hash: str | None,
    is_admin: bool,
    user_id: UUID | None = None,
    oidc_issuer: str | None = None,
    oidc_subject: str | None = None,
) -> UserRecord:
    """Insert an account and return it."""
    user_id = user_id or uuid4()
    await session.execute(
        text("""
            INSERT INTO users (
                id, email, name, password_hash, is_admin, oidc_issuer, oidc_subject
            ) VALUES (
                :id, :email, :name, :password_hash, :is_admin, :oidc_issuer, :oidc_subject
            )
        """),
        {
            "id": user_id,
            "email": email,
            "name": name,
            "password_hash": password_hash,
            "is_admin": is_admin,
            "oidc_issuer": oidc_issuer,
            "oidc_subject": oidc_subject,
        },
    )
    user = await get_user_by_id(session, user_id)
    if user is None:
        raise RuntimeError("Inserted user could not be reloaded")
    return user


async def create_session(session: AsyncSession, user_id: UUID, ttl_days: int) -> str:
    """Persist a session and return the raw cookie token."""
    token = secrets.token_urlsafe(32)
    await session.execute(
        text("""
            INSERT INTO sessions (id, user_id, token_hash, expires_at)
            VALUES (
                :id,
                :user_id,
                :token_hash,
                NOW() + make_interval(days => :ttl_days)
            )
        """),
        {
            "id": uuid4(),
            "user_id": user_id,
            "token_hash": hash_session_token(token),
            "ttl_days": ttl_days,
        },
    )
    return token


async def user_id_for_token(session: AsyncSession, token: str) -> UUID | None:
    """Resolve a cookie token to a user id when the session is unexpired."""
    result = await session.execute(
        text("""
            SELECT user_id
            FROM sessions
            WHERE token_hash = :token_hash
              AND expires_at > NOW()
        """),
        {"token_hash": hash_session_token(token)},
    )
    row = result.first()
    if row is None:
        return None
    user_id = row._mapping["user_id"]  # type: ignore[attr-defined]
    return user_id if isinstance(user_id, UUID) else UUID(str(user_id))


async def delete_session(session: AsyncSession, token: str) -> None:
    """Remove the session for a cookie token."""
    await session.execute(
        text("DELETE FROM sessions WHERE token_hash = :token_hash"),
        {"token_hash": hash_session_token(token)},
    )
