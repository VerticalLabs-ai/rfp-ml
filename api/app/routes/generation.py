"""
AI Writer / Proposal Copilot API endpoints.

Provides GovGPT-style AI writing assistance for proposal sections with
slash-command functionality, context-aware content generation, and
style-matched output.
"""

import logging
import os
import shutil
import sys
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator

# Add project root
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)

from app.core.config import settings
from app.dependencies import RFPDep

from src.bid_generation.style_manager import style_manager
from src.config.enhanced_bid_llm import EnhancedBidLLMManager

# Module-level File dependency for required file uploads
_REQUIRED_FILE = File(...)

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


class WriterCommand(str, Enum):
    """Available AI Writer slash commands matching GovGPT functionality."""

    EXECUTIVE_SUMMARY = "executive-summary"
    TECHNICAL_APPROACH = "technical-approach"
    PAST_PERFORMANCE = "past-performance"
    MANAGEMENT_APPROACH = "management-approach"
    STAFFING_PLAN = "staffing-plan"
    QUALITY_CONTROL = "quality-control"
    RISK_MITIGATION = "risk-mitigation"
    TRANSITION_PLAN = "transition-plan"
    COMPLIANCE_MATRIX = "compliance-matrix"
    PRICING_NARRATIVE = "pricing-narrative"
    COVER_LETTER = "cover-letter"
    CAPABILITY_STATEMENT = "capability-statement"


