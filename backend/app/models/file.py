from datetime import datetime, timezone

from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    BigInteger,
    Boolean,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.database import Base


class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        index=True,
    )

    original_name: Mapped[str] = mapped_column(
        String(255),
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("folders.id"),
        nullable=True,
        index=True,
    )

    storage_key: Mapped[str] = mapped_column(
        String(500),
        unique=True,
    )

    size: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
    )

    content_type: Mapped[str] = mapped_column(
        String(150),
    )

    deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ========================================================
    # RELATIONSHIPS
    # ========================================================

    owner = relationship(
        "User",
        back_populates="files",
    )

    folder = relationship(
        "Folder",
        back_populates="files",
    )

    versions = relationship(
        "FileVersion",
        back_populates="file",
        cascade="all, delete-orphan",
    )

    shares = relationship(
        "Share",
        back_populates="file",
        cascade="all, delete-orphan",
    )