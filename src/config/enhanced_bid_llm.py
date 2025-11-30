"""
Enhanced Bid Generation LLM with better fallback content generation
Optimized for government RFP bid writing when local models produce poor quality
"""

import logging
from dataclasses import dataclass
from typing import Any

from src.bid_generation.style_manager import style_manager
from src.config.llm_config import LLMManager


@dataclass
class EnhancedBidConfig:
    """Enhanced configuration for bid generation"""

    company_name: str = "AquaServe Solutions"
    years_experience: int = 10
    key_certifications: list[str] = None
    service_areas: list[str] = None

    def __post_init__(self):
        if self.key_certifications is None:
            self.key_certifications = [
                "FDA Approved Facility",
                "ISO 9001:2015 Certified",
                "OSHA Compliant",
                "EPA Water Quality Standards",
                "DOT Transportation Certified",
            ]
        if self.service_areas is None:
            self.service_areas = [
                "Bottled Water Delivery",
                "Construction Services",
                "Logistics and Delivery",
                "Facility Management",
                "Supply Chain Solutions",
            ]


class EnhancedBidLLMManager:
    """
    Enhanced LLM manager with high-quality fallback content generation
    Uses template-based generation when LLM quality is poor
    """

    def __init__(self, config: EnhancedBidConfig | None = None):
        self.config = config or EnhancedBidConfig()
        self.llm_manager = LLMManager()
        self.logger = self._setup_logger()
        # Content templates for high-quality fallbacks
        self.content_templates = self._initialize_templates()
        self.logger.info("Enhanced Bid LLM Manager initialized")

    def _setup_logger(self) -> logging.Logger:
        """Setup logging"""
        logger = logging.getLogger("enhanced_bid_llm")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _initialize_templates(self) -> dict[str, str]:
        """Initialize high-quality content templates"""
        return {
            "executive_summary": """
{company_name} is pleased to submit our proposal for {service_description}. With {years_experience} years of proven experience in {service_area}, we bring unmatched expertise and reliability to meet your requirements.
Our comprehensive approach ensures full compliance with all specifications while delivering exceptional value. We are committed to maintaining the highest standards of quality, safety, and customer service throughout the contract duration.
Key advantages of partnering with {company_name} include our established track record, certified processes, and dedicated account management. We guarantee timely delivery, competitive pricing, and proactive communication to ensure your complete satisfaction.
We look forward to the opportunity to serve your organization and exceed your expectations.
            """,
            "company_qualifications": """
{company_name} has been a leading provider of {service_area} services for {years_experience} years, serving government and commercial clients nationwide. Our qualifications include:
CERTIFICATIONS & COMPLIANCE:
{certifications_list}
EXPERIENCE & CAPABILITIES:
• Extensive experience with government contracting requirements
• Proven track record of on-time, on-budget project delivery
• Comprehensive quality assurance and safety programs
• Advanced logistics and inventory management systems
• 24/7 customer support and emergency response capabilities
PAST PERFORMANCE:
Our team has successfully completed numerous similar contracts, consistently receiving excellent performance ratings. We maintain strong relationships with suppliers and subcontractors to ensure reliable service delivery.
FINANCIAL STABILITY:
{company_name} maintains strong financial standing with adequate bonding capacity and insurance coverage to support contract requirements.
            """,
            "technical_approach": """
Our technical approach for {service_description} is designed to ensure seamless execution and full compliance with all requirements:
METHODOLOGY:
1. Initial Assessment: Comprehensive review of all requirements and site conditions
2. Implementation Planning: Detailed project schedule and resource allocation
3. Quality Assurance: Multi-level quality control processes
4. Performance Monitoring: Real-time tracking and reporting systems
DELIVERY PROCESS:
• Systematic ordering and inventory management
• Scheduled delivery routes optimized for efficiency
• Real-time tracking and notification systems
• Emergency response protocols for urgent needs
QUALITY CONTROL:
All services will meet or exceed specified standards. Our quality control program includes regular inspections, documentation, and corrective action procedures.
RISK MANAGEMENT:
We have identified potential risks and developed mitigation strategies to ensure uninterrupted service delivery throughout the contract period.
PROJECT MANAGEMENT:
A dedicated account manager will serve as your primary point of contact, ensuring clear communication and prompt resolution of any issues.
            """,
        }

    def generate_bid_section(
        self,
        section_type: str,
        rfp_context: str,
        requirements: dict[str, Any],
        max_words: int = 300,
    ) -> dict[str, Any]:
        """
        Generate high-quality bid section with enhanced fallback system
        """
        self.logger.info(f"Generating {section_type} section")
        try:
            # First try LLM generation
            llm_result = self._try_llm_generation(
                section_type, rfp_context, requirements, max_words
            )
            # Check if LLM result is good quality
            if self._is_good_quality(llm_result):
                self.logger.info(f"LLM generated quality content for {section_type}")
                return llm_result
            # Fall back to template-based generation
            self.logger.info(f"Using template-based generation for {section_type}")
            return self._generate_from_template(
                section_type, rfp_context, requirements, max_words
            )
        except Exception as e:
            self.logger.error(f"Error generating {section_type}: {e}")
            return self._generate_from_template(
                section_type, rfp_context, requirements, max_words
            )

    def refine_content(self, text: str, instruction: str, context: str = "") -> str:
        """Refine existing content based on user instruction."""

        prompt = f"""
You are a professional government proposal editor.
Original Text:
"{text}"

Context: {context}

Instruction: {instruction}

Please rewrite the text to satisfy the instruction while maintaining professional tone and accuracy.
Refined Text:
"""
        response = self.llm_manager.generate_text(
            prompt,
            task_type="refinement",
            max_tokens=len(text.split()) * 2 + 100,
            temperature=0.7,
        )
        return response.strip()

    def _try_llm_generation(
        self,
        section_type: str,
        rfp_context: str,
        requirements: dict[str, Any],
        max_words: int,
    ) -> dict[str, Any]:
        """Attempt LLM generation with optimized prompting"""
        # Create enhanced prompt
        prompt = self._create_enhanced_prompt(
            section_type, rfp_context, requirements, max_words
        )
        # Generate with LLM
        content = self.llm_manager.generate_text(
            prompt,
            task_type="bid_generation",
            max_tokens=max_words * 2,
            temperature=0.8,
        )
        return {
            "section_type": section_type,
            "content": content.strip(),
            "word_count": len(content.split()),
            "requirements_addressed": list(requirements.keys()),
            "confidence_score": self._calculate_confidence(content, requirements),
            "generation_method": "llm",
            "status": "generated",
        }

    def _create_enhanced_prompt(
        self,
        section_type: str,
        rfp_context: str,
        requirements: dict[str, Any],
        max_words: int,
    ) -> str:
        """Create enhanced prompts for better LLM output with Style Tuning"""

        # Retrieve style examples
        style_examples = style_manager.retrieve_examples(rfp_context, section_type, k=2)
        style_context = ""
        if style_examples:
            style_context = "\nSTYLE REFERENCE (Mimic this tone and structure):\n"
            for i, ex in enumerate(style_examples):
                style_context += f"--- Example {i+1} ---\n{ex.text[:500]}...\n"

        base_context = f"""
Company: {self.config.company_name}
Experience: {self.config.years_experience} years
Certifications: {', '.join(self.config.key_certifications[:3])}
RFP Context: {rfp_context}
Requirements: {self._format_requirements(requirements)}
{style_context}
"""
        prompts = {
            "executive_summary": f"""
Write a professional executive summary for a government bid proposal.
{base_context}
Create a compelling 3-paragraph executive summary that:
1. States our understanding and commitment to the project
2. Highlights our key qualifications and competitive advantages
3. Demonstrates confidence in successful project delivery
Write in a professional, confident tone matching the Style Reference if provided. Maximum {max_words} words.
Executive Summary:
            """,
            "company_qualifications": f"""
Write a company qualifications section for a government bid.
{base_context}
Create a qualifications section that covers:
1. Company experience and background
2. Relevant certifications and compliance
3. Past performance on similar projects
4. Financial stability and capacity
Write in a professional, detailed tone. Maximum {max_words} words.
Company Qualifications:
            """,
            "technical_approach": f"""
Write a technical approach section for a government bid.
{base_context}
Describe our technical approach including:
1. Methodology and implementation plan
2. Quality assurance processes
3. Risk management strategies
4. Project management approach
Write in a detailed, technical tone. Maximum {max_words} words.
Technical Approach:
            """,
        }
        return prompts.get(
            section_type,
            f"""
Write a {section_type} section for a government bid proposal.
{base_context}
Maximum {max_words} words.
        """,
        )

    def _is_good_quality(self, result: dict[str, Any]) -> bool:
        """Check if LLM result meets quality standards"""
        content = result.get("content", "")
        word_count = result.get("word_count", 0)
        # Quality criteria
        has_sufficient_length = word_count >= 30
        has_complete_sentences = content.count(".") >= 2
        not_repetitive = len(set(content.split())) > word_count * 0.6
        contains_relevant_terms = any(
            term in content.lower()
            for term in [
                "experience",
                "qualified",
                "deliver",
                "service",
                "comply",
                "quality",
            ]
        )
        return (
            has_sufficient_length
            and has_complete_sentences
            and not_repetitive
            and contains_relevant_terms
        )

    def _generate_from_template(
        self,
        section_type: str,
        rfp_context: str,
        requirements: dict[str, Any],
        max_words: int,
    ) -> dict[str, Any]:
        """Generate content using high-quality templates"""
        template = self.content_templates.get(section_type, "")
        if not template:
            template = (
                f"Our company is well-qualified to provide {rfp_context} services."
            )
        # Extract service information from RFP context
        service_description = self._extract_service_description(rfp_context)
        service_area = self._determine_service_area(rfp_context)
        # Format template
        content = template.format(
            company_name=self.config.company_name,
            years_experience=self.config.years_experience,
            service_description=service_description,
            service_area=service_area,
            certifications_list=self._format_certifications(),
        ).strip()
        # Trim to word limit
        words = content.split()
        if len(words) > max_words:
            content = " ".join(words[:max_words])
            # Ensure ending with complete sentence
            if not content.endswith("."):
                last_period = content.rfind(".")
                if last_period > len(content) * 0.8:
                    content = content[: last_period + 1]
        return {
            "section_type": section_type,
            "content": content,
            "word_count": len(content.split()),
            "requirements_addressed": list(requirements.keys()),
            "confidence_score": 0.85,  # High confidence for template-based
            "generation_method": "template",
            "status": "generated",
        }

    def _extract_service_description(self, rfp_context: str) -> str:
        """Extract service description from RFP context"""
        context_lower = rfp_context.lower()
        if "water" in context_lower:
            return "bottled water delivery services"
        elif "construction" in context_lower:
            return "construction and maintenance services"
        elif "delivery" in context_lower:
            return "logistics and delivery services"
        else:
            return "professional services"

    def _determine_service_area(self, rfp_context: str) -> str:
        """Determine primary service area from context"""
        context_lower = rfp_context.lower()
        for area in self.config.service_areas:
            if any(keyword in context_lower for keyword in area.lower().split()):
                return area
        return "Professional Services"

    def _format_certifications(self) -> str:
        """Format certifications for template"""
        return "\n".join(f"• {cert}" for cert in self.config.key_certifications)

    def _format_requirements(self, requirements: dict[str, Any]) -> str:
        """Format requirements for prompts"""
        if not requirements:
            return "General service requirements"
        return "; ".join(f"{k}: {v}" for k, v in requirements.items())

    def _calculate_confidence(
        self, content: str, requirements: dict[str, Any]
    ) -> float:
        """Calculate confidence score for generated content"""
        score = 0.3  # Base score
        if len(content) > 50:
            score += 0.2
        if content.count(".") >= 2:
            score += 0.2
        if any(req_key.lower() in content.lower() for req_key in requirements.keys()):
            score += 0.2
        if any(
            term in content.lower() for term in ["experience", "qualified", "certified"]
        ):
            score += 0.1
        return min(score, 1.0)

    def extract_requirements(self, rfp_text: str) -> dict[str, Any]:
        """Extract requirements with both LLM and rule-based approaches"""
        # Try LLM extraction first
        try:
            llm_requirements = self._llm_extract_requirements(rfp_text)
            if llm_requirements:
                return llm_requirements
        except Exception as e:
            self.logger.warning(f"LLM requirement extraction failed: {e}")
        # Fall back to rule-based extraction
        return self._rule_based_extraction(rfp_text)

    def _llm_extract_requirements(self, rfp_text: str) -> dict[str, Any]:
        """Extract requirements using LLM"""
        prompt = f"""
Analyze this RFP text and extract key requirements:
{rfp_text[:1000]}
List the main requirements in this format:
- Duration: [contract length]
- Frequency: [delivery frequency]
- Standards: [quality/compliance standards]
- Insurance: [insurance requirements]
- Experience: [experience requirements]
Requirements:
        """
        response = self.llm_manager.generate_text(
            prompt, task_type="structured_extraction", max_tokens=200, temperature=0.3
        )
        return self._parse_llm_requirements(response)

    def _rule_based_extraction(self, rfp_text: str) -> dict[str, Any]:
        """Extract requirements using rule-based approach"""
        requirements = {}
        text_lower = rfp_text.lower()
        # Duration extraction
        if "month" in text_lower:
            if "24" in rfp_text or "two year" in text_lower:
                requirements["duration"] = "24 months"
            elif "12" in rfp_text or "one year" in text_lower:
                requirements["duration"] = "12 months"
        # Frequency extraction
        if "weekly" in text_lower:
            requirements["delivery_frequency"] = "weekly"
        elif "monthly" in text_lower:
            requirements["delivery_frequency"] = "monthly"
        elif "daily" in text_lower:
            requirements["delivery_frequency"] = "daily"
        # Standards extraction
        if "fda" in text_lower:
            requirements["quality_standards"] = "FDA compliance required"
        if "iso" in text_lower:
            requirements["quality_standards"] = "ISO certification required"
        # Insurance extraction
        if "insurance" in text_lower and "liability" in text_lower:
            requirements["insurance"] = "General liability insurance required"
        # Experience extraction
        if "experience" in text_lower:
            if "5 year" in text_lower:
                requirements["experience"] = "Minimum 5 years experience"
            elif "year" in text_lower:
                requirements["experience"] = "Relevant experience required"
        return requirements

    def _parse_llm_requirements(self, response: str) -> dict[str, Any]:
        """Parse LLM response into requirements dictionary"""
        requirements = {}
        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if ":" in line and line.startswith("-"):
                key_value = line[1:].split(":", 1)
                if len(key_value) == 2:
                    key = key_value[0].strip().lower()
                    value = key_value[1].strip()
                    if value and value != "[" and len(value) > 5:
                        requirements[key] = value
        return requirements

    def validate_infrastructure(self) -> dict[str, Any]:
        """Validate the enhanced infrastructure"""
        validation_results = {
            "base_llm_operational": False,
            "template_system_ready": False,
            "content_generation_test": False,
            "requirements_extraction_test": False,
            "overall_status": "pending",
        }
        try:
            # Test base LLM
            base_validation = self.llm_manager.validate_setup()
            validation_results["base_llm_operational"] = base_validation.get(
                "setup_valid", False
            )
            # Test template system
            validation_results["template_system_ready"] = (
                len(self.content_templates) > 0
            )
            # Test content generation
            test_result = self.generate_bid_section(
                "executive_summary",
                "Government bottled water delivery service",
                {"duration": "12 months"},
                max_words=100,
            )
            validation_results["content_generation_test"] = (
                test_result["status"] == "generated"
                and test_result["word_count"] > 20
                and test_result["confidence_score"] > 0.7
            )
            # Test requirements extraction
            test_requirements = self.extract_requirements(
                "The contractor must provide weekly water delivery for 12 months with FDA compliance."
            )
            validation_results["requirements_extraction_test"] = (
                len(test_requirements) > 0
            )
            # Overall status
            passed_tests = sum(
                validation_results[key]
                for key in validation_results
                if key != "overall_status"
            )
            total_tests = len(validation_results) - 1
            if passed_tests >= total_tests * 0.75:
                validation_results["overall_status"] = "ready"
            elif passed_tests >= total_tests * 0.5:
                validation_results["overall_status"] = "mostly_ready"
            else:
                validation_results["overall_status"] = "needs_work"
            return validation_results
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            validation_results["overall_status"] = "error"
            validation_results["error"] = str(e)
            return validation_results


