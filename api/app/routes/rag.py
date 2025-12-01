"""
RAG (Retrieval-Augmented Generation) Management API.

Provides endpoints for:
- Checking RAG index status and health
- Triggering index rebuild
- Adding documents incrementally
"""
import logging
import os
import sys
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)
router = APIRouter()

# Global state for tracking build progress
_build_state = {
    "is_building": False,
    "progress": 0,
    "total": 0,
    "started_at": None,
    "completed_at": None,
    "error": None,
    "last_build_duration_seconds": None,
}


def _get_rag_engine():
    """Get or create RAG engine instance."""
    try:
        from src.rag.rag_engine import RAGEngine
        engine = RAGEngine()
        # Load existing index if available
        engine.build_index(force_rebuild=False)
        return engine
    except Exception as e:
        logger.error(f"Failed to get RAG engine: {e}")
        return None


class RAGStatusResponse(BaseModel):
    """Response model for RAG status."""
    is_available: bool
    is_building: bool
    build_progress: float = Field(description="Build progress 0-100")
    index_info: dict[str, Any] | None = None
    statistics: dict[str, Any] | None = None
    last_build: dict[str, Any] | None = None


class RAGHealthResponse(BaseModel):
    """Response model for RAG health check."""
    healthy: bool
    issues: list[str] = []
    recommendations: list[str] = []


class RebuildResponse(BaseModel):
    """Response for rebuild request."""
    status: str
    message: str
    job_id: str | None = None


class AddDocumentsRequest(BaseModel):
    """Request to add documents incrementally."""
    documents: list[str] = Field(..., min_length=1)
    document_ids: list[str] = Field(..., min_length=1)
    metadata: list[dict] = Field(default_factory=list)


class AddDocumentsResponse(BaseModel):
    """Response for add documents request."""
    added: int
    total_documents: int


def _run_rebuild_in_background(force: bool = True):
    """Background task to rebuild RAG index."""
    global _build_state
    _build_state["is_building"] = True
    _build_state["progress"] = 0
    _build_state["started_at"] = datetime.utcnow().isoformat()
    _build_state["error"] = None

    try:
        from src.rag.rag_engine import RAGEngine
        engine = RAGEngine()
        engine.build_index(force_rebuild=force)
        _build_state["progress"] = 100
        _build_state["completed_at"] = datetime.utcnow().isoformat()

        # Calculate duration
        if _build_state["started_at"]:
            start = datetime.fromisoformat(_build_state["started_at"])
            end = datetime.fromisoformat(_build_state["completed_at"])
            _build_state["last_build_duration_seconds"] = (end - start).total_seconds()

        logger.info("RAG index rebuild completed successfully")
    except Exception as e:
        _build_state["error"] = str(e)
        logger.error(f"RAG index rebuild failed: {e}")
    finally:
        _build_state["is_building"] = False


@router.get("/status", response_model=RAGStatusResponse)
async def get_rag_status() -> RAGStatusResponse:
    """
    Get current RAG index status.

    Returns detailed information about:
    - Whether RAG is available and ready
    - Build progress if currently building
    - Index statistics and file information
    """
    engine = _get_rag_engine()

    if engine is None:
        return RAGStatusResponse(
            is_available=False,
            is_building=_build_state["is_building"],
            build_progress=_build_state["progress"],
            last_build={
                "started_at": _build_state["started_at"],
                "completed_at": _build_state["completed_at"],
                "error": _build_state["error"],
                "duration_seconds": _build_state["last_build_duration_seconds"],
            } if _build_state["started_at"] else None,
        )

    try:
        index_info = engine.get_index_info()
        statistics = engine.get_statistics()
    except Exception as e:
        logger.warning(f"Failed to get index info: {e}")
        index_info = None
        statistics = None

    return RAGStatusResponse(
        is_available=engine.is_built,
        is_building=_build_state["is_building"],
        build_progress=_build_state["progress"] if _build_state["is_building"] else (100 if engine.is_built else 0),
        index_info=index_info,
        statistics=statistics,
        last_build={
            "started_at": _build_state["started_at"],
            "completed_at": _build_state["completed_at"],
            "error": _build_state["error"],
            "duration_seconds": _build_state["last_build_duration_seconds"],
        } if _build_state["started_at"] else None,
    )


