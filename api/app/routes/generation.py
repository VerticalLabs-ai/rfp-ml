import logging
import os
import shutil
import sys
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, field_validator

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.core.config import settings

from src.bid_generation.style_manager import style_manager
from src.config.enhanced_bid_llm import EnhancedBidLLMManager

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy initialization to avoid startup failures
_llm_manager = None


def get_llm_manager():
    """Get or create LLM manager instance."""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = EnhancedBidLLMManager()
    return _llm_manager


class RefineRequest(BaseModel):
    text: str
    instruction: str
    context: str = ""

    @field_validator("text", "instruction")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("text")
    @classmethod
    def validate_text_length(cls, v: str) -> str:
        if len(v) > 50000:
            raise ValueError("Text exceeds maximum length of 50000 characters")
        return v

@router.post("/style/upload")
async def upload_style_reference(file: UploadFile = File(...)):
    """
    Upload a past proposal or reference document to train the 'Voice of the Customer' model.
    Supports .txt, .md (PDF/Docx support to be added via unstructured loader).
    """
    allowed_extensions = [".txt", ".md"]
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {allowed_extensions}")

    try:
        # Save temp file
        temp_dir = Path(settings.DATA_DIR) / "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = temp_dir / file.filename

        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Read text
        with open(temp_path, encoding="utf-8", errors="ignore") as f:
            text = f.read()

        # Ingest
        style_manager.ingest_file(text, file.filename)

        # Cleanup
        os.remove(temp_path)

        return {"message": f"Successfully ingested {file.filename}", "chars_processed": len(text)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.post("/refine")
async def refine_text(data: RefineRequest):
    """
    Refine a specific text segment using the LLM.
    Input: { "text": "...", "instruction": "Make it more persuasive", "context": "..." }
    """
    try:
        llm_manager = get_llm_manager()
        refined = llm_manager.refine_content(data.text, data.instruction, data.context)
        return {"refined_text": refined}
    except Exception as e:
        # Fallback mock if LLM fails or is offline
        logger.warning("LLM Refinement failed: %s", e)
        refined = f"[REFINED]: {data.text}\n(Applied: {data.instruction})"
        return {"refined_text": refined}
