# CloudVault Architecture

React/TypeScript communicates with FastAPI REST APIs. PostgreSQL stores users, folders, file metadata, sharing permissions and versions. Actual file objects are stored in S3 in production. The backend generates short-lived S3 pre-signed URLs so large files can move directly between the browser and S3.

Core flow:

Browser -> FastAPI -> authorization/metadata -> PostgreSQL
Browser -> pre-signed URL -> S3

The code uses a storage-provider abstraction so local development can be separated from AWS storage.
