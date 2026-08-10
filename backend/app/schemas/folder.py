from pydantic import BaseModel, Field


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_folder_id: int | None = None


class FolderResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    parent_folder_id: int | None

    model_config = {"from_attributes": True}
