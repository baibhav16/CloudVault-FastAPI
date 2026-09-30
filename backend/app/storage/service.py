from app.core.config import settings
from app.storage.local import LocalStorage
from app.storage.s3 import S3Storage


if settings.storage_mode.lower() == "s3":
    storage = S3Storage()
    storage.mode = "s3"
else:
    storage = LocalStorage(settings.local_storage_path)
    storage.mode = "local"
