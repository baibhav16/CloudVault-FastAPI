from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class ShareCreate(BaseModel):
    email: EmailStr
    permission: str = "VIEWER"

    @field_validator("permission")
    @classmethod
    def validate_permission(cls, value: str):
        value = value.upper()

        if value not in {
            "VIEWER",
            "EDITOR",
        }:
            raise ValueError(
                "Permission must be VIEWER or EDITOR"
            )

        return value


class ShareResponse(BaseModel):
    id: int
    file_id: int
    shared_with_user_id: int
    permission: str

    class Config:
        from_attributes = True