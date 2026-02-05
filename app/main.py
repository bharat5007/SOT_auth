"""
FastAPI Auth Microservice - Main Application Entry
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .database import engine, Base
from .routes import auth
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup: Create tables (skip if database not available)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"⚠️ Database initialization failed: {str(e)}")
        raise Exception(str(e))

    yield

    # Shutdown: Cleanup if needed
    try:
        await engine.dispose()
    except Exception:
        pass


app = FastAPI(
    title=settings.APP_NAME,
    description="JWT Authentication Microservice with FastAPI",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"service": settings.APP_NAME, "status": "healthy", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check for load balancers"""
    return {"status": "ok"}
