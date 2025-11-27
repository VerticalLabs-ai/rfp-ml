"""
AI-powered Q&A analyzer for extracting insights and categorizing RFP questions.
"""
import os
import logging
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)


class QAAnalyzer:
    """
    Analyzes RFP Q&A entries to extract:
    - Category (technical, pricing, scope, timeline, compliance)
    - Key insights
    - Related proposal sections that may be affected
    """

    CATEGORIES = [
        "technical",      # Technical requirements, specifications
        "pricing",        # Pricing, costs, budget questions
        "scope",          # Scope of work, deliverables
        "timeline",       # Deadlines, milestones, schedules
        "compliance",     # Compliance requirements, certifications
        "submission",     # Proposal submission requirements
        "evaluation",     # Evaluation criteria
        "other",          # Other/uncategorized
    ]

    PROPOSAL_SECTIONS = [
        "executive_summary",
        "technical_approach",
        "management_approach",
        "past_performance",
        "pricing_volume",
        "compliance_matrix",
        "staffing_plan",
        "quality_assurance",
        "risk_management",
    ]

    def __init__(self, llm_config=None):
        """
        Initialize the Q&A analyzer.

        Args:
            llm_config: Optional LLM configuration. If not provided, uses default.
        """
        self.llm_config = llm_config
        self._llm_client = None

    def _get_llm_client(self):
        """Get or create LLM client."""
        if self._llm_client is None:
            try:
                from src.config.llm_config import get_llm_client
                self._llm_client = get_llm_client()
            except Exception as e:
                logger.warning(f"Could not initialize LLM client: {e}")
                return None
        return self._llm_client

    async def analyze(
        self,
        question_text: str,
        answer_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a Q&A entry.

        Args:
            question_text: The question text
            answer_text: The answer text (if available)

        Returns:
            Dict with:
                - category: str
                - insights: List[str]
                - related_sections: List[str]
        """
        # Try LLM-based analysis first
        llm_client = self._get_llm_client()
        if llm_client:
            try:
                return await self._analyze_with_llm(question_text, answer_text)
            except Exception as e:
                logger.warning(f"LLM analysis failed, falling back to rule-based: {e}")

        # Fallback to rule-based analysis
        return self._analyze_rule_based(question_text, answer_text)

    async def _analyze_with_llm(
        self,
        question_text: str,
        answer_text: Optional[str]
    ) -> Dict[str, Any]:
        """Analyze using LLM."""
        llm_client = self._get_llm_client()

        prompt = f"""Analyze this RFP Q&A entry and provide:
1. Category: One of {self.CATEGORIES}
2. Key insights: 2-3 important takeaways that would affect a proposal response
3. Related proposal sections: Which sections from {self.PROPOSAL_SECTIONS} should be updated based on this Q&A

Question: {question_text}
{f"Answer: {answer_text}" if answer_text else "Answer: Not yet provided"}

Respond in JSON format:
{{
    "category": "category_name",
    "insights": ["insight1", "insight2"],
    "related_sections": ["section1", "section2"]
}}
"""

        response = await llm_client.generate(prompt)

        # Parse JSON response
        try:
            # Extract JSON from response if wrapped in markdown
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            result = json.loads(json_str)
            return {
                "category": result.get("category", "other"),
                "insights": result.get("insights", []),
                "related_sections": result.get("related_sections", []),
            }
        except json.JSONDecodeError:
            logger.warning(f"Could not parse LLM response as JSON: {response[:200]}")
            return self._analyze_rule_based(question_text, answer_text)

    def _analyze_rule_based(
        self,
        question_text: str,
        answer_text: Optional[str]
    ) -> Dict[str, Any]:
        """
        Rule-based fallback analysis using keywords.
        """
        combined_text = (question_text + " " + (answer_text or "")).lower()

        # Determine category based on keywords
        category = self._categorize_by_keywords(combined_text)

        # Extract basic insights
        insights = self._extract_basic_insights(question_text, answer_text)

        # Determine related sections
        related_sections = self._determine_related_sections(category, combined_text)

        return {
            "category": category,
            "insights": insights,
            "related_sections": related_sections,
        }

    def _categorize_by_keywords(self, text: str) -> str:
        """Categorize Q&A based on keywords."""
        keyword_map = {
            "technical": [
                "technical", "system", "software", "hardware", "integration",
                "architecture", "specification", "requirement", "technology",
                "platform", "interface", "api", "database", "security"
            ],
            "pricing": [
                "price", "cost", "budget", "rate", "labor", "material",
                "fee", "payment", "invoice", "billing", "discount", "ceiling"
            ],
            "scope": [
                "scope", "deliverable", "task", "work", "service",
                "responsibility", "duty", "obligation", "include", "exclude"
            ],
            "timeline": [
                "deadline", "date", "schedule", "timeline", "milestone",
                "duration", "period", "when", "time", "extension"
            ],
            "compliance": [
                "compliance", "regulation", "certification", "clearance",
                "requirement", "mandatory", "shall", "must", "license"
            ],
            "submission": [
                "submit", "submission", "format", "page", "font", "proposal",
                "upload", "portal", "attachment", "document"
            ],
            "evaluation": [
                "evaluation", "criteria", "score", "weight", "factor",
                "rating", "assess", "review", "selection"
            ],
        }

        max_score = 0
        best_category = "other"

        for category, keywords in keyword_map.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > max_score:
                max_score = score
                best_category = category

        return best_category

    def _extract_basic_insights(
        self,
        question_text: str,
        answer_text: Optional[str]
    ) -> List[str]:
        """Extract basic insights from Q&A."""
        insights = []

        # Check for deadline changes
        if answer_text and any(word in answer_text.lower() for word in ["extended", "postponed", "changed"]):
            insights.append("Deadline or timeline may have been modified")

        # Check for clarifications
        if "clarif" in question_text.lower():
            insights.append("Clarification provided on requirements")

        # Check for scope changes
        if answer_text and any(word in answer_text.lower() for word in ["added", "removed", "changed", "modified"]):
            insights.append("Scope or requirements may have been modified")

        # Check for mandatory requirements
        if answer_text and any(word in answer_text.lower() for word in ["mandatory", "required", "shall", "must"]):
            insights.append("Contains mandatory compliance requirement")

        # If no insights, provide generic one
        if not insights:
            insights.append("Review question for potential impact on proposal")

        return insights[:3]  # Limit to 3 insights

    def _determine_related_sections(self, category: str, text: str) -> List[str]:
        """Determine which proposal sections are affected."""
        category_section_map = {
            "technical": ["technical_approach", "compliance_matrix"],
            "pricing": ["pricing_volume", "executive_summary"],
            "scope": ["technical_approach", "management_approach", "staffing_plan"],
            "timeline": ["management_approach", "staffing_plan"],
            "compliance": ["compliance_matrix", "technical_approach"],
            "submission": ["executive_summary"],
            "evaluation": ["executive_summary", "technical_approach"],
            "other": ["compliance_matrix"],
        }

        sections = set(category_section_map.get(category, ["compliance_matrix"]))

        # Add sections based on specific keywords
        if "past performance" in text or "experience" in text:
            sections.add("past_performance")
        if "staff" in text or "personnel" in text or "team" in text:
            sections.add("staffing_plan")
        if "quality" in text or "qa" in text:
            sections.add("quality_assurance")
        if "risk" in text:
            sections.add("risk_management")

        return list(sections)[:4]  # Limit to 4 sections


async def analyze_qa_batch(
    qa_items: List[Dict[str, str]],
    analyzer: Optional[QAAnalyzer] = None
) -> List[Dict[str, Any]]:
    """
    Analyze a batch of Q&A items.

    Args:
        qa_items: List of dicts with 'question' and optional 'answer' keys
        analyzer: Optional QAAnalyzer instance

    Returns:
        List of analysis results
    """
    if analyzer is None:
        analyzer = QAAnalyzer()

    results = []
    for qa in qa_items:
        analysis = await analyzer.analyze(
            qa.get("question", ""),
            qa.get("answer")
        )
        results.append(analysis)

    return results
