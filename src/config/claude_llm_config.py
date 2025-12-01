"""
Claude LLM Configuration Module
Supports Claude 4.5 Sonnet and Opus models with extended thinking mode
for generating comprehensive, winning RFP proposals.
"""
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class ClaudeModel(Enum):
    """Available Claude 4.5 models"""
    SONNET_4_5 = "claude-sonnet-4-5-20250929"
    OPUS_4_5 = "claude-opus-4-5-20251101"


@dataclass
class ClaudeThinkingConfig:
    """Configuration for Claude's extended thinking mode"""
    enabled: bool = False
    budget_tokens: int = 10000  # Tokens allocated for thinking

    def to_api_param(self) -> dict[str, Any] | None:
        """Convert to API parameter format"""
        if not self.enabled:
            return None
        return {
            "type": "enabled",
            "budget_tokens": self.budget_tokens
        }


@dataclass
class ClaudeLLMConfig:
    """Configuration for Claude LLM settings"""
    model: ClaudeModel = ClaudeModel.SONNET_4_5
    api_key: str | None = None
    max_tokens: int = 16000  # Higher default for comprehensive proposals
    temperature: float = 1.0  # Claude 4.5 default
    thinking: ClaudeThinkingConfig = field(default_factory=ClaudeThinkingConfig)
    timeout: float = 120.0  # Longer timeout for thinking mode
    retries: int = 3

    def __post_init__(self):
        """Load API key from environment if not provided"""
        if not self.api_key:
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not found in environment")


