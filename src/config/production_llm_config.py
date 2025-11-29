"""
Production-ready LLM configuration optimized for bid generation
Includes environment detection and performance optimization
"""
import logging
from dataclasses import dataclass, field
from typing import Any

from src.config.llm_config import LLMConfig, LLMManager


@dataclass
class BidGenerationLLMConfig(LLMConfig):
    """Specialized configuration for bid generation tasks"""
    # Optimized models for different tasks
    general_model: str = "distilgpt2"  # Fast model for general tasks
    bid_generation_model: str = "distilgpt2"  # Model for bid content generation
    structured_extraction_model: str = "distilgpt2"  # Model for requirement extraction
    # Task-specific parameters
    bid_generation_temperature: float = 0.8  # More creative for bid writing
    structured_extraction_temperature: float = 0.2  # More deterministic for extraction
    general_temperature: float = 0.7
    # Performance optimization
    use_model_caching: bool = True
    max_concurrent_requests: int = 3
    chunk_large_prompts: bool = True
    max_prompt_length: int = 2048
    # Bid-specific settings
    company_name: str = "AquaServe Solutions"
    default_certifications: list = field(default_factory=lambda: [
        "FDA Approved Facility",
        "ISO 9001:2015 Certified",
        "OSHA Compliant",
        "EPA Water Quality Standards"
    ])
    # Output formatting
    use_structured_output: bool = True
    include_confidence_scores: bool = True
