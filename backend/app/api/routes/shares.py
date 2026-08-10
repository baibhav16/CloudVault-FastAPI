from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.file import File as DBFile
from app.models.share import Share
from app.models.user import User
from app.schemas.share import ShareCreate, ShareResponse


router = APIRouter()


# ============================================================
# SHARE FILE
# ============================================================

@router.post(
    "/files/{file_id}",
    response_model=ShareResponse,
    status_code=201,
)
def share_file(
    file_id: int,
    payload: ShareCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Share a file with another registered CloudVault user.
    """

    # --------------------------------------------------------
    # Find file
    # --------------------------------------------------------

    db_file = db.get(
        DBFile,
        file_id
    )

    if not db_file:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    # --------------------------------------------------------
    # Only owner can share
    # --------------------------------------------------------

    if db_file.owner_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the file owner can share this file",
        )

    # --------------------------------------------------------
    # Cannot share with yourself
    # --------------------------------------------------------

    target_email = payload.email.strip().lower()

    if target_email == user.email.lower():
        raise HTTPException(
            status_code=400,
            detail="You cannot share a file with yourself",
        )

    # --------------------------------------------------------
    # Find target user
    # --------------------------------------------------------

    target_user = db.scalar(
        select(User).where(
            User.email == target_email
        )
    )

    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="User with this email does not exist",
        )

    # --------------------------------------------------------
    # Check existing share
    # --------------------------------------------------------

    existing_share = db.scalar(
        select(Share).where(
            Share.file_id == file_id,
            Share.shared_with_user_id == target_user.id,
        )
    )

    if existing_share:

        # Update permission instead of creating duplicate
        existing_share.permission = (
            payload.permission.upper()
        )

        db.commit()
        db.refresh(existing_share)

        return existing_share

    # --------------------------------------------------------
    # Create share
    # --------------------------------------------------------

    share = Share(
        file_id=file_id,
        shared_with_user_id=target_user.id,
        permission=payload.permission.upper(),
    )

    db.add(share)

    db.commit()

    db.refresh(share)

    return share


# ============================================================
# LIST SHARED FILES
# ============================================================

@router.get(
    "/files",
)
def get_shared_files(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return files shared with the current user.
    """

    results = db.execute(
        select(
            Share,
            DBFile,
            User,
        )
        .join(
            DBFile,
            Share.file_id == DBFile.id,
        )
        .join(
            User,
            DBFile.owner_id == User.id,
        )
        .where(
            Share.shared_with_user_id == user.id,
            DBFile.deleted.is_(False),
        )
        .order_by(
            DBFile.updated_at.desc()
        )
    ).all()

    response = []

    for share, db_file, owner in results:

        response.append({
            "share_id": share.id,
            "file_id": db_file.id,
            "name": db_file.name,
            "original_name": db_file.original_name,
            "size": db_file.size,
            "content_type": db_file.content_type,
            "permission": share.permission,
            "owner_id": owner.id,
            "owner_name": owner.name,
            "owner_email": owner.email,
            "created_at": db_file.created_at,
        })

    return response


# ============================================================
# REVOKE SHARE
# ============================================================

@router.delete(
    "/{share_id}",
    status_code=204,
)
def revoke_share(
    share_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke a file share.

    Only the file owner can revoke it.
    """

    share = db.get(
        Share,
        share_id
    )

    if not share:
        raise HTTPException(
            status_code=404,
            detail="Share not found",
        )

    db_file = db.get(
        DBFile,
        share.file_id
    )

    if not db_file:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    if db_file.owner_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the file owner can revoke this share",
        )

    db.delete(share)

    db.commit()

    return None