from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from mmino.api.v1 import endpoints, websockets
from mmino.core.config import settings
from mmino.db.session import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    print("Database initialized")
    yield
    # Shutdown
    print("Shutting down")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:5173"], # Needs to be from settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "audio-api"}

# Include routers
app.include_router(endpoints.router, prefix=settings.API_V1_PREFIX)
app.include_router(websockets.router, prefix=settings.API_V1_PREFIX)