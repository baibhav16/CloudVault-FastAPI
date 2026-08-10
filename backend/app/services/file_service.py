from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.models.file import File
from app.models.share import Share


def list_files(db: Session, user_id: int, folder_id: int | None, search: str | None):
    query = select(File).where(File.deleted.is_(False))
    query = query.where(
        or_(
            File.owner_id == user_id,
            File.id.in_(
                select(Share.file_id).where(Share.shared_with_user_id == user_id)
            ),
        )
    )
    if folder_id is not None:
        query = query.where(File.folder_id == folder_id)
    if search:
        query = query.where(File.name.ilike(f"%{search}%"))
    return db.scalars(query.order_by(File.updated_at.desc())).all()
