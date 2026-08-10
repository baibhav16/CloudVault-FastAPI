from datetime import datetime

from pydantic import BaseModel, Field


class FileCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
    )

    original_name: str = Field(
        min_length=1,
        max_length=255,
    )

    folder_id: int | None = None

    size: int = Field(
        ge=0,
    )

    content_type: str = (
        "application/octet-stream"
    )


class FileResponse(BaseModel):
    id: int

    name: str

    original_name: str

    owner_id: int

    folder_id: int | None

    storage_key: str

    size: int

    content_type: str

    deleted: bool

    created_at: datetime

    updated_at: datetime

    # Current version number
    current_version: int = 1

    model_config = {
        "from_attributes": True
    }