from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import Base, engine
from app.models import user, folder, file, share, version
from app.api.routes import auth, files, folders, shares, versions


# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CloudVault API",
    version="1.0.0",
    description="Secure cloud file storage and sharing API",
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

app.include_router(
    files.router,
    prefix="/api/v1/files",
    tags=["Files"],
)

app.include_router(
    folders.router,
    prefix="/api/v1/folders",
    tags=["Folders"],
)

app.include_router(
    shares.router,
    prefix="/api/v1/shares",
    tags=["Sharing"],
)

app.include_router(
    versions.router,
    prefix="/api/v1/versions",
    tags=["Versions"],
)


@app.get("/")
def root():
    return {
        "message": "Welcome to CloudVault API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "cloudvault",
    }