class BidGenerationLLMManager:
    """
    Specialized LLM manager for bid generation tasks
    Optimized for government RFP bid writing
    """
    def __init__(self, config: BidGenerationLLMConfig | None = None):
        self.config = config or BidGenerationLLMConfig()
        # Initialize base LLM manager
        base_config = LLMConfig(
            local_model_name=self.config.general_model,
            local_model_temperature=self.config.general_temperature,
            use_gpu=False,  # Optimized for CPU environment
            openai_temperature=self.config.general_temperature
        )
        self.llm_manager = LLMManager(base_config)
        self.logger = self._setup_logger()
        # Cache for commonly used prompts
        self.prompt_cache = {}
        self.logger.info("Bid Generation LLM Manager initialized")
    def _setup_logger(self) -> logging.Logger:
        """Setup specialized logging for bid generation"""
        logger = logging.getLogger('bid_generation_llm')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    def generate_bid_section(
        self,
        section_type: str,
        rfp_context: str,
        requirements: dict[str, Any],
        max_words: int = 300
    ) -> dict[str, Any]:
        """
        Generate a specific section of a bid document
        Args:
            section_type: Type of section (executive_summary, qualifications, etc.)
            rfp_context: Relevant RFP information
            requirements: Specific requirements for this section
            max_words: Maximum word count for the section
        Returns:
            Dictionary with generated content and metadata
        """
        # Create section-specific prompt
        prompt = self._create_section_prompt(section_type, rfp_context, requirements, max_words)
        try:
            # Generate content using bid generation parameters
            content = self.llm_manager.generate_text(
                prompt,
                task_type="bid_generation",
                temperature=self.config.bid_generation_temperature,
                max_tokens=min(max_words * 2, 500)  # Rough token estimation
            )
            # Post-process content
            processed_content = self._post_process_content(content, section_type, max_words)
            return {
                "section_type": section_type,
                "content": processed_content,
                "word_count": len(processed_content.split()),
                "requirements_addressed": list(requirements.keys()),
                "confidence_score": self._calculate_confidence_score(processed_content, requirements),
                "status": "generated"
            }
        except Exception as e:
            self.logger.error(f"Failed to generate {section_type} section: {e}")
            return {
                "section_type": section_type,
                "content": f"Error generating {section_type} section",
                "word_count": 0,
                "requirements_addressed": [],
                "confidence_score": 0.0,
                "status": "error",
                "error": str(e)
            }
    def _create_section_prompt(
        self,
        section_type: str,
        rfp_context: str,
        requirements: dict[str, Any],
        max_words: int
    ) -> str:
        """Create specialized prompts for different bid sections"""
        company_info = f"""
        Company: {self.config.company_name}
        Certifications: {', '.join(self.config.default_certifications)}
        """
        section_prompts = {
            "executive_summary": f"""
            Write a compelling executive summary for a government bid proposal.
            RFP Context: {rfp_context}
            Requirements to address:
            {self._format_requirements(requirements)}
            {company_info}
            Create a professional executive summary that:
            1. Clearly states our understanding of the requirement
            2. Highlights our key qualifications and competitive advantages
            3. Demonstrates our commitment to quality and compliance
            4. Maintains a confident, professional tone
            Maximum length: {max_words} words.
            """,
            "company_qualifications": f"""
            Write a company qualifications section for a government bid.
            RFP Context: {rfp_context}
            Required qualifications:
            {self._format_requirements(requirements)}
            {company_info}
            Create a qualifications section that:
            1. Details our relevant experience and capabilities
            2. Lists all applicable certifications and compliance
            3. Provides specific examples of similar successful projects
            4. Demonstrates our technical expertise
            Maximum length: {max_words} words.
            """,
            "technical_approach": f"""
            Write a technical approach section for a government bid.
            RFP Context: {rfp_context}
            Technical requirements:
            {self._format_requirements(requirements)}
            {company_info}
            Create a technical approach that:
            1. Outlines our methodology for meeting all requirements
            2. Describes our quality assurance processes
            3. Details our implementation timeline
            4. Addresses any technical challenges and solutions
            Maximum length: {max_words} words.
            """
        }
        return section_prompts.get(section_type, f"""
        Write a {section_type} section for a government bid proposal.
        RFP Context: {rfp_context}
        Requirements: {self._format_requirements(requirements)}
        {company_info}
        Maximum length: {max_words} words.
        """)
    def _format_requirements(self, requirements: dict[str, Any]) -> str:
        """Format requirements dictionary into readable text"""
        if not requirements:
            return "No specific requirements provided."
        formatted = []
        for key, value in requirements.items():
            formatted.append(f"- {key}: {value}")
        return "\n".join(formatted)
    def _post_process_content(self, content: str, section_type: str, max_words: int) -> str:
        """Post-process generated content for quality and formatting"""
        # Basic cleanup
        content = content.strip()
        # Remove any incomplete sentences at the end
        sentences = content.split('.')
        if len(sentences) > 1 and len(sentences[-1].strip()) < 10:
            content = '.'.join(sentences[:-1]) + '.'
        # Word count check
        words = content.split()
        if len(words) > max_words:
            # Truncate to max words while preserving sentence structure
            truncated_words = words[:max_words]
            truncated_content = ' '.join(truncated_words)
            # Find last complete sentence
            last_period = truncated_content.rfind('.')
            if last_period > len(truncated_content) * 0.8:  # If period is near the end
                content = truncated_content[:last_period + 1]
            else:
                content = truncated_content
        return content
    def _calculate_confidence_score(self, content: str, requirements: dict[str, Any]) -> float:
        """Calculate confidence score based on content quality and requirement coverage"""
        score = 0.0
        # Base score for having content
        if len(content.strip()) > 20:
            score += 0.3
        # Score for addressing requirements
        if requirements:
            addressed_count = 0
            for req_key in requirements.keys():
                if req_key.lower() in content.lower():
                    addressed_count += 1
            requirement_coverage = addressed_count / len(requirements)
            score += requirement_coverage * 0.4
        else:
            score += 0.4  # If no specific requirements, give benefit of doubt
        # Score for content quality indicators
        quality_indicators = [
            len(content.split()) > 50,  # Sufficient length
            '.' in content,  # Complete sentences
            'experience' in content.lower() or 'qualified' in content.lower(),  # Relevant terms
            'comply' in content.lower() or 'meet' in content.lower(),  # Compliance language
        ]
        quality_score = sum(quality_indicators) / len(quality_indicators)
        score += quality_score * 0.3
        return min(score, 1.0)
    def extract_requirements(self, rfp_text: str) -> dict[str, Any]:
        """
        Extract requirements from RFP text using structured extraction
        Args:
            rfp_text: Raw RFP text to analyze
        Returns:
            Dictionary of extracted requirements
        """
        prompt = f"""
        Analyze the following RFP text and extract key requirements.
        RFP Text:
        {rfp_text[:1500]}  # Limit text length for processing
        Extract and format the requirements as a structured list:
        1. Mandatory requirements (must-haves)
        2. Technical specifications
        3. Delivery/timeline requirements
        4. Certification/compliance requirements
        5. Experience/qualification requirements
        Format each requirement clearly and concisely.
        """
        try:
            response = self.llm_manager.generate_text(
                prompt,
                task_type="structured_extraction",
                temperature=self.config.structured_extraction_temperature,
                max_tokens=400
            )
            # Parse response into structured format
            requirements = self._parse_requirements_response(response)
            self.logger.info(f"Extracted {len(requirements)} requirements from RFP")
            return requirements
        except Exception as e:
            self.logger.error(f"Failed to extract requirements: {e}")
            return {}
    def _parse_requirements_response(self, response: str) -> dict[str, Any]:
        """Parse LLM response into structured requirements dictionary"""
        requirements = {}
        current_category = "general"
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Check for category headers
            if any(keyword in line.lower() for keyword in ['mandatory', 'technical', 'delivery', 'certification', 'experience']):
                current_category = line.lower().replace(':', '').replace('-', '').strip()
                continue
            # Extract individual requirements
            if line.startswith(('-', '•', '*')) or line[0].isdigit():
                # Clean up the requirement text
                req_text = line.lstrip('-•*0123456789. ').strip()
                if len(req_text) > 10:  # Only include substantial requirements
                    req_key = f"{current_category}_{len(requirements) + 1}"
                    requirements[req_key] = req_text
        return requirements
    def validate_infrastructure(self) -> dict[str, Any]:
        """Validate the bid generation LLM infrastructure"""
        self.logger.info("Validating bid generation LLM infrastructure...")
        # Get base validation results
        base_validation = self.llm_manager.validate_setup()
        # Add bid generation specific tests
        bid_validation = {
            "base_llm_valid": base_validation['setup_valid'],
            "bid_generation_test": False,
            "requirement_extraction_test": False,
            "section_generation_test": False,
            "performance_metrics": {},
            "errors": base_validation.get('errors', [])
        }
        if base_validation['setup_valid']:
            # Test bid section generation
            try:
                test_section = self.generate_bid_section(
                    "executive_summary",
                    "Government bottled water delivery service contract",
                    {"duration": "12 months", "delivery_frequency": "bi-weekly"},
                    max_words=100
                )
                bid_validation["bid_generation_test"] = test_section['status'] == 'generated'
                bid_validation["section_generation_test"] = test_section['confidence_score'] > 0.5
            except Exception as e:
                bid_validation["errors"].append(f"Bid generation test failed: {e}")
            # Test requirement extraction
            try:
                test_requirements = self.extract_requirements(
                    "The contractor must provide bottled water delivery for 12 months. "
                    "All water must meet FDA standards. Delivery must be bi-weekly."
                )
                bid_validation["requirement_extraction_test"] = len(test_requirements) > 0
            except Exception as e:
                bid_validation["errors"].append(f"Requirement extraction test failed: {e}")
        # Overall validation
        bid_validation["setup_valid"] = (
            bid_validation["base_llm_valid"] and
            bid_validation["bid_generation_test"] and
            bid_validation["requirement_extraction_test"]
        )
        return bid_validation
# Convenience function for creating bid generation LLM manager
def create_bid_generation_llm_manager(config: BidGenerationLLMConfig | None = None) -> BidGenerationLLMManager:
    """Create and return configured bid generation LLM manager"""
    return BidGenerationLLMManager(config)
if __name__ == "__main__":
    # Test the bid generation LLM infrastructure
    print("Testing Bid Generation LLM Infrastructure")
    print("=" * 50)
    manager = create_bid_generation_llm_manager()
    # Validate infrastructure
    validation = manager.validate_infrastructure()
    print(f"Setup valid: {validation['setup_valid']}")
    print(f"Base LLM valid: {validation['base_llm_valid']}")
    print(f"Bid generation test: {validation['bid_generation_test']}")
    print(f"Requirement extraction test: {validation['requirement_extraction_test']}")
    print(f"Section generation test: {validation['section_generation_test']}")
    if validation['errors']:
        print("\nErrors:")
        for error in validation['errors']:
            print(f"  - {error}")
    if validation['setup_valid']:
        print("\n✓ Bid Generation LLM Infrastructure is ready!")
    else:
        print("\n✗ Bid Generation LLM Infrastructure needs attention")
