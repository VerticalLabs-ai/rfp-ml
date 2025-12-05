"""
Proposal Copilot API endpoints.

Provides AI-assisted proposal writing with section-by-section generation,
compliance checking, draft management, and slash command functionality.
"""
import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import anthropic
from app.dependencies import DBDep, RFPDep
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class SectionContent(BaseModel):
    """Content for a single proposal section."""
    content: str = ""


class DraftSaveRequest(BaseModel):
    """Request to save a proposal draft."""
    sections: dict[str, str] = Field(..., description="Section ID to content mapping")


class ComplianceCheckRequest(BaseModel):
    """Request to check compliance of proposal sections."""
    sections: dict[str, SectionContent] = Field(..., description="Section ID to content mapping")


class ComplianceIssue(BaseModel):
    """A compliance issue found during checking."""
    severity: str  # "error", "warning", "info"
    message: str
    section: str | None = None
    requirement: str | None = None


class ComplianceCheckResponse(BaseModel):
    """Response from compliance check."""
    score: float = Field(..., description="Overall compliance score (0-100)")
    issues: list[ComplianceIssue] = Field(default_factory=list)
    section_scores: dict[str, float] = Field(default_factory=dict)


class DraftResponse(BaseModel):
    """Response from draft operations."""
    rfp_id: str
    saved_at: str
    sections: dict[str, str]
    status: str


class SlashCommand(str, Enum):
    """Available slash commands for the editor."""
    WRITE = "write"           # Generate new content
    EXPAND = "expand"         # Expand selected text
    SUMMARIZE = "summarize"   # Summarize selected text
    BULLETS = "bullets"       # Convert to bullet points
    PARAGRAPH = "paragraph"   # Convert bullets to paragraph
    FORMAL = "formal"         # Make tone more formal
    SIMPLIFY = "simplify"     # Simplify language
    REQUIREMENTS = "requirements"  # Extract requirements
    COMPLIANCE = "compliance" # Add compliance language
    SIMILAR = "similar"       # Find similar past performance
    CITE = "cite"             # Add citation format
    TABLE = "table"           # Convert to table format
    HEADING = "heading"       # Add section heading


class CommandRequest(BaseModel):
    """Request to execute a slash command."""
    command: SlashCommand
    selected_text: str = ""  # Text selected in editor (for transform commands)
    context: str = ""        # Surrounding content for context
    section_id: str = ""     # Current proposal section
    custom_prompt: str = ""  # For custom commands


class CommandResponse(BaseModel):
    """Non-streaming command response."""
    result: str
    command: str
    tokens_used: int = 0


@router.post("/{rfp_id}/draft", response_model=DraftResponse)
async def save_draft(rfp: RFPDep, request: DraftSaveRequest, db: DBDep):
    """
    Save a proposal draft for an RFP.

    Saves the current state of all proposal sections to the database.
    """
    from app.models.database import BidDocument
    import uuid

    try:
        # Check if bid document exists
        existing = db.query(BidDocument).filter(
            BidDocument.rfp_id == rfp.id
        ).first()

        if existing:
            # Update existing
            existing.content_json = {"sections": request.sections}
            existing.updated_at = datetime.now(timezone.utc)
            existing.status = "draft"
        else:
            # Create new
            bid_doc = BidDocument(
                rfp_id=rfp.id,
                document_id=f"bid-{uuid.uuid4().hex[:8]}",
                content_json={"sections": request.sections},
                status="draft",
            )
            db.add(bid_doc)

        db.commit()

        return DraftResponse(
            rfp_id=rfp.rfp_id,
            saved_at=datetime.now(timezone.utc).isoformat(),
            sections=request.sections,
            status="draft",
        )

    except Exception as e:
        logger.exception(f"Failed to save draft for RFP {rfp.rfp_id}")
        raise HTTPException(status_code=500, detail="Failed to save draft") from e