# Command templates and prompts for each section type
WRITER_COMMANDS = {
    WriterCommand.EXECUTIVE_SUMMARY: {
        "name": "Executive Summary",
        "description": "Generate a compelling executive summary for the proposal",
        "prompt_template": """Write a professional executive summary for a government proposal.

RFP: {rfp_title}
Agency: {agency}
Description: {rfp_description}
Additional Context: {user_context}

Create a 3-4 paragraph executive summary that:
1. Demonstrates understanding of the requirement
2. Highlights key qualifications and differentiators
3. States commitment and confidence in delivery
4. Includes relevant past performance highlights

Maintain a professional, confident tone. Maximum {max_words} words.""",
        "default_max_words": 400,
    },
    WriterCommand.TECHNICAL_APPROACH: {
        "name": "Technical Approach",
        "description": "Generate a detailed technical approach section",
        "prompt_template": """Write a technical approach section for a government proposal.

RFP: {rfp_title}
Agency: {agency}
Requirements: {rfp_description}
Additional Context: {user_context}

Create a comprehensive technical approach that includes:
1. Understanding of requirements
2. Proposed methodology and approach
3. Tools, technologies, and processes
4. Quality assurance measures
5. Deliverables and milestones

Use clear, technical language appropriate for evaluators. Maximum {max_words} words.""",
        "default_max_words": 600,
    },
    WriterCommand.PAST_PERFORMANCE: {
        "name": "Past Performance",
        "description": "Generate past performance narratives",
        "prompt_template": """Write a past performance section for a government proposal.

RFP: {rfp_title}
Agency: {agency}
Contract Type: {rfp_description}
Additional Context: {user_context}

Create past performance narratives that:
1. Describe 2-3 relevant contract examples
2. Include contract values, timeframes, and agencies
3. Highlight similarities to current requirement
4. Demonstrate successful outcomes and metrics
5. Reference positive CPARs or customer testimonials

Use the STAR format (Situation, Task, Action, Result). Maximum {max_words} words.""",
        "default_max_words": 500,
    },
    WriterCommand.MANAGEMENT_APPROACH: {
        "name": "Management Approach",
        "description": "Generate management approach and organizational structure",
        "prompt_template": """Write a management approach section for a government proposal.

RFP: {rfp_title}
Agency: {agency}
Scope: {rfp_description}
Additional Context: {user_context}

Create a management approach that covers:
1. Organizational structure and reporting
2. Key personnel roles and responsibilities
3. Communication and coordination plan
4. Performance monitoring and reporting
5. Contract management procedures

Include an organizational chart description. Maximum {max_words} words.""",
        "default_max_words": 450,
    },
    WriterCommand.STAFFING_PLAN: {
        "name": "Staffing Plan",
        "description": "Generate staffing and personnel plan",
        "prompt_template": """Write a staffing plan section for a government proposal.

RFP: {rfp_title}
Agency: {agency}
Requirements: {rfp_description}
Additional Context: {user_context}

Create a staffing plan that includes:
1. Key personnel qualifications
2. Staff categories and labor mix
3. Recruitment and retention strategies
4. Training and development
5. Contingency staffing plans

Align with labor category requirements. Maximum {max_words} words.""",
        "default_max_words": 400,
    },
    WriterCommand.QUALITY_CONTROL: {
        "name": "Quality Control Plan",
        "description": "Generate quality control and assurance plan",
        "prompt_template": """Write a quality control plan for a government proposal.

RFP: {rfp_title}
Agency: {agency}
Deliverables: {rfp_description}
Additional Context: {user_context}

Create a QC/QA plan that addresses:
1. Quality management approach
2. Inspection and testing procedures
3. Corrective action processes
4. Documentation and records
5. Continuous improvement methodology

Reference applicable standards (ISO, CMMI, etc.). Maximum {max_words} words.""",
        "default_max_words": 400,
    },
    WriterCommand.RISK_MITIGATION: {
        "name": "Risk Mitigation",
        "description": "Generate risk identification and mitigation plan",
        "prompt_template": """Write a risk mitigation section for a government proposal.

RFP: {rfp_title}
Agency: {agency}
Scope: {rfp_description}
Additional Context: {user_context}

Create a risk management plan that:
1. Identifies key technical, schedule, and cost risks
2. Assesses probability and impact
3. Proposes mitigation strategies
4. Defines monitoring and response procedures
5. Includes a risk matrix or summary

Use standard risk management terminology. Maximum {max_words} words.""",
        "default_max_words": 400,
    },
    WriterCommand.TRANSITION_PLAN: {
        "name": "Transition Plan",
        "description": "Generate transition-in and transition-out plans",
        "prompt_template": """Write a transition plan for a government proposal.

RFP: {rfp_title}
Agency: {agency}
Contract Details: {rfp_description}
Additional Context: {user_context}

Create a comprehensive transition plan covering:
1. Transition-in approach and timeline
2. Knowledge transfer procedures
3. Personnel onboarding
4. Systems and data migration
5. Transition-out planning for contract end

Include specific milestones and deliverables. Maximum {max_words} words.""",
        "default_max_words": 450,
    },
    WriterCommand.COMPLIANCE_MATRIX: {
        "name": "Compliance Matrix",
        "description": "Generate compliance matrix narrative",
        "prompt_template": """Write a compliance narrative for a government proposal.

RFP: {rfp_title}
Agency: {agency}
Requirements: {rfp_description}
Additional Context: {user_context}

Create a compliance narrative that:
1. Maps requirements to proposal sections
2. States compliance status for each requirement
3. Explains approach to meeting standards
4. Notes any exceptions or deviations
5. References supporting documentation

Use clear, direct compliance language. Maximum {max_words} words.""",
        "default_max_words": 350,
    },
    WriterCommand.PRICING_NARRATIVE: {
        "name": "Pricing Narrative",
        "description": "Generate pricing approach and basis of estimate",
        "prompt_template": """Write a pricing narrative for a government proposal.

RFP: {rfp_title}
Agency: {agency}
Contract Type: {rfp_description}
Additional Context: {user_context}

Create a pricing narrative that explains:
1. Pricing methodology and approach
2. Basis of estimate for key cost elements
3. Labor rate justification
4. Value proposition and cost efficiencies
5. Assumptions and exclusions

Maintain compliance with FAR pricing requirements. Maximum {max_words} words.""",
        "default_max_words": 400,
    },
    WriterCommand.COVER_LETTER: {
        "name": "Cover Letter",
        "description": "Generate professional proposal cover letter",
        "prompt_template": """Write a cover letter for a government proposal.

RFP: {rfp_title}
Agency: {agency}
Solicitation: {rfp_description}
Additional Context: {user_context}

Create a professional cover letter that:
1. References the solicitation number and title
2. Expresses interest and capability
3. Highlights key differentiators
4. States compliance with requirements
5. Provides point of contact information

Keep it concise and professional. Maximum {max_words} words.""",
        "default_max_words": 250,
    },
    WriterCommand.CAPABILITY_STATEMENT: {
        "name": "Capability Statement",
        "description": "Generate capability statement for the opportunity",
        "prompt_template": """Write a capability statement for a government opportunity.

RFP: {rfp_title}
Agency: {agency}
Requirements: {rfp_description}
Additional Context: {user_context}

Create a one-page capability statement including:
1. Company overview and core competencies
2. NAICS codes and contract vehicles
3. Past performance highlights
4. Differentiators and value proposition
5. Contact information and certifications

Format for easy scanning. Maximum {max_words} words.""",
        "default_max_words": 350,
    },
}


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


