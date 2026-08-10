# API

Base URL: `/api/v1`

Auth:
- POST `/auth/register`
- POST `/auth/login`
- GET `/auth/me`

Files:
- GET `/files`
- POST `/files`
- POST `/files/{id}/upload-url`
- GET `/files/{id}/download-url`
- DELETE `/files/{id}`

Folders:
- GET `/folders`
- POST `/folders`

Sharing:
- POST `/shares/files/{file_id}`

Versions:
- GET `/versions/files/{file_id}`

Interactive API docs are available at `/docs`.