@router.get("/health", response_model=RAGHealthResponse)
async def check_rag_health() -> RAGHealthResponse:
    """
    Check RAG index health.

    Validates:
    - Index files exist and are valid
    - Metadata is not corrupted
    - Embedding model is available
    """
    issues = []
    recommendations = []

    engine = _get_rag_engine()
    if engine is None:
        return RAGHealthResponse(
            healthy=False,
            issues=["RAG engine failed to initialize"],
            recommendations=["Check logs for initialization errors", "Verify dependencies are installed"],
        )

    try:
        index_info = engine.get_index_info()

        # Check FAISS index
        if not index_info["files"]["faiss_exists"]:
            issues.append("FAISS index file does not exist")
            recommendations.append("Run a full index rebuild")
        elif index_info["vectors"]["total"] == 0:
            issues.append("FAISS index has no vectors")
            recommendations.append("Rebuild index or add documents")

        # Check metadata
        if index_info["files"]["metadata_exists"] and not index_info["files"]["metadata_valid"]:
            issues.append("Metadata file is corrupted")
            recommendations.append("Rebuild index to regenerate metadata (now with atomic writes)")

        # Check for metadata mismatch
        if index_info["vectors"]["total"] != index_info["vectors"]["documents_with_metadata"]:
            issues.append(f"Metadata mismatch: {index_info['vectors']['total']} vectors but {index_info['vectors']['documents_with_metadata']} metadata entries")
            recommendations.append("Rebuild index to sync metadata with vectors")

        # Check embedding availability
        stats = engine.get_statistics()
        if not stats["embedding_available"]:
            issues.append("Embedding model not available")
            recommendations.append("Check sentence-transformers installation")

    except Exception as e:
        issues.append(f"Health check error: {str(e)}")
        recommendations.append("Check system logs for details")

    return RAGHealthResponse(
        healthy=len(issues) == 0,
        issues=issues,
        recommendations=recommendations,
    )


@router.post("/rebuild", response_model=RebuildResponse)
async def trigger_rebuild(
    background_tasks: BackgroundTasks,
    force: bool = True,
) -> RebuildResponse:
    """
    Trigger a RAG index rebuild.

    This runs in the background and may take significant time (~1 hour for large datasets).
    Use GET /rag/status to monitor progress.

    Args:
        force: If True, rebuild even if index exists. If False, only build if missing.
    """
    if _build_state["is_building"]:
        return RebuildResponse(
            status="already_running",
            message="A rebuild is already in progress. Check /rag/status for progress.",
        )

    # Start rebuild in background
    background_tasks.add_task(_run_rebuild_in_background, force)

    return RebuildResponse(
        status="started",
        message="RAG index rebuild started. This may take up to an hour for large datasets. Monitor progress at /rag/status.",
    )


@router.post("/add-documents", response_model=AddDocumentsResponse)
async def add_documents(request: AddDocumentsRequest) -> AddDocumentsResponse:
    """
    Add documents to the RAG index incrementally.

    This is much faster than a full rebuild when adding new documents.
    The index must already be built.
    """
    if _build_state["is_building"]:
        raise HTTPException(
            status_code=409,
            detail="Cannot add documents while index is being rebuilt",
        )

    engine = _get_rag_engine()
    if engine is None or not engine.is_built:
        raise HTTPException(
            status_code=400,
            detail="RAG index not available. Build the index first using POST /rag/rebuild",
        )

    # Validate input lengths match
    if len(request.documents) != len(request.document_ids):
        raise HTTPException(
            status_code=400,
            detail="documents and document_ids must have the same length",
        )

    if request.metadata and len(request.metadata) != len(request.documents):
        raise HTTPException(
            status_code=400,
            detail="metadata must have the same length as documents if provided",
        )

    # Use empty dicts if no metadata provided
    metadata = request.metadata if request.metadata else [{} for _ in request.documents]

    try:
        added = engine.add_documents(
            documents=request.documents,
            document_ids=request.document_ids,
            metadata=metadata,
        )

        stats = engine.get_statistics()
        return AddDocumentsResponse(
            added=added,
            total_documents=stats["total_vectors"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add documents: {str(e)}",
        )


@router.delete("/index")
async def delete_index() -> dict:
    """
    Delete the current RAG index.

    Use this to clean up before a fresh rebuild.
    """
    if _build_state["is_building"]:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete index while rebuild is in progress",
        )

    try:
        from src.config.paths import PathConfig
        index_path = PathConfig.EMBEDDINGS_DIR / "rag_index"

        deleted_files = []
        for suffix in [".faiss", "_metadata.json", "_tfidf.pkl", "_metadata.json.tmp"]:
            file_path = f"{index_path}{suffix}"
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_files.append(file_path)

        return {
            "status": "deleted",
            "deleted_files": deleted_files,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete index: {str(e)}",
        )
