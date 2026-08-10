from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    parent_folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("folders.id"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # User who owns the folder
    owner = relationship(
        "User",
        back_populates="folders"
    )

    # Parent folder
    parent = relationship(
        "Folder",
        remote_side=[id],
        back_populates="children"
    )

    # Child folders
    children = relationship(
        "Folder",
        back_populates="parent"
    )

    # Files inside this folder
    files = relationship(
        "File",
        back_populates="folder"
    )