from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File as FastAPIFile,
    Form,
    Query,
)
from fastapi.responses import (
    FileResponse,
    StreamingResponse,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.file import File as DBFile
from app.models.folder import Folder
from app.models.share import Share
from app.models.version import FileVersion
from app.schemas.file import FileResponse as FileSchema
from app.storage import storage


router = APIRouter()


# ============================================================
# GET FILES
# ============================================================

@router.get(
    "",
    response_model=list[FileSchema]
)
def get_files(
    folder_id: int | None = None,

    search: str | None = Query(
        default=None,
        max_length=100
    ),

    user=Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Get files belonging to the current user.

    Includes current version metadata.
    """

    # --------------------------------------------------------
    # BASE QUERY
    # --------------------------------------------------------

    query = select(DBFile).where(
        DBFile.owner_id == user.id,
        DBFile.deleted.is_(False)
    )

    # --------------------------------------------------------
    # FOLDER FILTER
    # --------------------------------------------------------

    if folder_id is None:

        query = query.where(
            DBFile.folder_id.is_(None)
        )

    else:

        folder = db.get(
            Folder,
            folder_id
        )

        if not folder:

            raise HTTPException(
                status_code=404,
                detail="Folder not found"
            )

        if folder.owner_id != user.id:

            raise HTTPException(
                status_code=403,
                detail=(
                    "You don't have permission "
                    "to access this folder"
                )
            )

        query = query.where(
            DBFile.folder_id == folder_id
        )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if search and search.strip():

        query = query.where(
            DBFile.name.ilike(
                f"%{search.strip()}%"
            )
        )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    query = query.order_by(
        DBFile.updated_at.desc()
    )

    db_files = db.scalars(
        query
    ).all()

    # --------------------------------------------------------
    # BUILD RESPONSE
    # --------------------------------------------------------

    result = []

    for db_file in db_files:

        latest_version = db.scalar(
            select(FileVersion)
            .where(
                FileVersion.file_id ==
                db_file.id
            )
            .order_by(
                FileVersion.version_number.desc()
            )
            .limit(1)
        )

        current_version = (
            latest_version.version_number
            if latest_version
            else 1
        )

        result.append(
            {
                "id":
                    db_file.id,

                "name":
                    db_file.name,

                "original_name":
                    db_file.original_name,

                "owner_id":
                    db_file.owner_id,

                "folder_id":
                    db_file.folder_id,

                "storage_key":
                    db_file.storage_key,

                "size":
                    db_file.size,

                "content_type":
                    db_file.content_type,

                "deleted":
                    db_file.deleted,

                "created_at":
                    db_file.created_at,

                "updated_at":
                    db_file.updated_at,

                "current_version":
                    current_version,
            }
        )

    return result


# ============================================================
# UPLOAD FILE
# ============================================================

@router.post(
    "/upload",
    response_model=FileSchema,
    status_code=201
)
def upload_file(
    uploaded_file: UploadFile = FastAPIFile(...),

    folder_id: int | None = Form(
        default=None
    ),

    user=Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Upload a new file.

    The initial upload automatically
    becomes Version 1.
    """

    # ========================================================
    # VALIDATE FOLDER
    # ========================================================

    if folder_id is not None:

        folder = db.get(
            Folder,
            folder_id
        )

        if not folder:

            raise HTTPException(
                status_code=404,
                detail="Folder not found"
            )

        if folder.owner_id != user.id:

            raise HTTPException(
                status_code=403,
                detail="You don't have permission to upload to this folder"
            )

    # ========================================================
    # FILE NAME
    # ========================================================

    original_name = (
        uploaded_file.filename
        or "unnamed-file"
    )

    # Remove possible path components.

    original_name = Path(
        original_name
    ).name

    if not original_name:

        original_name = "unnamed-file"

    # ========================================================
    # STORAGE KEY
    # ========================================================

    unique_name = (
        f"{uuid4()}-{original_name}"
    )

    storage_key = (
        f"{user.id}/{unique_name}"
    )

    # ========================================================
    # SAVE FILE
    # ========================================================

    try:

        saved_key, file_size = (
            storage.save_upload(
                uploaded_file.file,
                storage_key
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to save file: {str(exc)}"
            )
        )

    content_type = (
        uploaded_file.content_type
        or "application/octet-stream"
    )

    # ========================================================
    # DATABASE FILE RECORD
    # ========================================================

    db_file = DBFile(
        name=original_name,

        original_name=original_name,

        owner_id=user.id,

        folder_id=folder_id,

        storage_key=saved_key,

        size=file_size,

        content_type=content_type,

    )

    db.add(db_file)

    # IMPORTANT:
    #
    # Flush gives db_file its ID
    # without committing the transaction.

    try:

        db.flush()

    except Exception:

        db.rollback()

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=500,
            detail="Failed to create file metadata"
        )

    # ========================================================
    # VERSION 1
    # ========================================================

    version_one = FileVersion(

        file_id=db_file.id,

        version_number=1,

        storage_key=saved_key,

        size=file_size,

    )

    db.add(
        version_one
    )

    # ========================================================
    # COMMIT EVERYTHING
    # ========================================================

    try:

        db.commit()

        db.refresh(
            db_file
        )

    except Exception:

        db.rollback()

        # Remove physical file if
        # database transaction fails.

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=500,
            detail="Failed to save file and version metadata"
        )

    return db_file