class AIWriterRequest(BaseModel):
    """Request for AI Writer command execution."""

    command: WriterCommand = Field(..., description="The writer command to execute")
    context: str = Field(
        default="", max_length=2000, description="Additional context or requirements"
    )
    max_words: int | None = Field(
        default=None, ge=50, le=2000, description="Maximum words for output"
    )
    tone: str = Field(
        default="professional",
        description="Writing tone: professional, formal, conversational",
    )
    include_citations: bool = Field(
        default=False, description="Include source citations if available"
    )


class AIWriterResponse(BaseModel):
    """Response from AI Writer command."""

    command: str
    section_name: str
    content: str
    word_count: int
    confidence_score: float
    generation_method: str
    rfp_id: str
    suggestions: list[str] = []


class ExpandRequest(BaseModel):
    """Request to expand a section or outline."""

    text: str = Field(..., min_length=10, max_length=5000)
    expansion_type: str = Field(
        default="detailed", description="Type: detailed, bullets, examples"
    )
    target_length: int = Field(default=300, ge=50, le=1000)


class SummarizeRequest(BaseModel):
    """Request to summarize content."""

    text: str = Field(..., min_length=50, max_length=10000)
    summary_type: str = Field(
        default="executive", description="Type: executive, bullets, technical"
    )
    max_length: int = Field(default=150, ge=50, le=500)


@router.post("/style/upload")
async def upload_style_reference(file: UploadFile = _REQUIRED_FILE):
    """
    Upload a past proposal or reference document to train the 'Voice of the Customer' model.
    Supports .txt, .md (PDF/Docx support to be added via unstructured loader).
    """
    allowed_extensions = [".txt", ".md"]
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {allowed_extensions}",
        )

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

        return {
            "message": f"Successfully ingested {file.filename}",
            "chars_processed": len(text),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e!s}") from e


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


# =============================================================================
# AI Writer / Proposal Copilot Endpoints (GovGPT Parity)
# =============================================================================


@router.get("/writer/commands")
async def list_writer_commands():
    """
    List all available AI Writer slash commands.

    Returns command names, descriptions, and default settings for
    frontend slash-command menu integration.
    """
    commands = []
    for cmd, config in WRITER_COMMANDS.items():
        commands.append(
            {
                "command": cmd.value,
                "name": config["name"],
                "description": config["description"],
                "default_max_words": config["default_max_words"],
                "shortcut": f"/{cmd.value}",
            }
        )
    return {"commands": commands, "total": len(commands)}


@router.post("/{rfp_id}/writer", response_model=AIWriterResponse)
async def execute_writer_command(rfp: RFPDep, request: AIWriterRequest):
    """
    Execute an AI Writer slash command for a specific RFP.

    Generates proposal section content based on the command type and RFP context.
    Supports all standard proposal sections with RAG-enhanced context retrieval.
    """
    import time

    start_time = time.time()

    command_config = WRITER_COMMANDS.get(request.command)
    if not command_config:
        raise HTTPException(
            status_code=400, detail=f"Unknown command: {request.command.value}"
        )

    max_words = request.max_words or command_config["default_max_words"]

    try:
        llm_manager = get_llm_manager()

        # Build prompt with RFP context
        prompt = command_config["prompt_template"].format(
            rfp_title=rfp.title,
            agency=rfp.agency or "Government Agency",
            rfp_description=(
                rfp.description[:1500] if rfp.description else "Not specified"
            ),
            user_context=request.context,
            max_words=max_words,
        )

        # Add tone modification if not professional
        if request.tone != "professional":
            tone_instructions = {
                "formal": "\n\nUse a formal, traditional government proposal style.",
                "conversational": "\n\nUse a more conversational yet professional tone.",
            }
            prompt += tone_instructions.get(request.tone, "")

        # Try to enhance with RAG context if available
        rag_context = ""
        if request.include_citations:
            try:
                from src.rag.chroma_rag_engine import get_rag_engine

                rag = get_rag_engine()
                if rag and rag.collection.count() > 0:
                    results = rag.retrieve(
                        f"{rfp.title} {request.command.value}", top_k=3
                    )
                    if results:
                        context_text = "\n\n".join(
                            [r["content"][:500] for r in results]
                        )
                        rag_context = "\n\nReference material:\n" + context_text[:1000]
                        prompt += rag_context
            except Exception as e:
                logger.debug("RAG context retrieval skipped: %s", e)

        # Generate content
        result = llm_manager.llm_manager.generate_text(
            prompt,
            task_type="bid_generation",
            max_tokens=max_words * 2,
            temperature=0.7,
        )

        content = (
            result.strip() if isinstance(result, str) else result.get("content", "")
        )
        word_count = len(content.split())

        # Calculate confidence
        confidence = 0.85 if word_count >= max_words * 0.5 else 0.6
        if any(
            term in content.lower()
            for term in ["experience", "qualified", "comply", "deliver"]
        ):
            confidence += 0.1
        confidence = min(confidence, 1.0)

        # Generate follow-up suggestions
        suggestions = _generate_suggestions(request.command, rfp)

        processing_time = int((time.time() - start_time) * 1000)
        logger.info("AI Writer generated %d words in %dms", word_count, processing_time)

        return AIWriterResponse(
            command=request.command.value,
            section_name=command_config["name"],
            content=content,
            word_count=word_count,
            confidence_score=round(confidence, 2),
            generation_method="llm",
            rfp_id=rfp.rfp_id,
            suggestions=suggestions,
        )

    except Exception as e:
        logger.error("AI Writer error for %s: %s", request.command.value, e)
        # Return fallback content
        fallback_content = _generate_fallback_content(request.command, rfp, max_words)
        return AIWriterResponse(
            command=request.command.value,
            section_name=command_config["name"],
            content=fallback_content,
            word_count=len(fallback_content.split()),
            confidence_score=0.5,
            generation_method="template",
            rfp_id=rfp.rfp_id,
            suggestions=[],
        )


