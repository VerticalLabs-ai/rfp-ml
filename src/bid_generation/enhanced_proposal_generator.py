"""
Enhanced Proposal Generator
Uses Claude 4.5 with extended thinking mode to generate comprehensive,
winning RFP proposal content. Supports both Sonnet and Opus models.
"""
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ProposalQuality(Enum):
    """Quality levels for proposal generation"""
    STANDARD = "standard"  # Claude Sonnet without thinking
    ENHANCED = "enhanced"  # Claude Sonnet with thinking
    PREMIUM = "premium"    # Claude Opus with thinking


@dataclass
class ProposalGenerationConfig:
    """Configuration for proposal generation"""
    quality: ProposalQuality = ProposalQuality.ENHANCED
    enable_thinking: bool = True
    thinking_budget: int = 10000
    include_rag_context: bool = True
    target_word_count_multiplier: float = 1.5  # Generate 1.5x target for editing
    sections_to_enhance: list = field(default_factory=lambda: [
        "executive_summary",
        "technical_approach",
        "company_qualifications",
        "management_approach",
        "pricing_narrative",
    ])


class EnhancedProposalGenerator:
    """
    Enhanced proposal generator using Claude 4.5 with thinking mode
    for comprehensive RFP proposal content generation.
    """

    def __init__(
        self,
        config: ProposalGenerationConfig | None = None,
        rag_engine=None,
        api_key: str | None = None,
    ):
        """
        Initialize the enhanced proposal generator.

        Args:
            config: Generation configuration
            rag_engine: Optional RAG engine for historical context
            api_key: Optional Anthropic API key
        """
        self.config = config or ProposalGenerationConfig()
        self.rag_engine = rag_engine
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.claude_manager = None
        self.logger = logging.getLogger(__name__)

        self._initialize_claude()

    def _initialize_claude(self):
        """Initialize Claude LLM manager"""
        if not self.api_key:
            self.logger.warning("ANTHROPIC_API_KEY not found - Claude features disabled")
            return

        try:
            from src.config.claude_llm_config import (
                ClaudeModel,
                create_claude_llm_manager,
            )

            # Select model based on quality setting
            if self.config.quality == ProposalQuality.PREMIUM:
                model = ClaudeModel.OPUS_4_5
            else:
                model = ClaudeModel.SONNET_4_5

            self.claude_manager = create_claude_llm_manager(
                api_key=self.api_key,
                model=model,
                enable_thinking=self.config.enable_thinking,
                thinking_budget=self.config.thinking_budget,
            )
            self.logger.info(f"Claude manager initialized with {model.value}")

        except ImportError as e:
            self.logger.error(f"Failed to import Claude config: {e}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Claude manager: {e}")

    def is_available(self) -> bool:
        """Check if Claude-enhanced generation is available"""
        return self.claude_manager is not None

    def get_rag_context(self, rfp_data: dict[str, Any]) -> str | None:
        """Get RAG context for the RFP"""
        if not self.rag_engine or not self.config.include_rag_context:
            return None

        try:
            # Build search query from RFP data
            query = f"{rfp_data.get('title', '')} {rfp_data.get('description', '')[:500]}"

            # Get relevant historical context using retrieve() method
            results = self.rag_engine.retrieve(query, k=3)

            if results and len(results) > 0:
                context_parts = []
                for i, result in enumerate(results):
                    if hasattr(result, 'content'):
                        context_parts.append(f"Reference {i+1}:\n{result.content[:500]}")
                    elif isinstance(result, dict):
                        context_parts.append(f"Reference {i+1}:\n{result.get('content', '')[:500]}")

                return "\n\n".join(context_parts) if context_parts else None

        except Exception as e:
            self.logger.warning(f"Failed to get RAG context: {e}")

        return None

    def generate_enhanced_section(
        self,
        section_type: str,
        rfp_data: dict[str, Any],
        company_profile: dict[str, Any],
        compliance_data: dict[str, Any] | None = None,
        pricing_data: dict[str, Any] | None = None,
        quality_override: ProposalQuality | None = None,
        enable_thinking_override: bool | None = None,
        qa_items: list[dict[str, Any]] | None = None,
        compliance_signals: dict[str, Any] | None = None,
        document_content: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate an enhanced proposal section using Claude.

        Args:
            section_type: Type of section to generate
            rfp_data: RFP information
            company_profile: Company information
            compliance_data: Optional compliance matrix data
            pricing_data: Optional pricing data
            quality_override: Override quality setting
            enable_thinking_override: Override thinking mode
            qa_items: Q&A items from the RFP for context
            compliance_signals: Detected compliance signals (FEMA, etc.)
            document_content: Extracted text from RFP attachments (PDFs, DOCX)

        Returns:
            Dictionary with generated content and metadata
        """
        if not self.is_available():
            return {
                "status": "unavailable",
                "error": "Claude manager not available",
                "content": None,
                "section_type": section_type,
            }

        # Determine settings
        quality = quality_override or self.config.quality
        enable_thinking = enable_thinking_override if enable_thinking_override is not None else self.config.enable_thinking

        # Get RAG context
        rag_context = self.get_rag_context(rfp_data)

        # Use premium (Opus) model for PREMIUM quality
        use_opus = quality == ProposalQuality.PREMIUM

        try:
            result = self.claude_manager.generate_comprehensive_proposal_section(
                section_type=section_type,
                rfp_data=rfp_data,
                company_profile=company_profile,
                compliance_data=compliance_data,
                pricing_data=pricing_data,
                rag_context=rag_context,
                use_opus=use_opus,
                enable_thinking=enable_thinking,
                qa_items=qa_items,
                compliance_signals=compliance_signals,
                document_content=document_content,
            )

            # Add quality metadata
            result["quality"] = quality.value
            result["rag_context_used"] = rag_context is not None

            return result

        except Exception as e:
            self.logger.error(f"Failed to generate {section_type}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "content": None,
                "section_type": section_type,
            }

    def generate_complete_proposal(
        self,
        rfp_data: dict[str, Any],
        company_profile: dict[str, Any],
        compliance_data: dict[str, Any] | None = None,
        pricing_data: dict[str, Any] | None = None,
        sections: list[str] | None = None,
        quality: ProposalQuality | None = None,
        enable_thinking: bool | None = None,
        progress_callback=None,
    ) -> dict[str, Any]:
        """
        Generate a complete enhanced proposal with all sections.

        Args:
            rfp_data: RFP information
            company_profile: Company information
            compliance_data: Optional compliance matrix data
            pricing_data: Optional pricing data
            sections: List of sections to generate (None = all)
            quality: Quality level for generation
            enable_thinking: Enable thinking mode
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with all generated sections and metadata
        """
        sections_to_generate = sections or self.config.sections_to_enhance
        quality = quality or self.config.quality
        enable_thinking = enable_thinking if enable_thinking is not None else self.config.enable_thinking

        results = {
            "rfp_title": rfp_data.get("title", "Unknown RFP"),
            "sections": {},
            "metadata": {
                "quality": quality.value,
                "thinking_enabled": enable_thinking,
                "total_sections": len(sections_to_generate),
                "successful_sections": 0,
                "total_word_count": 0,
                "errors": [],
            }
        }

        for i, section_type in enumerate(sections_to_generate):
            self.logger.info(f"Generating {section_type} ({i+1}/{len(sections_to_generate)})")

            if progress_callback:
                progress_callback(section_type, i, len(sections_to_generate))

            section_result = self.generate_enhanced_section(
                section_type=section_type,
                rfp_data=rfp_data,
                company_profile=company_profile,
                compliance_data=compliance_data,
                pricing_data=pricing_data,
                quality_override=quality,
                enable_thinking_override=enable_thinking,
            )

            results["sections"][section_type] = section_result

            if section_result.get("status") == "success":
                results["metadata"]["successful_sections"] += 1
                results["metadata"]["total_word_count"] += section_result.get("word_count", 0)
            else:
                results["metadata"]["errors"].append({
                    "section": section_type,
                    "error": section_result.get("error", "Unknown error")
                })

        results["metadata"]["success_rate"] = (
            results["metadata"]["successful_sections"] / len(sections_to_generate)
            if sections_to_generate else 0
        )

        return results

    def enhance_existing_content(
        self,
        existing_content: str,
        section_type: str,
        rfp_data: dict[str, Any],
        company_profile: dict[str, Any],
        enhancement_instructions: str | None = None,
        quality: ProposalQuality | None = None,
    ) -> dict[str, Any]:
        """
        Enhance existing proposal content using Claude.

        Args:
            existing_content: The existing content to enhance
            section_type: Type of section
            rfp_data: RFP information
            company_profile: Company information
            enhancement_instructions: Specific enhancement instructions
            quality: Quality level for enhancement

        Returns:
            Dictionary with enhanced content and metadata
        """
        if not self.is_available():
            return {
                "status": "unavailable",
                "error": "Claude manager not available",
                "content": existing_content,
            }

        quality = quality or self.config.quality
        use_opus = quality == ProposalQuality.PREMIUM

        # Build enhancement prompt
        prompt = f"""
## Current Content to Enhance

{existing_content}

## RFP Context

- **Title:** {rfp_data.get('title', 'Unknown')}
- **Agency:** {rfp_data.get('agency', 'Unknown')}
- **Description:** {rfp_data.get('description', '')[:1000]}

## Company Context

- **Company:** {company_profile.get('company_name', 'Unknown')}
- **Competencies:** {', '.join(company_profile.get('core_competencies', [])[:5])}

## Task

Enhance the above {section_type.replace('_', ' ')} content to make it more:
1. Comprehensive and detailed
2. Persuasive and compelling
3. Specific with concrete examples
4. Professional and confident
5. Aligned with government contracting best practices

{enhancement_instructions or ''}

Provide the enhanced version:
"""

        system_message = f"""You are an expert government contracting proposal editor.
Your task is to enhance existing proposal content to make it more comprehensive and compelling.
Maintain the original structure but significantly expand and improve the content.
Add specific details, examples, and evidence where appropriate.
Ensure the enhanced content is at least 50% longer than the original."""

        try:
            result = self.claude_manager.generate_completion(
                prompt=prompt,
                system_message=system_message,
                task_type="proposal_generation",
                use_thinking=self.config.enable_thinking,
                model_override=None,  # Use configured model based on quality
            )

            if result["status"] == "success":
                result["original_word_count"] = len(existing_content.split())
                result["enhanced_word_count"] = len(result["content"].split()) if result["content"] else 0
                result["improvement_ratio"] = (
                    result["enhanced_word_count"] / result["original_word_count"]
                    if result["original_word_count"] > 0 else 1.0
                )

            return result

        except Exception as e:
            self.logger.error(f"Failed to enhance content: {e}")
            return {
                "status": "error",
                "error": str(e),
                "content": existing_content,
            }


def create_enhanced_proposal_generator(
    quality: str = "enhanced",
    enable_thinking: bool = True,
    thinking_budget: int = 10000,
    rag_engine=None,
    api_key: str | None = None,
) -> EnhancedProposalGenerator:
    """
    Factory function to create an enhanced proposal generator.

    Args:
        quality: Quality level ("standard", "enhanced", "premium")
        enable_thinking: Enable Claude's thinking mode
        thinking_budget: Token budget for thinking
        rag_engine: Optional RAG engine for context
        api_key: Optional Anthropic API key

    Returns:
        Configured EnhancedProposalGenerator instance
    """
    # Map quality string to enum
    quality_map = {
        "standard": ProposalQuality.STANDARD,
        "enhanced": ProposalQuality.ENHANCED,
        "premium": ProposalQuality.PREMIUM,
    }
    quality_enum = quality_map.get(quality.lower(), ProposalQuality.ENHANCED)

    config = ProposalGenerationConfig(
        quality=quality_enum,
        enable_thinking=enable_thinking,
        thinking_budget=thinking_budget,
    )

    return EnhancedProposalGenerator(
        config=config,
        rag_engine=rag_engine,
        api_key=api_key,
    )


if __name__ == "__main__":
    print("Testing Enhanced Proposal Generator")
    print("=" * 50)

    # Test initialization
    generator = create_enhanced_proposal_generator(quality="enhanced")

    print(f"Claude Available: {generator.is_available()}")

    if generator.is_available():
        # Test with sample RFP data
        test_rfp = {
            "title": "Water Delivery Services for Government Facilities",
            "agency": "General Services Administration",
            "description": "Procurement of bottled water delivery services for multiple government facilities in the DC metro area. Contractor shall provide weekly delivery of 5-gallon water jugs and related equipment maintenance.",
            "naics_code": "312112",
            "award_amount": 150000,
        }

        test_company = {
            "company_name": "IBYTE Enterprises, LLC",
            "certifications": ["Small Business", "WOSB"],
            "core_competencies": ["Water Delivery", "Government Contracting", "Logistics"],
        }

        print("\nGenerating Executive Summary...")
        result = generator.generate_enhanced_section(
            section_type="executive_summary",
            rfp_data=test_rfp,
            company_profile=test_company,
        )

        print(f"Status: {result.get('status')}")
        print(f"Word Count: {result.get('word_count', 0)}")
        print(f"Thinking Used: {result.get('thinking_enabled', False)}")

        if result.get("content"):
            print(f"\nGenerated Content Preview:\n{result['content'][:500]}...")

    else:
        print("Claude not available - set ANTHROPIC_API_KEY to enable")