# ============================================================
# DOWNLOAD FILE
# ============================================================

@router.get(
    "/{file_id}/download"
)
def download_file(
    file_id: int,

    user=Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Download a file.

    Access is allowed for:

    1. Owner
    2. User with a valid share
    """

    db_file = db.get(
        DBFile,
        file_id
    )

    if not db_file:

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    # --------------------------------------------------------
    # TRASH
    # --------------------------------------------------------

    if db_file.deleted:

        raise HTTPException(
            status_code=404,
            detail="File is in Trash"
        )

    # --------------------------------------------------------
    # AUTHORIZATION
    # --------------------------------------------------------

    is_owner = (
        db_file.owner_id == user.id
    )

    if not is_owner:

        share = db.scalar(
            select(Share).where(
                Share.file_id == file_id,
                Share.shared_with_user_id == user.id
            )
        )

        if not share:

            raise HTTPException(
                status_code=403,
                detail="You don't have permission to download this file"
            )

    # --------------------------------------------------------
    # STORAGE CHECK
    # --------------------------------------------------------

    if not storage.exists(
        db_file.storage_key
    ):

        raise HTTPException(
            status_code=404,
            detail="Physical file not found"
        )

    # --------------------------------------------------------
    # S3
    # --------------------------------------------------------

    if storage.mode == "s3":

        file_stream = storage.download(
            db_file.storage_key
        )

        return StreamingResponse(
            file_stream,
            media_type=(
                db_file.content_type
                or "application/octet-stream"
            ),
            headers={
                "Content-Disposition":
                    f'attachment; filename="{db_file.original_name}"'
            },
        )

    # --------------------------------------------------------
    # LOCAL
    # --------------------------------------------------------

    return FileResponse(
        path=storage.get_path(
            db_file.storage_key
        ),
        filename=db_file.original_name,
        media_type=(
            db_file.content_type
            or "application/octet-stream"
        ),
    )


# ============================================================
# MOVE FILE TO TRASH
# ============================================================

@router.delete(
    "/{file_id}",
    status_code=204
)
def trash_file(
    file_id: int,

    user=Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Soft delete a file.
    """

    db_file = db.get(
        DBFile,
        file_id
    )

    if not db_file:

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    if db_file.owner_id != user.id:

        raise HTTPException(
            status_code=403,
            detail="Only the file owner can delete this file"
        )

    db_file.deleted = True

    db.commit()

    return None


# ============================================================
# GET TRASH
# ============================================================

@router.get(
    "/trash",
    response_model=list[FileSchema]
)
def get_trash(
    user=Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Return files currently in Trash.
    """

    query = (
        select(DBFile)
        .where(
            DBFile.owner_id == user.id,
            DBFile.deleted.is_(True)
        )
        .order_by(
            DBFile.updated_at.desc()
        )
    )

    return db.scalars(query).all()


# ============================================================
# RESTORE FILE
# ============================================================

@router.patch(
    "/{file_id}/restore",
    response_model=FileSchema
)
def restore_file(
    file_id: int,

    user=Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Restore a file from Trash.
    """

    db_file = db.get(
        DBFile,
        file_id
    )

    if not db_file:

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    if db_file.owner_id != user.id:

        raise HTTPException(
            status_code=403,
            detail="You don't have permission to restore this file"
        )

    if not db_file.deleted:

        raise HTTPException(
            status_code=400,
            detail="File is not in Trash"
        )

    db_file.deleted = False

    db.commit()

    db.refresh(
        db_file
    )

    return db_file


# ============================================================
# PERMANENT DELETE
# ============================================================

@router.delete(
    "/{file_id}/permanent",
    status_code=204
)
def permanently_delete_file(
    file_id: int,

    user=Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Permanently delete a file.

    Deletes:

    1. File versions from database
       through CASCADE.
    2. Physical original/current file.
    3. Physical version files.
    4. Main file database record.
    """

    db_file = db.get(
        DBFile,
        file_id
    )

    if not db_file:

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    if db_file.owner_id != user.id:

        raise HTTPException(
            status_code=403,
            detail="You don't have permission to permanently delete this file"
        )

    if not db_file.deleted:

        raise HTTPException(
            status_code=400,
            detail="File must be in Trash first"
        )

    # ========================================================
    # GET ALL VERSIONS
    # ========================================================

    versions = db.scalars(
        select(FileVersion).where(
            FileVersion.file_id == file_id
        )
    ).all()

    # ========================================================
    # DELETE CURRENT FILE
    # ========================================================

    try:

        if storage.exists(
            db_file.storage_key
        ):

            storage.delete(
                db_file.storage_key
            )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to delete physical file: "
                f"{str(exc)}"
            )
        )

    # ========================================================
    # DELETE VERSION FILES
    # ========================================================

    for version in versions:

        if (
            version.storage_key
            == db_file.storage_key
        ):
            continue

        try:

            if storage.exists(
                version.storage_key
            ):

                storage.delete(
                    version.storage_key
                )

        except Exception:

            # Continue deleting other versions.
            pass

    # ========================================================
    # DELETE DATABASE RECORD
    # ========================================================

    db.delete(
        db_file
    )

    db.commit()

    return None