@router.post("/{rfp_id}/writer/expand")
async def expand_content(rfp: RFPDep, request: ExpandRequest):
    """
    Expand a section outline or brief text into detailed content.

    Takes existing text and expands it based on the expansion type:
    - detailed: Full prose expansion
    - bullets: Expand into bullet points
    - examples: Add concrete examples
    """
    try:
        llm_manager = get_llm_manager()

        expansion_prompts = {
            "detailed": f"""Expand this outline into detailed prose for a government proposal:

{request.text}

RFP Context: {rfp.title}
Target length: approximately {request.target_length} words.

Expanded content:""",
            "bullets": f"""Expand this content into detailed bullet points for a government proposal:

{request.text}

RFP Context: {rfp.title}
Create {request.target_length // 50} detailed bullet points.

Bullet points:""",
            "examples": f"""Add concrete examples to this proposal content:

{request.text}

RFP Context: {rfp.title}
Add 2-3 specific examples that demonstrate capability. Target: {request.target_length} words.

With examples:""",
        }

        prompt = expansion_prompts.get(
            request.expansion_type, expansion_prompts["detailed"]
        )

        result = llm_manager.llm_manager.generate_text(
            prompt,
            task_type="bid_generation",
            max_tokens=request.target_length * 2,
            temperature=0.7,
        )

        expanded = (
            result.strip() if isinstance(result, str) else result.get("content", "")
        )

        return {
            "original_text": request.text,
            "expanded_text": expanded,
            "expansion_type": request.expansion_type,
            "word_count": len(expanded.split()),
            "rfp_id": rfp.rfp_id,
        }

    except Exception as e:
        logger.error("Content expansion failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Expansion failed: {e!s}") from e


@router.post("/{rfp_id}/writer/summarize")
async def summarize_content(rfp: RFPDep, request: SummarizeRequest):
    """
    Summarize proposal content.

    Creates condensed versions of proposal text:
    - executive: Executive-style summary
    - bullets: Key points as bullets
    - technical: Technical summary preserving key details
    """
    try:
        llm_manager = get_llm_manager()

        summary_prompts = {
            "executive": f"""Create an executive summary of this proposal content:

{request.text}

RFP: {rfp.title}
Maximum {request.max_length} words. Focus on key value propositions and outcomes.

Executive Summary:""",
            "bullets": f"""Summarize this proposal content as key bullet points:

{request.text}

RFP: {rfp.title}
Create {request.max_length // 30} key points.

Key Points:""",
            "technical": f"""Create a technical summary of this proposal content:

{request.text}

RFP: {rfp.title}
Maximum {request.max_length} words. Preserve technical details and specifications.

Technical Summary:""",
        }

        prompt = summary_prompts.get(request.summary_type, summary_prompts["executive"])

        result = llm_manager.llm_manager.generate_text(
            prompt,
            task_type="bid_generation",
            max_tokens=request.max_length * 2,
            temperature=0.5,
        )

        summary = (
            result.strip() if isinstance(result, str) else result.get("content", "")
        )

        return {
            "original_length": len(request.text.split()),
            "summary": summary,
            "summary_type": request.summary_type,
            "summary_length": len(summary.split()),
            "compression_ratio": round(
                len(summary.split()) / len(request.text.split()), 2
            ),
            "rfp_id": rfp.rfp_id,
        }

    except Exception as e:
        logger.error("Content summarization failed: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Summarization failed: {e!s}"
        ) from e


