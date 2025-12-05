"""
FastAPI main application for RFP Dashboard.
"""

from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.routes import (
    alerts,
    analytics,
    chat,
    compliance,
    copilot,
    discovery,
    documents,
    generation,
    jobs,
    pipeline,
    predictions,
    pricing,
    profiles,
    rag,
    rfps,
    saved_rfps,
    scraper,
    streaming,
    submissions,
)
from app.websockets import channels as websocket_channels
from app.websockets import websocket_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    import sys
    import traceback

    # Startup
    try:
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
    except Exception as e:
        print(f"ERROR during startup: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        # Don't crash - let the app start but log the error
        # This allows the health check to still work

    # Initialize ChromaDB RAG engine at startup (eager initialization)
    try:
        print("Initializing ChromaDB RAG engine...")
        from src.rag.chroma_rag_engine import get_rag_engine

        engine = get_rag_engine()
        stats = engine.get_statistics()
        print(f"RAG engine ready: {stats['total_documents']} documents")

        # Build from parquet if empty
        if stats["total_documents"] == 0:
            print("Empty collection, building from parquet files...")
            engine.build_index(force_rebuild=True)
            new_stats = engine.get_statistics()
            print(f"RAG build complete: {new_stats['total_documents']} documents")
    except Exception as e:
        print(f"WARNING: Failed to initialize RAG engine: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        # Don't crash - RAG is optional for basic functionality

    yield
    # Shutdown
    print("Shutting down application...")


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

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
app.include_router(
    discovery.router, prefix=f"{settings.API_V1_STR}/discovery", tags=["discovery"]
)
app.include_router(
    pipeline.router, prefix=f"{settings.API_V1_STR}/pipeline", tags=["pipeline"]
)
app.include_router(
    submissions.router,
    prefix=f"{settings.API_V1_STR}/submissions",
    tags=["submissions"],
)
app.include_router(
    predictions.router,
    prefix=f"{settings.API_V1_STR}/predictions",
    tags=["predictions"],
)
app.include_router(
    generation.router, prefix=f"{settings.API_V1_STR}/generation", tags=["generation"]
)
app.include_router(
    profiles.router, prefix=f"{settings.API_V1_STR}/profiles", tags=["profiles"]
)
app.include_router(
    scraper.router, prefix=f"{settings.API_V1_STR}/scraper", tags=["scraper"]
)
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])
app.include_router(
    copilot.router, prefix=f"{settings.API_V1_STR}/copilot", tags=["copilot"]
)
app.include_router(
    alerts.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["alerts"]
)
app.include_router(
    streaming.router, prefix=f"{settings.API_V1_STR}/streaming", tags=["streaming"]
)
app.include_router(jobs.router, prefix=f"{settings.API_V1_STR}/jobs", tags=["jobs"])
app.include_router(rag.router, prefix=f"{settings.API_V1_STR}/rag", tags=["rag"])
app.include_router(
    documents.router, prefix=f"{settings.API_V1_STR}/documents", tags=["documents"]
)
app.include_router(compliance.router, prefix=settings.API_V1_STR)
app.include_router(
    saved_rfps.router, prefix=settings.API_V1_STR, tags=["saved-rfps"]
)
app.include_router(
    analytics.router,
    prefix=f"{settings.API_V1_STR}/analytics",
    tags=["analytics"],
)
app.include_router(
    pricing.router,
    prefix=f"{settings.API_V1_STR}/pricing",
    tags=["pricing"],
)
app.include_router(websocket_router.router, prefix="/ws", tags=["websocket"])
app.include_router(
    websocket_channels.router, prefix="/ws/channels", tags=["websocket-channels"]
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RFP Bid Generation Dashboard API",
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/features")
async def get_features():
    """Get feature flags status."""
    from app.core.feature_flags import feature_flags

    return feature_flags.get_status()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
