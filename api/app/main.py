"""
FastAPI main application for RFP Dashboard.
"""
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.routes import alerts, chat, generation, pipeline, predictions, profiles, rfps, scraper, submissions
from app.websockets import websocket_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Initializing database...")
    init_db()
    print("Database initialized successfully")

    # Run seeds
    print("Running database seeds...")
    from app.core.database import SessionLocal
    from app.core.seed import run_seeds
    with SessionLocal() as db:
        run_seeds(db)
    print("Database seeds complete")

    yield
    # Shutdown
    print("Shutting down application...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rfps.router, prefix=f"{settings.API_V1_STR}/rfps", tags=["rfps"])
app.include_router(pipeline.router, prefix=f"{settings.API_V1_STR}/pipeline", tags=["pipeline"])
app.include_router(submissions.router, prefix=f"{settings.API_V1_STR}/submissions", tags=["submissions"])
app.include_router(predictions.router, prefix=f"{settings.API_V1_STR}/predictions", tags=["predictions"])
app.include_router(generation.router, prefix=f"{settings.API_V1_STR}/generation", tags=["generation"])
app.include_router(profiles.router, prefix=f"{settings.API_V1_STR}/profiles", tags=["profiles"])
app.include_router(scraper.router, prefix=f"{settings.API_V1_STR}/scraper", tags=["scraper"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["alerts"])
app.include_router(websocket_router.router, prefix="/ws", tags=["websocket"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RFP Bid Generation Dashboard API",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