@router.get("/{rfp_id}/draft", response_model=DraftResponse)
async def get_draft(rfp: RFPDep, db: DBDep):
    """
    Get the current draft for an RFP.
    """
    from app.models.database import BidDocument

    bid_doc = db.query(BidDocument).filter(
        BidDocument.rfp_id == rfp.id
    ).first()

    if not bid_doc or not bid_doc.content_json:
        return DraftResponse(
            rfp_id=rfp.rfp_id,
            saved_at=datetime.now(timezone.utc).isoformat(),
            sections={},
            status="empty",
        )

    return DraftResponse(
        rfp_id=rfp.rfp_id,
        saved_at=bid_doc.updated_at.isoformat() if bid_doc.updated_at else datetime.now(timezone.utc).isoformat(),
        sections=bid_doc.content_json.get("sections", {}),
        status=bid_doc.status or "draft",
    )


@router.post("/{rfp_id}/compliance-check", response_model=ComplianceCheckResponse)
async def check_compliance(rfp: RFPDep, request: ComplianceCheckRequest):
    """
    Check proposal compliance against RFP requirements.

    Uses a combination of rule-based checks and LLM analysis for:
    - Required content coverage
    - Missing mandatory elements
    - Word count requirements
    - RFP-specific requirement alignment
    - Regulatory compliance
    """
    try:
        issues: list[ComplianceIssue] = []
        section_scores: dict[str, float] = {}

        # Required sections and their minimum word counts
        required_sections = {
            "executive_summary": {"min_words": 200, "required": True},
            "technical_approach": {"min_words": 500, "required": True},
            "management_approach": {"min_words": 300, "required": True},
            "past_performance": {"min_words": 200, "required": True},
            "compliance_matrix": {"min_words": 100, "required": True},
            "staffing_plan": {"min_words": 150, "required": False},
            "quality_assurance": {"min_words": 100, "required": False},
            "risk_mitigation": {"min_words": 100, "required": False},
        }

        # Key phrases that should be addressed
        key_phrases_by_section = {
            "executive_summary": ["value proposition", "qualifications", "approach", "benefits"],
            "technical_approach": ["methodology", "solution", "technology", "implementation"],
            "management_approach": ["project management", "communication", "reporting", "governance"],
            "past_performance": ["contract", "client", "results", "similar"],
            "compliance_matrix": ["requirement", "compliance", "response"],
        }

        total_score = 0
        section_count = 0

        for section_id, config in required_sections.items():
            section_data = request.sections.get(section_id)
            content = section_data.content if section_data else ""
            word_count = len(content.split()) if content else 0

            score = 0

            # Check if required section is empty
            if config["required"] and word_count == 0:
                issues.append(ComplianceIssue(
                    severity="error",
                    message=f"Required section '{section_id.replace('_', ' ').title()}' is empty",
                    section=section_id,
                ))
            elif word_count > 0:
                # Word count scoring
                min_words = config["min_words"]
                if word_count >= min_words:
                    score += 50
                elif word_count >= min_words * 0.5:
                    score += 25
                    issues.append(ComplianceIssue(
                        severity="warning",
                        message=f"Section '{section_id.replace('_', ' ').title()}' is below recommended word count ({word_count}/{min_words} words)",
                        section=section_id,
                    ))
                else:
                    issues.append(ComplianceIssue(
                        severity="warning",
                        message=f"Section '{section_id.replace('_', ' ').title()}' needs more content ({word_count}/{min_words} words)",
                        section=section_id,
                    ))

                # Key phrase coverage
                key_phrases = key_phrases_by_section.get(section_id, [])
                content_lower = content.lower()
                phrases_found = sum(1 for phrase in key_phrases if phrase in content_lower)
                if key_phrases:
                    phrase_coverage = phrases_found / len(key_phrases)
                    score += phrase_coverage * 50

                    missing_phrases = [p for p in key_phrases if p not in content_lower]
                    if missing_phrases and phrase_coverage < 0.75:
                        issues.append(ComplianceIssue(
                            severity="info",
                            message=f"Consider addressing: {', '.join(missing_phrases[:3])}",
                            section=section_id,
                        ))

            section_scores[section_id] = round(score, 1)
            if config["required"]:
                total_score += score
                section_count += 1

        # Calculate overall score from rule-based checks
        rule_based_score = round(total_score / section_count, 1) if section_count > 0 else 0

        # Add RFP-specific checks
        all_content = " ".join([
            s.content for s in request.sections.values() if s.content
        ]).lower()

        if rfp.naics_code and rule_based_score > 0:
            if rfp.naics_code not in all_content:
                issues.append(ComplianceIssue(
                    severity="info",
                    message=f"Consider referencing NAICS code {rfp.naics_code} in your proposal",
                ))

        # LLM-enhanced compliance check (if content exists)
        llm_issues = []
        llm_score_adjustment = 0

        if rule_based_score > 20 and len(all_content) > 200:
            try:
                import anthropic
                import os

                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    client = anthropic.Anthropic(api_key=api_key)

                    # Build context for LLM
                    rfp_context = f"""RFP Title: {rfp.title}
Agency: {rfp.agency or 'Not specified'}
Description: {rfp.description or 'Not available'}
NAICS Code: {rfp.naics_code or 'Not specified'}
Category: {rfp.category or 'General'}
Estimated Value: {f'${rfp.estimated_value:,.0f}' if rfp.estimated_value else 'Not specified'}"""

                    # Build proposal summary
                    proposal_summary = "\n\n".join([
                        f"## {section_id.replace('_', ' ').title()}\n{data.content[:500]}..."
                        for section_id, data in request.sections.items()
                        if data.content and len(data.content) > 50
                    ][:5])

                    prompt = f"""Analyze this government proposal for compliance issues. Be concise.

RFP DETAILS:
{rfp_context}

PROPOSAL SECTIONS (excerpts):
{proposal_summary}

Identify 2-4 specific compliance concerns or improvements. For each, provide:
1. Severity: ERROR, WARNING, or INFO
2. Brief issue description (one sentence)
3. Which section it affects (if applicable)

Format each issue on one line as: SEVERITY|description|section
Example: WARNING|Missing security clearance requirements|technical_approach

Only output the issues, no other text."""

                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=500,
                        messages=[{"role": "user", "content": prompt}]
                    )

                    llm_response = response.content[0].text.strip()

                    # Parse LLM issues
                    for line in llm_response.split("\n"):
                        line = line.strip()
                        if "|" in line:
                            parts = line.split("|")
                            if len(parts) >= 2:
                                severity = parts[0].strip().lower()
                                message = parts[1].strip()
                                section = parts[2].strip() if len(parts) > 2 else None

                                if severity in ["error", "warning", "info"]:
                                    llm_issues.append(ComplianceIssue(
                                        severity=severity,
                                        message=f"[AI] {message}",
                                        section=section if section and section in required_sections else None,
                                    ))

                    # Adjust score based on LLM issues
                    error_count = sum(1 for i in llm_issues if i.severity == "error")
                    warning_count = sum(1 for i in llm_issues if i.severity == "warning")
                    llm_score_adjustment = -(error_count * 10 + warning_count * 5)

            except Exception as e:
                logger.warning(f"LLM compliance check failed (falling back to rules only): {e}")

        # Combine all issues
        issues.extend(llm_issues)

        # Calculate final score
        overall_score = max(0, min(100, rule_based_score + llm_score_adjustment))

        return ComplianceCheckResponse(
            score=overall_score,
            issues=issues,
            section_scores=section_scores,
        )

    except Exception as e:
        logger.exception(f"Compliance check failed for RFP {rfp.rfp_id}")
        raise HTTPException(status_code=500, detail="Compliance check failed") from e


