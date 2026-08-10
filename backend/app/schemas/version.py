from datetime import datetime
from pydantic import BaseModel


class VersionResponse(BaseModel):
    id: int
    file_id: int
    version_number: int
    storage_key: str
    size: int
    created_at: datetime

    model_config = {"from_attributes": True}
