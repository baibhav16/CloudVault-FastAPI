from datetime import datetime, timezone

from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.database import Base


class Share(Base):
    __tablename__ = "shares"

    __table_args__ = (
        UniqueConstraint(
            "file_id",
            "shared_with_user_id",
            name="uq_file_shared_user",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    file_id: Mapped[int] = mapped_column(
        ForeignKey("files.id"),
        nullable=False,
        index=True,
    )

    shared_with_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    permission: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="VIEWER",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    file = relationship(
        "File",
        back_populates="shares",
    )

    shared_with = relationship(
        "User",
        back_populates="shared_files",
    )