@router.get("/{rfp_id}/suggestions")
async def get_section_suggestions(
    rfp: RFPDep,
    section: str,
):
    """
    Get AI suggestions for improving a proposal section.

    Returns contextual suggestions based on the RFP requirements
    and the current section.
    """
    suggestions_map = {
        "executive_summary": [
            "Open with a compelling value proposition that addresses the agency's core need",
            "Highlight 2-3 key differentiators that set your company apart",
            "Include a brief overview of your approach and methodology",
            "Mention relevant past performance with similar agencies",
            "Close with a strong compliance statement",
        ],
        "technical_approach": [
            "Start with your understanding of the technical requirements",
            "Describe your methodology framework (Agile, Waterfall, etc.)",
            "Include specific technologies and tools you'll use",
            "Address how you'll handle technical risks",
            "Provide a high-level architecture or solution diagram reference",
        ],
        "management_approach": [
            "Define clear roles and responsibilities",
            "Describe your communication and reporting cadence",
            "Include your quality management processes",
            "Address change management procedures",
            "Mention relevant certifications (ISO, CMMI, etc.)",
        ],
        "past_performance": [
            "Focus on contracts similar in size and scope",
            "Include specific metrics and outcomes",
            "Highlight work with similar agencies or in the same industry",
            "Address any lessons learned that apply",
            "Provide contact information for references",
        ],
        "compliance_matrix": [
            "Map each RFP requirement to a response",
            "Use clear compliance language (Compliant, Partial, Exception)",
            "Reference proposal sections for detailed responses",
            "Highlight where you exceed requirements",
            "Note any clarifications or assumptions",
        ],
    }

    default_suggestions = [
        "Review the RFP requirements carefully before writing",
        "Use clear, concise language",
        "Include specific examples and evidence",
        "Address evaluation criteria directly",
        "Proofread for consistency and accuracy",
    ]

    return {
        "rfp_id": rfp.rfp_id,
        "section": section,
        "suggestions": suggestions_map.get(section, default_suggestions),
    }