class ClaudeLLMManager:
    """
    Manager for Claude 4.5 LLM interactions with extended thinking support.
    Optimized for generating comprehensive, winning RFP proposals.
    """

    # Task-specific configurations
    TASK_CONFIGS = {
        "proposal_generation": {
            "model": ClaudeModel.SONNET_4_5,
            "max_tokens": 16000,
            "thinking_enabled": True,
            "thinking_budget": 10000,
            "temperature": 1.0,
        },
        "premium_proposal_generation": {
            "model": ClaudeModel.OPUS_4_5,
            "max_tokens": 32000,
            "thinking_enabled": True,
            "thinking_budget": 20000,
            "temperature": 1.0,
        },
        "executive_summary": {
            "model": ClaudeModel.SONNET_4_5,
            "max_tokens": 4000,
            "thinking_enabled": True,
            "thinking_budget": 5000,
            "temperature": 1.0,
        },
        "technical_approach": {
            "model": ClaudeModel.SONNET_4_5,
            "max_tokens": 8000,
            "thinking_enabled": True,
            "thinking_budget": 8000,
            "temperature": 1.0,
        },
        "compliance_response": {
            "model": ClaudeModel.SONNET_4_5,
            "max_tokens": 4000,
            "thinking_enabled": False,
            "temperature": 0.7,
        },
        "pricing_justification": {
            "model": ClaudeModel.SONNET_4_5,
            "max_tokens": 2000,
            "thinking_enabled": False,
            "temperature": 0.5,
        },
    }

    def __init__(self, config: ClaudeLLMConfig | None = None):
        """Initialize Claude LLM Manager"""
        self.config = config or ClaudeLLMConfig()
        self.client = None
        self.logger = logging.getLogger(__name__)
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Anthropic client"""
        if not self.config.api_key:
            self.logger.warning("No API key available, Claude client not initialized")
            return

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.config.api_key)
            self.logger.info(f"Claude client initialized with model: {self.config.model.value}")
        except ImportError:
            self.logger.error("anthropic package not installed. Install with: pip install anthropic")
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")

    def _get_task_config(self, task_type: str) -> dict[str, Any]:
        """Get configuration for specific task type"""
        return self.TASK_CONFIGS.get(task_type, self.TASK_CONFIGS["proposal_generation"])

    def generate_completion(
        self,
        prompt: str,
        system_message: str | None = None,
        task_type: str = "proposal_generation",
        use_thinking: bool | None = None,
        thinking_budget: int | None = None,
        model_override: ClaudeModel | None = None,
        max_tokens_override: int | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Generate completion using Claude with optional extended thinking.

        Args:
            prompt: The user prompt
            system_message: Optional system message for context
            task_type: Type of task for config lookup
            use_thinking: Override thinking mode (None = use task default)
            thinking_budget: Override thinking budget
            model_override: Override model selection
            max_tokens_override: Override max tokens

        Returns:
            Dictionary with response content and metadata
        """
        if not self.client:
            return {
                "status": "error",
                "error": "Claude client not initialized",
                "content": None
            }

        # Get task-specific configuration
        task_config = self._get_task_config(task_type)

        # Determine model
        model = model_override or task_config.get("model", self.config.model)
        if isinstance(model, ClaudeModel):
            model = model.value

        # Determine max tokens
        max_tokens = max_tokens_override or task_config.get("max_tokens", self.config.max_tokens)

        # Determine thinking configuration
        enable_thinking = use_thinking if use_thinking is not None else task_config.get("thinking_enabled", False)
        budget = thinking_budget or task_config.get("thinking_budget", 10000)

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        # Build API call parameters
        api_params = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        # Add system message if provided
        if system_message:
            api_params["system"] = system_message

        # Add thinking configuration if enabled
        if enable_thinking:
            api_params["thinking"] = {
                "type": "enabled",
                "budget_tokens": budget
            }
            self.logger.info(f"Thinking mode enabled with budget: {budget} tokens")

        try:
            self.logger.info(f"Generating completion with model: {model}, thinking: {enable_thinking}")

            # Use streaming for thinking mode (required by Anthropic API for long operations)
            if enable_thinking:
                return self._generate_with_streaming(api_params, model, enable_thinking)
            else:
                response = self.client.messages.create(**api_params)

                # Extract content from response
                content = ""
                for block in response.content:
                    if block.type == "text":
                        content = block.text

                return {
                    "status": "success",
                    "content": content,
                    "thinking": None,
                    "model": model,
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                    "thinking_enabled": False,
                }

        except Exception as e:
            self.logger.error(f"Claude completion failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "content": None
            }

    def _generate_with_streaming(
        self,
        api_params: dict[str, Any],
        model: str,
        enable_thinking: bool
    ) -> dict[str, Any]:
        """
        Generate completion using streaming (required for extended thinking).

        Args:
            api_params: API parameters
            model: Model name
            enable_thinking: Whether thinking is enabled

        Returns:
            Dictionary with response content and metadata
        """
        content = ""
        thinking_content = ""
        input_tokens = 0
        output_tokens = 0

        try:
            with self.client.messages.stream(**api_params) as stream:
                for event in stream:
                    # Handle different event types
                    if hasattr(event, 'type'):
                        if event.type == 'content_block_start':
                            # Check if this is a thinking block or text block
                            if hasattr(event, 'content_block'):
                                block = event.content_block
                                if hasattr(block, 'type') and block.type == 'thinking':
                                    self.logger.debug("Thinking block started")
                        elif event.type == 'content_block_delta':
                            if hasattr(event, 'delta'):
                                delta = event.delta
                                if hasattr(delta, 'type'):
                                    if delta.type == 'thinking_delta':
                                        thinking_content += delta.thinking
                                    elif delta.type == 'text_delta':
                                        content += delta.text
                        elif event.type == 'message_delta':
                            if hasattr(event, 'usage'):
                                output_tokens = event.usage.output_tokens
                        elif event.type == 'message_start':
                            if hasattr(event, 'message') and hasattr(event.message, 'usage'):
                                input_tokens = event.message.usage.input_tokens

            self.logger.info(f"Streaming complete. Content length: {len(content)}, Thinking length: {len(thinking_content)}")

            return {
                "status": "success",
                "content": content,
                "thinking": thinking_content if enable_thinking else None,
                "model": model,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
                "thinking_enabled": enable_thinking,
            }

        except Exception as e:
            self.logger.error(f"Streaming completion failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "content": None
            }

    def generate_comprehensive_proposal_section(
        self,
        section_type: str,
        rfp_data: dict[str, Any],
        company_profile: dict[str, Any],
        compliance_data: dict[str, Any] | None = None,
        pricing_data: dict[str, Any] | None = None,
        rag_context: str | None = None,
        use_opus: bool = False,
        enable_thinking: bool = True,
    ) -> dict[str, Any]:
        """
        Generate a comprehensive proposal section using Claude with thinking mode.

        Args:
            section_type: Type of section (executive_summary, technical_approach, etc.)
            rfp_data: RFP information
            company_profile: Company information
            compliance_data: Optional compliance matrix data
            pricing_data: Optional pricing data
            rag_context: Optional RAG context for historical reference
            use_opus: Use Opus for premium generation
            enable_thinking: Enable extended thinking mode

        Returns:
            Dictionary with generated content and metadata
        """
        # Determine task type based on section and model choice
        if use_opus:
            task_type = "premium_proposal_generation"
        elif section_type in self.TASK_CONFIGS:
            task_type = section_type
        else:
            task_type = "proposal_generation"

        # Build comprehensive prompt
        prompt = self._build_section_prompt(
            section_type, rfp_data, company_profile,
            compliance_data, pricing_data, rag_context
        )

        # Build system message
        system_message = self._get_proposal_system_message(section_type)

        # Generate content
        result = self.generate_completion(
            prompt=prompt,
            system_message=system_message,
            task_type=task_type,
            use_thinking=enable_thinking,
            model_override=ClaudeModel.OPUS_4_5 if use_opus else None,
        )

        if result["status"] == "success":
            result["section_type"] = section_type
            result["word_count"] = len(result["content"].split()) if result["content"] else 0

        return result

    def _build_section_prompt(
        self,
        section_type: str,
        rfp_data: dict[str, Any],
        company_profile: dict[str, Any],
        compliance_data: dict[str, Any] | None,
        pricing_data: dict[str, Any] | None,
        rag_context: str | None,
    ) -> str:
        """Build comprehensive prompt for section generation"""

        # Extract RFP details
        rfp_title = rfp_data.get('title', 'Government Contract')
        rfp_agency = rfp_data.get('agency', 'Government Agency')
        rfp_description = rfp_data.get('description', '')
        rfp_naics = rfp_data.get('naics_code', '')
        award_amount = rfp_data.get('award_amount', 0)

        # Extract company details
        company_name = company_profile.get('company_name', 'Our Company')
        certifications = company_profile.get('certifications', [])
        core_competencies = company_profile.get('core_competencies', [])
        past_performance = company_profile.get('past_performance', [])

        # Build context sections
        rfp_context = f"""
## RFP Information
- **Title:** {rfp_title}
- **Agency:** {rfp_agency}
- **NAICS Code:** {rfp_naics}
- **Estimated Value:** ${award_amount:,.2f}

### RFP Description
{rfp_description[:2000] if len(rfp_description) > 2000 else rfp_description}
"""

        company_context = f"""
## Company Information
- **Company Name:** {company_name}
- **Certifications:** {', '.join(certifications) if certifications else 'N/A'}
- **Core Competencies:** {', '.join(core_competencies[:5]) if core_competencies else 'N/A'}
"""

        if past_performance:
            company_context += "\n### Past Performance\n"
            for perf in past_performance[:3]:
                if isinstance(perf, dict):
                    company_context += f"- {perf.get('client', 'Client')}: {perf.get('project', 'Project')}\n"

        # Add compliance context if available
        compliance_context = ""
        if compliance_data:
            compliance_rate = compliance_data.get('compliance_summary', {}).get('compliance_rate', 0)
            requirements = compliance_data.get('requirements_and_responses', [])[:5]
            compliance_context = f"""
## Compliance Analysis
- **Compliance Rate:** {compliance_rate:.1%}
- **Key Requirements Identified:** {len(requirements)}
"""
            if requirements:
                compliance_context += "\n### Key Requirements:\n"
                for req in requirements:
                    req_text = req.get('requirement_text', '')[:100]
                    compliance_context += f"- {req_text}...\n"

        # Add pricing context if available
        pricing_context = ""
        if pricing_data:
            pricing_context = f"""
## Pricing Strategy
- **Recommended Price:** ${pricing_data.get('recommended_price', 0):,.2f}
- **Strategy:** {pricing_data.get('recommended_strategy', 'Competitive')}
- **Margin:** {pricing_data.get('margin_percentage', 0):.1f}%
- **Justification:** {pricing_data.get('justification', '')}
"""

        # Add RAG context if available
        historical_context = ""
        if rag_context:
            historical_context = f"""
## Historical Context (Similar Successful Bids)
{rag_context[:1500]}
"""

        # Section-specific instructions
        section_instructions = self._get_section_instructions(section_type)

        # Combine into full prompt
        prompt = f"""
{rfp_context}

{company_context}

{compliance_context}

{pricing_context}

{historical_context}

---

# Task: Generate {section_type.replace('_', ' ').title()} Section

{section_instructions}

## Requirements:
1. Write in a professional, confident tone appropriate for government contracting
2. Be specific and detailed - avoid generic language
3. Address the agency's needs directly based on the RFP description
4. Highlight relevant company qualifications and differentiators
5. Include concrete examples, metrics, and evidence where possible
6. Structure the content with clear headings and logical flow
7. Ensure the content is comprehensive and persuasive
8. Target word count: {self._get_target_word_count(section_type)} words minimum

Generate the {section_type.replace('_', ' ')} section now:
"""
        return prompt

    def _get_section_instructions(self, section_type: str) -> str:
        """Get specific instructions for each section type"""
        instructions = {
            "executive_summary": """
Generate a compelling executive summary that:
- Opens with a strong statement of understanding the agency's needs
- Summarizes our key qualifications and why we're the best choice
- Highlights our competitive advantages and unique value proposition
- Addresses compliance with key requirements
- Provides a clear value statement with pricing context
- Closes with a confident commitment to successful delivery
- Creates urgency and differentiates from competitors
""",
            "technical_approach": """
Generate a detailed technical approach section that:
- Describes our methodology and approach to meeting all requirements
- Outlines specific processes, procedures, and workflows
- Details our quality assurance and quality control measures
- Explains our project management approach and milestones
- Addresses risk management and mitigation strategies
- Describes resource allocation and staffing approach
- Includes implementation timeline and key deliverables
- Demonstrates innovation and best practices
""",
            "company_qualifications": """
Generate a comprehensive company qualifications section that:
- Details our relevant experience and track record
- Highlights specific past performance on similar contracts
- Lists all relevant certifications and credentials
- Describes our organizational capabilities and capacity
- Showcases our team's expertise and qualifications
- Demonstrates our financial stability and reliability
- Provides evidence of successful government contracting experience
""",
            "management_approach": """
Generate a thorough management approach section that:
- Describes our organizational structure for this contract
- Details key personnel and their qualifications
- Explains our communication and reporting procedures
- Outlines our quality management system
- Describes our approach to schedule and cost management
- Explains subcontractor management (if applicable)
- Details our continuous improvement processes
""",
            "pricing_narrative": """
Generate a persuasive pricing narrative section that:
- Explains our pricing methodology and approach
- Justifies the proposed pricing with market analysis
- Demonstrates cost efficiency and value
- Explains any cost assumptions or exclusions
- Highlights cost control measures
- Shows how our pricing ensures sustainable delivery
- Addresses any pricing risks and mitigation
""",
        }
        return instructions.get(section_type, f"""
Generate a comprehensive {section_type.replace('_', ' ')} section that:
- Addresses all relevant requirements from the RFP
- Demonstrates our capabilities and qualifications
- Provides specific, detailed information
- Uses professional government contracting language
- Is persuasive and compelling
""")

    def _get_target_word_count(self, section_type: str) -> int:
        """Get target word count for each section type"""
        word_counts = {
            "executive_summary": 800,
            "technical_approach": 1500,
            "company_qualifications": 1000,
            "management_approach": 1200,
            "pricing_narrative": 600,
        }
        return word_counts.get(section_type, 800)

    def _get_proposal_system_message(self, section_type: str) -> str:
        """Get system message for proposal generation"""
        return f"""You are an expert government contracting proposal writer with extensive experience winning federal, state, and local government contracts. You specialize in writing compelling, compliant, and comprehensive {section_type.replace('_', ' ')} sections.

Your writing style:
- Professional and authoritative
- Specific and evidence-based
- Compliant with government contracting standards
- Persuasive without being aggressive
- Clear and well-structured

Key principles:
1. Always address the customer's needs first
2. Provide specific, quantifiable evidence
3. Use action verbs and confident language
4. Maintain compliance with RFP requirements
5. Differentiate from competitors
6. Focus on value and outcomes

You write proposals that WIN contracts."""

    def validate_setup(self) -> dict[str, Any]:
        """Validate Claude LLM setup"""
        validation = {
            "status": "success",
            "api_key_configured": bool(self.config.api_key),
            "client_initialized": self.client is not None,
            "model": self.config.model.value,
            "thinking_supported": True,
            "errors": []
        }

        if not self.config.api_key:
            validation["status"] = "error"
            validation["errors"].append("ANTHROPIC_API_KEY not configured")

        if not self.client:
            validation["status"] = "error"
            validation["errors"].append("Anthropic client not initialized")

        # Test connection with a simple query
        if self.client:
            try:
                test_result = self.generate_completion(
                    prompt="Say 'test successful' in 3 words or less.",
                    task_type="compliance_response",
                    use_thinking=False,
                )
                validation["connection_test"] = test_result["status"] == "success"
                if test_result["status"] != "success":
                    validation["errors"].append(f"Connection test failed: {test_result.get('error')}")
            except Exception as e:
                validation["connection_test"] = False
                validation["errors"].append(f"Connection test error: {str(e)}")

        validation["setup_valid"] = validation["status"] == "success" and validation.get("connection_test", False)
        return validation


