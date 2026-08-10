from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.folder import Folder
from app.schemas.folder import (
    FolderCreate,
    FolderResponse,
)

router = APIRouter()


@router.get(
    "",
    response_model=list[FolderResponse]
)
def list_folders(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Folder)
        .where(Folder.owner_id == user.id)
        .order_by(Folder.name)
    ).all()


@router.post(
    "",
    response_model=FolderResponse,
    status_code=201
)
def create_folder(
    payload: FolderCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check parent folder
    if payload.parent_folder_id is not None:
        parent = db.get(
            Folder,
            payload.parent_folder_id
        )

        if not parent or parent.owner_id != user.id:
            raise HTTPException(
                status_code=404,
                detail="Parent folder not found"
            )

    folder = Folder(
        name=payload.name.strip(),
        owner_id=user.id,
        parent_folder_id=payload.parent_folder_id,
    )

    db.add(folder)
    db.commit()
    db.refresh(folder)

    return folder