@router.post("/{rfp_id}/generate-outline")
async def generate_proposal_outline(rfp: RFPDep):
    """
    Generate a proposal outline based on the RFP.

    Creates section headers and key points to address.
    """
    try:
        from src.config.llm_adapter import create_llm_interface

        llm = create_llm_interface()

        prompt = f"""Generate a proposal outline for the following RFP:

Title: {rfp.title}
Agency: {rfp.agency or 'Not specified'}
Description: {rfp.description or 'Not available'}
NAICS Code: {rfp.naics_code or 'Not specified'}
Category: {rfp.category or 'General'}

Create a structured outline with:
1. Executive Summary key points
2. Technical Approach sections
3. Management Approach elements
4. Past Performance focus areas
5. Compliance considerations

Format as a clear, actionable outline."""

        result = llm.generate_text(prompt, use_case="outline")
        outline = result.get("content", result.get("text", ""))

        return {
            "rfp_id": rfp.rfp_id,
            "outline": outline,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.exception(f"Failed to generate outline for RFP {rfp.rfp_id}")
        raise HTTPException(status_code=500, detail="Outline generation failed") from e


# Slash command prompts for non-streaming commands
NON_STREAMING_PROMPTS = {
    SlashCommand.BULLETS: "Convert the following text into clear, concise bullet points. Only output the bullet points, no other text:\n\n{text}",
    SlashCommand.PARAGRAPH: "Convert these bullet points into a well-written, cohesive paragraph. Only output the paragraph, no other text:\n\n{text}",
    SlashCommand.FORMAL: "Rewrite this text in a more formal, professional tone suitable for a government proposal. Only output the rewritten text, no other text:\n\n{text}",
    SlashCommand.SIMPLIFY: "Simplify this text to make it clearer and easier to understand while preserving the key information. Only output the simplified text, no other text:\n\n{text}",
    SlashCommand.HEADING: "Generate an appropriate section heading for this content. Only output the heading, no other text:\n\n{text}",
}


@router.post("/{rfp_id}/command", response_model=CommandResponse)
async def execute_command(rfp: RFPDep, request: CommandRequest):
    """
    Execute a slash command on selected text.

    For non-streaming quick commands like formatting.
    """
    prompt_template = NON_STREAMING_PROMPTS.get(request.command)
    if not prompt_template:
        raise HTTPException(
            status_code=400,
            detail=f"Command '{request.command}' requires streaming. Use /command/stream endpoint."
        )

    text = request.selected_text or request.context
    if not text:
        raise HTTPException(status_code=400, detail="No text provided for command")

    prompt = prompt_template.format(text=text)

    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Anthropic API key not configured")

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        return CommandResponse(
            result=response.content[0].text,
            command=request.command.value,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
        )
    except anthropic.APIError as e:
        logger.exception(f"Anthropic API error for command {request.command}")
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}") from e
    except Exception as e:
        logger.exception(f"Command execution failed: {request.command}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{rfp_id}/ai-action")
