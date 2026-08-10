# CloudVault

A secure full-stack cloud file storage and sharing platform.

## Stack
- React + TypeScript + Vite
- Python 3.12 + FastAPI
- SQLAlchemy + PostgreSQL
- JWT authentication
- AWS S3 pre-signed URLs
- Redis (optional)
- Docker Compose

## MVP
- User registration/login
- JWT protected APIs
- Folder management
- File metadata management
- Local upload/download development mode
- S3 storage adapter
- File sharing and permissions
- Versioning
- Search and pagination
- Trash/restore

## Run locally

1. Copy `backend/.env.example` to `backend/.env`.
2. Start PostgreSQL and Redis:
   `docker compose up -d postgres redis`
3. Install backend dependencies:
   `cd backend && python -m venv .venv`
   `pip install -r requirements.txt`
4. Start API:
   `uvicorn app.main:app --reload`
5. Start frontend:
   `cd frontend && npm install && npm run dev`

API docs: http://localhost:8000/docs
Frontend: http://localhost:5173