# Convenience function
def create_enhanced_bid_manager(
    config: EnhancedBidConfig | None = None,
) -> EnhancedBidLLMManager:
    """Create enhanced bid LLM manager"""
    return EnhancedBidLLMManager(config)


if __name__ == "__main__":
    print("🚀 ENHANCED BID LLM MANAGER TEST")
    print("=" * 50)
    # Create manager
    manager = create_enhanced_bid_manager()
    # Validate infrastructure
    validation = manager.validate_infrastructure()
    print(f"Base LLM Operational: {validation['base_llm_operational']}")
    print(f"Template System Ready: {validation['template_system_ready']}")
    print(f"Content Generation Test: {validation['content_generation_test']}")
    print(f"Requirements Extraction Test: {validation['requirements_extraction_test']}")
    print(f"Overall Status: {validation['overall_status']}")
    if validation["overall_status"] in ["ready", "mostly_ready"]:
        print("\n✅ Enhanced Bid LLM Manager is operational!")
        # Test generation
        print("\nTesting bid section generation...")
        result = manager.generate_bid_section(
            "executive_summary",
            "Government bottled water delivery for 24 months",
            {"duration": "24 months", "frequency": "weekly"},
            max_words=150,
        )
        print(
            f"Generated {result['word_count']} words using {result['generation_method']}"
        )
        print(f"Confidence: {result['confidence_score']:.2f}")
        print(f"Content preview: {result['content'][:100]}...")
    else:
        print("\n❌ Enhanced Bid LLM Manager needs attention")