async def execute_ai_action(
    rfp_id: int,
    request: dict,
    db: DBDep,
):
    """Execute an AI-powered text transformation or analysis action."""
    action_id = request.get("action_id")
    selected_text = request.get("selected_text", "")
    full_content = request.get("full_content", "")

    # Validate action
    valid_actions = [
        "improve", "expand", "simplify", "formalize",
        "grammar", "readability", "passive", "jargon"
    ]
    if action_id not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action_id}")

    # Get RFP context
    from app.models.database import RFPOpportunity
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Build prompts based on action
    prompts = {
        "improve": f"""Improve the following text for clarity, impact, and professionalism.
Keep the same meaning but make it more compelling for a government proposal:

Text to improve:
{selected_text}

Return only the improved text, no explanations.""",

        "expand": f"""Expand the following text with more detail and supporting information.
Add relevant technical details and professional language suitable for a government proposal:

Text to expand:
{selected_text}

Return only the expanded text, no explanations.""",

        "simplify": f"""Simplify the following text to make it easier to understand.
Use clearer language while maintaining professionalism:

Text to simplify:
{selected_text}

Return only the simplified text, no explanations.""",

        "formalize": f"""Rewrite the following text in formal government proposal language.
Use professional, official tone appropriate for federal contracts:

Text to formalize:
{selected_text}

Return only the formalized text, no explanations.""",

        "grammar": f"""Analyze the following text for grammar and spelling errors.
Return a JSON array of issues with this structure:
[{{"offset": number, "length": number, "message": "description", "replacements": ["suggestion1"], "severity": "error|warning|info"}}]

Text to analyze:
{full_content}""",

        "readability": f"""Analyze the readability of the following text.
Return a JSON object with this structure:
{{"score": 0-100, "grade": "Grade level", "avgSentenceLength": number, "avgWordLength": number, "suggestions": ["suggestion1", "suggestion2"]}}

Text to analyze:
{full_content}""",

        "passive": f"""Find all passive voice constructions in the following text.
Return a JSON array with this structure:
[{{"offset": number, "length": number, "text": "passive phrase", "suggestion": "active alternative"}}]

Text to analyze:
{full_content}""",

        "jargon": f"""Identify and simplify jargon and complex terms in the following text.
Replace technical jargon with clearer alternatives while maintaining accuracy:

Text to simplify:
{selected_text}

Return only the simplified text, no explanations.""",
    }

    prompt = prompts.get(action_id, "")

    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Anthropic API key not configured")

        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.content[0].text
        return {"result": result, "action": action_id}

    except anthropic.APIError as e:
        logger.exception(f"Anthropic API error for AI action {action_id}")
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}") from e
    except Exception as e:
        logger.exception(f"AI action execution failed: {action_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e


def _build_streaming_prompt(command: SlashCommand, rfp, request: CommandRequest) -> str:
    """Build the prompt for streaming slash commands."""
    rfp_context = f"""RFP: {rfp.title}
Agency: {rfp.agency or 'Not specified'}
Description: {rfp.description[:500] if rfp.description else 'Not available'}
NAICS: {rfp.naics_code or 'Not specified'}
Section: {request.section_id.replace('_', ' ').title() if request.section_id else 'Not specified'}"""

    prompts = {
        SlashCommand.WRITE: f"""Write new proposal content for the {request.section_id.replace('_', ' ') if request.section_id else 'proposal'} section.

RFP Context:
{rfp_context}

Current section context:
{request.context[:1000] if request.context else 'Empty section - start fresh'}

{request.custom_prompt if request.custom_prompt else 'Generate professional proposal content that addresses the RFP requirements.'}

Write clear, compelling content suitable for a government proposal. Only output the proposal content, no explanatory text.""",

        SlashCommand.EXPAND: f"""Expand and elaborate on the following text with more detail, examples, and supporting information.

RFP Context:
{rfp_context}

Text to expand:
{request.selected_text}

Provide a more comprehensive version that maintains the original meaning but adds depth and specificity. Only output the expanded text, no explanatory text.""",

        SlashCommand.SUMMARIZE: f"""Summarize the following text concisely while preserving all key points.

Text to summarize:
{request.selected_text}

Provide a clear, concise summary. Only output the summary, no explanatory text.""",

        SlashCommand.REQUIREMENTS: f"""Extract and list the key requirements from this text as clear, actionable items.

RFP Context:
{rfp_context}

Text to analyze:
{request.selected_text or request.context}

List each requirement as a bullet point with a brief description of how it should be addressed. Only output the requirements list, no explanatory text.""",

        SlashCommand.COMPLIANCE: f"""Add appropriate compliance language to this proposal text, ensuring it meets government contracting standards.

RFP Context:
{rfp_context}

Text to enhance:
{request.selected_text or request.context}

Add compliance-focused language that demonstrates understanding of requirements and commitment to meeting them. Only output the enhanced text, no explanatory text.""",

        SlashCommand.SIMILAR: f"""Based on this proposal section, describe relevant past performance examples that would strengthen the proposal.

RFP Context:
{rfp_context}

Current content:
{request.selected_text or request.context}

Suggest 2-3 past performance examples that align with the RFP requirements, with brief descriptions of scope, outcomes, and relevance. Only output the past performance examples, no explanatory text.""",

        SlashCommand.TABLE: f"""Convert this content into a well-formatted markdown table with appropriate headers and rows.

Content:
{request.selected_text}

Create a clear table structure. Only output the markdown table, no explanatory text.""",

        SlashCommand.CITE: f"""Format this text with proper citations and references suitable for a government proposal.

Text:
{request.selected_text}

Add appropriate citation formatting and reference markers. Only output the cited text, no explanatory text.""",
    }

    return prompts.get(command, "")


@router.post("/{rfp_id}/command/stream")
async def execute_command_stream(rfp: RFPDep, request: CommandRequest):
    """
    Execute a slash command with streaming response.

    For longer content generation commands.
    """
    # Check if this is a non-streaming command
    if request.command in NON_STREAMING_PROMPTS:
        # Redirect to non-streaming endpoint behavior
        result = await execute_command(rfp, request)
        # Return as a streaming response with single chunk
        async def single_chunk():
            yield f"data: {json.dumps({'type': 'content', 'text': result.result})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return StreamingResponse(
            single_chunk(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    prompt = _build_streaming_prompt(request.command, rfp, request)
    if not prompt:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown command: {request.command}"
        )

    async def generate():
        try:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Anthropic API key not configured'})}\n\n"
                return

            client = anthropic.Anthropic(api_key=api_key)

            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'type': 'content', 'text': text})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except anthropic.APIError as e:
            logger.exception(f"Anthropic API error for streaming command {request.command}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'AI service error: {str(e)}'})}\n\n"
        except Exception as e:
            logger.exception(f"Streaming command execution failed: {request.command}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