# Factory function
def create_claude_llm_manager(
    api_key: str | None = None,
    model: ClaudeModel = ClaudeModel.SONNET_4_5,
    enable_thinking: bool = False,
    thinking_budget: int = 10000,
) -> ClaudeLLMManager:
    """
    Create a Claude LLM Manager with specified configuration.

    Args:
        api_key: Anthropic API key (uses env var if not provided)
        model: Claude model to use
        enable_thinking: Enable thinking mode by default
        thinking_budget: Default thinking budget

    Returns:
        Configured ClaudeLLMManager instance
    """
    config = ClaudeLLMConfig(
        model=model,
        api_key=api_key,
        thinking=ClaudeThinkingConfig(
            enabled=enable_thinking,
            budget_tokens=thinking_budget
        )
    )
    return ClaudeLLMManager(config)


if __name__ == "__main__":
    print("Testing Claude LLM Configuration")
    print("=" * 50)

    try:
        manager = create_claude_llm_manager()
        validation = manager.validate_setup()

        print(f"API Key Configured: {validation['api_key_configured']}")
        print(f"Client Initialized: {validation['client_initialized']}")
        print(f"Model: {validation['model']}")
        print(f"Thinking Supported: {validation['thinking_supported']}")
        print(f"Setup Valid: {validation['setup_valid']}")

        if validation['errors']:
            print("\nErrors:")
            for error in validation['errors']:
                print(f"  - {error}")

        if validation['setup_valid']:
            print("\n✓ Claude LLM Configuration is ready!")
        else:
            print("\n✗ Claude LLM Configuration needs attention")

    except Exception as e:
        print(f"Error: {e}")
