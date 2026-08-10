from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


def register(
    db: Session,
    name: str,
    email: str,
    password: str
) -> User:

    email = email.strip().lower()

    existing = db.scalar(
        select(User).where(User.email == email)
    )

    if existing:
        raise ValueError("Email already registered")

    user = User(
        name=name.strip(),
        email=email,
        password_hash=hash_password(password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate(
    db: Session,
    email: str,
    password: str
) -> User | None:

    email = email.strip().lower()

    user = db.scalar(
        select(User).where(User.email == email)
    )

    if user is None:
        return None

    if not verify_password(
        password,
        user.password_hash
    ):
        return None

    return user