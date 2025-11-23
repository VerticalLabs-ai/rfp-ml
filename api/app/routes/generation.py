from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List, Dict, Any
import shutil
import os
from pathlib import Path
import sys

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.bid_generation.style_manager import style_manager
from src.config.enhanced_bid_llm import EnhancedBidLLMManager
from app.core.config import settings

router = APIRouter()
llm_manager = EnhancedBidLLMManager()

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
        with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
            
        # Ingest
        style_manager.ingest_file(text, file.filename)
        
        # Cleanup
        os.remove(temp_path)
        
        return {"message": f"Successfully ingested {file.filename}", "chars_processed": len(text)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.post("/refine")
async def refine_text(data: Dict[str, str]):
    """
    Refine a specific text segment using the LLM.
    Input: { "text": "...", "instruction": "Make it more persuasive", "context": "..." }
    """
    text = data.get("text")
    instruction = data.get("instruction")
    context = data.get("context", "")
    
    if not text or not instruction:
         raise HTTPException(status_code=400, detail="Missing text or instruction")
         
    try:
        refined = llm_manager.refine_content(text, instruction, context)
        return {"refined_text": refined}
    except Exception as e:
        # Fallback mock if LLM fails or is offline
        print(f"LLM Refinement failed: {e}")
        refined = f"[REFINED]: {text}\n(Applied: {instruction})"
        return {"refined_text": refined}