@router.post("/{rfp_id}/writer/improve")
async def improve_content(rfp: RFPDep, data: RefineRequest):
    """
    Improve existing proposal content with specific instructions.

    Alias for /refine but RFP-context aware. Supports instructions like:
    - "Make more persuasive"
    - "Add compliance language"
    - "Strengthen technical details"
    - "Add metrics and specifics"
    """
    try:
        llm_manager = get_llm_manager()

        prompt = f"""You are a government proposal expert. Improve this content:

Original:
{data.text}

RFP: {rfp.title}
Agency: {rfp.agency or 'Government Agency'}
Instruction: {data.instruction}
{f'Additional Context: {data.context}' if data.context else ''}

Provide the improved version maintaining the same structure but enhancing quality:

Improved:"""

        result = llm_manager.llm_manager.generate_text(
            prompt,
            task_type="refinement",
            max_tokens=len(data.text.split()) * 2 + 200,
            temperature=0.7,
        )

        improved = (
            result.strip() if isinstance(result, str) else result.get("content", "")
        )

        return {
            "original_text": data.text,
            "improved_text": improved,
            "instruction": data.instruction,
            "rfp_id": rfp.rfp_id,
            "word_count_change": len(improved.split()) - len(data.text.split()),
        }

    except Exception as e:
        logger.error("Content improvement failed: %s", e)
        # Fallback
        return {
            "original_text": data.text,
            "improved_text": data.text,
            "instruction": data.instruction,
            "rfp_id": rfp.rfp_id,
            "word_count_change": 0,
            "error": str(e),
        }


def _generate_suggestions(command: WriterCommand, rfp: Any) -> list[str]:
    """Generate follow-up command suggestions based on current command."""
    suggestion_map = {
        WriterCommand.EXECUTIVE_SUMMARY: [
            "Try /technical-approach next",
            "Add /past-performance to strengthen credibility",
            "Consider /cover-letter for submission",
        ],
        WriterCommand.TECHNICAL_APPROACH: [
            "Add /quality-control for completeness",
            "Include /risk-mitigation section",
            "Generate /staffing-plan for resources",
        ],
        WriterCommand.PAST_PERFORMANCE: [
            "Add /capability-statement",
            "Consider /management-approach",
            "Include specific metrics and outcomes",
        ],
        WriterCommand.MANAGEMENT_APPROACH: [
            "Add /staffing-plan details",
            "Include /quality-control procedures",
            "Consider /transition-plan",
        ],
    }
    return suggestion_map.get(command, ["Review and customize the generated content"])


def _generate_fallback_content(command: WriterCommand, rfp: Any, max_words: int) -> str:
    """Generate template-based fallback content when LLM fails."""
    fallbacks = {
        WriterCommand.EXECUTIVE_SUMMARY: f"""
Our team is pleased to submit this proposal in response to {rfp.title}.

With extensive experience in similar contracts, we are uniquely qualified to meet
{rfp.agency or 'the agency'}'s requirements. Our approach combines proven methodologies,
qualified personnel, and a commitment to excellence that ensures successful delivery.

We understand the critical nature of this requirement and are prepared to deliver
exceptional results while maintaining full compliance with all specifications. Our team
looks forward to the opportunity to serve {rfp.agency or 'your agency'}.
        """,
        WriterCommand.TECHNICAL_APPROACH: f"""
Our technical approach for {rfp.title} is designed to meet all requirements efficiently and effectively.

METHODOLOGY:
1. Requirements Analysis - Comprehensive review of all specifications
2. Planning - Detailed project schedule and resource allocation
3. Execution - Systematic implementation with quality checkpoints
4. Delivery - On-time completion with full documentation

QUALITY ASSURANCE:
Our QA processes ensure all deliverables meet or exceed standards.

RISK MANAGEMENT:
Proactive identification and mitigation of potential issues ensures project success.
        """,
    }

    content = fallbacks.get(command, f"[Generated content for {command.value} section]")
    # Trim to max words
    words = content.split()
    if len(words) > max_words:
        content = " ".join(words[:max_words])
    return content.strip()
