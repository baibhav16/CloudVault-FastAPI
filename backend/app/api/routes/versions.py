from uuid import uuid4
from pathlib import Path
import re

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File as FastAPIFile,
)
from fastapi.responses import (
    FileResponse,
    StreamingResponse,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.file import File as DBFile
from app.models.version import FileVersion
from app.storage import storage


router = APIRouter()


# ============================================================
# HELPER - CLEAN FILE NAME
# ============================================================

def clean_original_filename(
    filename: str | None,
) -> str:

    if not filename:
        return "unnamed-file"

    # Prevent paths from becoming part of the filename
    filename = Path(filename).name

    # Remove accidental version suffixes.
    #
    # Example:
    #
    # ZS (1).pdf.v4
    #
    # becomes:
    #
    # ZS (1).pdf

    filename = re.sub(
        r"\.v\d+$",
        "",
        filename,
        flags=re.IGNORECASE,
    )

    if not filename:
        return "unnamed-file"

    return filename


# ============================================================
# HELPER - VERSION DOWNLOAD NAME
# ============================================================

def make_version_filename(
    original_name: str,
    version_number: int,
) -> str:

    original_name = clean_original_filename(
        original_name
    )

    path = Path(original_name)

    # File has extension

    if path.suffix:

        return (
            f"{path.stem} "
            f"(Version {version_number})"
            f"{path.suffix}"
        )

    # File has no extension

    return (
        f"{original_name} "
        f"(Version {version_number})"
    )


# ============================================================
# UPLOAD NEW VERSION
# ============================================================

@router.post(
    "/{file_id}",
    status_code=201,
)
def upload_new_version(
    file_id: int,

    uploaded_file: UploadFile = FastAPIFile(...),

    user=Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Upload a new version of an existing file.

    The actual file is stored using the configured
    storage backend (S3 or local storage).
    """

    # --------------------------------------------------------
    # FIND FILE
    # --------------------------------------------------------

    db_file = db.get(
        DBFile,
        file_id,
    )

    if not db_file:

        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    # --------------------------------------------------------
    # OWNER CHECK
    # --------------------------------------------------------

    if db_file.owner_id != user.id:

        raise HTTPException(
            status_code=403,
            detail=(
                "Only the file owner can "
                "upload a new version"
            ),
        )

    # --------------------------------------------------------
    # TRASH CHECK
    # --------------------------------------------------------

    if db_file.deleted:

        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot create a version "
                "for a file in Trash"
            ),
        )

    # --------------------------------------------------------
    # GET LATEST VERSION
    # --------------------------------------------------------

    latest_version = db.scalar(
        select(FileVersion)
        .where(
            FileVersion.file_id == file_id
        )
        .order_by(
            FileVersion.version_number.desc()
        )
        .limit(1)
    )

    if latest_version:

        next_version = (
            latest_version.version_number + 1
        )

    else:

        next_version = 1

    # --------------------------------------------------------
    # KEEP ORIGINAL LOGICAL FILE NAME
    # --------------------------------------------------------

    original_name = clean_original_filename(
        db_file.original_name
    )

    # Do NOT use uploaded_file.filename
    # as the logical name.
    #
    # This prevents:
    #
    # file.pdf.v4
    #
    # from becoming the new file name.

    # --------------------------------------------------------
    # UNIQUE STORAGE KEY
    # --------------------------------------------------------

    storage_name = (
        f"v{next_version}_"
        f"{uuid4()}_"
        f"{original_name}"
    )

    storage_key = (
        f"{user.id}/versions/"
        f"{file_id}/{storage_name}"
    )

    # --------------------------------------------------------
    # SAVE FILE THROUGH STORAGE ABSTRACTION
    # --------------------------------------------------------

    try:

        saved_key, file_size = (
            storage.save_upload(
                uploaded_file.file,
                storage_key,
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to save version: "
                f"{str(exc)}"
            ),
        )

    # --------------------------------------------------------
    # CONTENT TYPE
    # --------------------------------------------------------

    content_type = (
        uploaded_file.content_type
        or db_file.content_type
        or "application/octet-stream"
    )

    # --------------------------------------------------------
    # VERSION DATABASE RECORD
    # --------------------------------------------------------

    version = FileVersion(
        file_id=file_id,
        version_number=next_version,
        storage_key=saved_key,
        size=file_size,
    )

    db.add(version)

    # --------------------------------------------------------
    # UPDATE CURRENT FILE
    # --------------------------------------------------------

    db_file.storage_key = saved_key

    db_file.size = file_size

    db_file.content_type = content_type

    db_file.original_name = original_name

    db_file.name = original_name

    # --------------------------------------------------------
    # COMMIT
    # --------------------------------------------------------

    try:

        db.commit()

        db.refresh(version)

        db.refresh(db_file)

    except Exception:

        db.rollback()

        # Remove S3/local object if metadata
        # could not be committed.

        try:

            storage.delete(
                saved_key
            )

        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to save version metadata"
            ),
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "id": version.id,

        "file_id": version.file_id,

        "version_number":
            version.version_number,

        "size":
            version.size,

        "created_at":
            version.created_at,

        "message":
            (
                f"Version "
                f"{version.version_number} "
                f"uploaded successfully"
            ),
    }


# ============================================================
# GET VERSION HISTORY
# ============================================================

@router.get(
    "/{file_id}"
)
def get_versions(
    file_id: int,

    user=Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Return all versions of a file.
    """

    # --------------------------------------------------------
    # FIND FILE
    # --------------------------------------------------------

    db_file = db.get(
        DBFile,
        file_id,
    )

    if not db_file:

        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    # --------------------------------------------------------
    # OWNER CHECK
    # --------------------------------------------------------

    if db_file.owner_id != user.id:

        raise HTTPException(
            status_code=403,
            detail=(
                "You don't have permission "
                "to view versions"
            ),
        )

    # --------------------------------------------------------
    # GET VERSIONS
    # --------------------------------------------------------

    versions = db.scalars(
        select(FileVersion)
        .where(
            FileVersion.file_id == file_id
        )
        .order_by(
            FileVersion.version_number.desc()
        )
    ).all()

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return [
        {
            "id": version.id,

            "file_id": version.file_id,

            "version_number":
                version.version_number,

            "size":
                version.size,

            "created_at":
                version.created_at,

            "is_current":
                (
                    version.storage_key
                    == db_file.storage_key
                ),
        }

        for version in versions
    ]


# ============================================================
# DOWNLOAD SPECIFIC VERSION
# ============================================================

@router.get(
    "/{file_id}/{version_id}/download"
)
def download_version(
    file_id: int,

    version_id: int,

    user=Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Download ANY version directly.

    Restore is NOT required.
    """

    # --------------------------------------------------------
    # FIND FILE
    # --------------------------------------------------------

    db_file = db.get(
        DBFile,
        file_id,
    )

    if not db_file:

        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    # --------------------------------------------------------
    # OWNER CHECK
    # --------------------------------------------------------

    if db_file.owner_id != user.id:

        raise HTTPException(
            status_code=403,
            detail=(
                "You don't have permission "
                "to access versions"
            ),
        )

    # --------------------------------------------------------
    # FIND VERSION
    # --------------------------------------------------------

    version = db.scalar(
        select(FileVersion)
        .where(
            FileVersion.id == version_id,
            FileVersion.file_id == file_id,
        )
    )

    if not version:

        raise HTTPException(
            status_code=404,
            detail="Version not found",
        )

    # --------------------------------------------------------
    # STORAGE CHECK
    # --------------------------------------------------------

    if not storage.exists(
        version.storage_key
    ):

        raise HTTPException(
            status_code=404,
            detail="Version file not found",
        )

    # --------------------------------------------------------
    # DOWNLOAD NAME
    # --------------------------------------------------------

    download_name = make_version_filename(
        db_file.original_name,
        version.version_number,
    )

    # --------------------------------------------------------
    # S3
    # --------------------------------------------------------

    if storage.mode == "s3":

        try:

            file_stream = storage.download(
                version.storage_key
            )

            return StreamingResponse(
                file_stream,
                media_type=(
                    db_file.content_type
                    or "application/octet-stream"
                ),
                headers={
                    "Content-Disposition":
                        (
                            f'attachment; '
                            f'filename="{download_name}"'
                        )
                },
            )

        except Exception as exc:

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Failed to download version: "
                    f"{str(exc)}"
                ),
            )

    # --------------------------------------------------------
    # LOCAL STORAGE
    # --------------------------------------------------------

    return FileResponse(
        path=storage.get_path(
            version.storage_key
        ),
        filename=download_name,
        media_type=(
            db_file.content_type
            or "application/octet-stream"
        ),
    )


# ============================================================
# RESTORE VERSION
# ============================================================

@router.post(
    "/{file_id}/{version_id}/restore"
)
def restore_version(
    file_id: int,

    version_id: int,

    user=Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    ),
):
    """
    Restore an old version.

    IMPORTANT:

    Restore does NOT overwrite the old version.

    Instead it creates a NEW version.

    Example:

        v1
        v2
        v3 Current

    Restore v1:

        v1
        v2
        v3
        v4 Current
           ↑
        copy of v1
    """

    # --------------------------------------------------------
    # FIND FILE
    # --------------------------------------------------------

    db_file = db.get(
        DBFile,
        file_id,
    )

    if not db_file:

        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    # --------------------------------------------------------
    # OWNER CHECK
    # --------------------------------------------------------

    if db_file.owner_id != user.id:

        raise HTTPException(
            status_code=403,
            detail=(
                "Only the owner can "
                "restore versions"
            ),
        )

    # --------------------------------------------------------
    # TRASH CHECK
    # --------------------------------------------------------

    if db_file.deleted:

        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot restore a version "
                "of a file in Trash"
            ),
        )

    # --------------------------------------------------------
    # FIND VERSION
    # --------------------------------------------------------

    version = db.scalar(
        select(FileVersion)
        .where(
            FileVersion.id == version_id,
            FileVersion.file_id == file_id,
        )
    )

    if not version:

        raise HTTPException(
            status_code=404,
            detail="Version not found",
        )

    # --------------------------------------------------------
    # CHECK SOURCE OBJECT
    # --------------------------------------------------------

    # IMPORTANT:
    #
    # Do NOT use:
    #
    # Path(version.storage_key).exists()
    #
    # because the object may live in S3.

    if not storage.exists(
        version.storage_key
    ):

        raise HTTPException(
            status_code=404,
            detail="Version file not found",
        )

    # --------------------------------------------------------
    # FIND LATEST VERSION
    # --------------------------------------------------------

    latest_version = db.scalar(
        select(FileVersion)
        .where(
            FileVersion.file_id == file_id
        )
        .order_by(
            FileVersion.version_number.desc()
        )
        .limit(1)
    )

    if latest_version:

        next_version = (
            latest_version.version_number + 1
        )

    else:

        next_version = 1

    # --------------------------------------------------------
    # CLEAN ORIGINAL NAME
    # --------------------------------------------------------

    original_name = clean_original_filename(
        db_file.original_name
    )

    # --------------------------------------------------------
    # NEW STORAGE KEY
    # --------------------------------------------------------

    new_storage_name = (
        f"v{next_version}_"
        f"{uuid4()}_"
        f"{original_name}"
    )

    new_storage_key = (
        f"{user.id}/versions/"
        f"{file_id}/{new_storage_name}"
    )

    # --------------------------------------------------------
    # COPY VERSION INSIDE STORAGE
    # --------------------------------------------------------

    try:

        saved_key, restored_size = (
            storage.copy(
                version.storage_key,
                new_storage_key,
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to restore version: "
                f"{str(exc)}"
            ),
        )

    # --------------------------------------------------------
    # CREATE NEW VERSION
    # --------------------------------------------------------

    restored_version = FileVersion(
        file_id=file_id,

        version_number=next_version,

        storage_key=saved_key,

        size=restored_size,
    )

    db.add(
        restored_version
    )

    # --------------------------------------------------------
    # UPDATE CURRENT FILE
    # --------------------------------------------------------

    db_file.storage_key = saved_key

    db_file.size = restored_size

    # Keep the original:
    #
    # name
    # original_name
    # content_type
    #
    # unchanged.

    # --------------------------------------------------------
    # COMMIT
    # --------------------------------------------------------

    try:

        db.commit()

        db.refresh(
            restored_version
        )

        db.refresh(
            db_file
        )

    except Exception:

        db.rollback()

        # Database failed after the object
        # was already copied.

        try:

            storage.delete(
                saved_key
            )

        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail="Failed to restore version",
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "message":
            "Version restored successfully",

        "file_id":
            file_id,

        "restored_from_version":
            version.version_number,

        "new_version":
            restored_version.version_number,

        "version_id":
            restored_version.id,

        "storage_key":
            restored_version.storage_key,
    }