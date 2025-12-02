"""
Fixed Bid Document Generator for AI-powered RFP bid generation system.
Integrates RAG, Compliance Matrix, and Pricing Engine outputs into structured bid documents.
Supports Claude 4.5 with extended thinking mode for comprehensive proposal generation.
"""
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import markdown
import pandas as pd

# Import path configuration
from src.config.paths import PathConfig
from src.utils.category import determine_category

from .visualizer import Visualizer


class ProposalGenerationMode(Enum):
    """Mode for proposal content generation"""
    TEMPLATE = "template"  # Use template-based generation (fast, basic)
    CLAUDE_STANDARD = "claude_standard"  # Claude Sonnet without thinking
    CLAUDE_ENHANCED = "claude_enhanced"  # Claude Sonnet with thinking (recommended)
    CLAUDE_PREMIUM = "claude_premium"  # Claude Opus with thinking (highest quality)


@dataclass
class ProposalGenerationOptions:
    """Options for proposal generation"""
    mode: ProposalGenerationMode = ProposalGenerationMode.TEMPLATE
    enable_thinking: bool = True
    thinking_budget: int = 10000
    enhance_sections: list | None = None  # None = enhance all sections


class BidDocumentGenerator:
    """
    Generate complete, structured bid documents integrating all pipeline components.
    Supports Claude 4.5 with extended thinking for comprehensive proposals.
    """
    def __init__(
        self,
        rag_engine=None,
        compliance_generator=None,
        pricing_engine=None,
        templates_dir: str | None = None,
        content_library_dir: str | None = None,
        output_dir: str | None = None,
        proposal_options: ProposalGenerationOptions | None = None,
        anthropic_api_key: str | None = None,
    ):
        """
        Initialize bid document generator.

        Args:
            rag_engine: RAG engine for context retrieval
            compliance_generator: Compliance matrix generator
            pricing_engine: Pricing engine
            templates_dir: Directory for templates
            content_library_dir: Directory for content library
            output_dir: Output directory for generated documents
            proposal_options: Options for proposal generation (mode, thinking, etc.)
            anthropic_api_key: API key for Claude (uses env var if not provided)
        """
        # Ensure PathConfig directories are initialized
        PathConfig.ensure_directories()

        self.rag_engine = rag_engine
        self.compliance_generator = compliance_generator
        self.pricing_engine = pricing_engine
        self.templates_dir = templates_dir or str(PathConfig.TEMPLATES_DIR)
        self.content_library_dir = content_library_dir or str(PathConfig.CONTENT_LIBRARY_DIR)
        self.output_dir = output_dir or str(PathConfig.BID_DOCUMENTS_DIR)
        self.proposal_options = proposal_options or ProposalGenerationOptions()
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

        # Initialize visualizer
        self.visualizer = Visualizer(output_dir=os.path.join(self.output_dir, "assets"))

        # Create directories
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.content_library_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize logging
        self.logger = logging.getLogger(__name__)

        # Initialize enhanced proposal generator if Claude mode is selected
        self.enhanced_generator = None
        self._initialize_enhanced_generator()

        # Load content library
        self.content_library = self._load_content_library()

    def _initialize_enhanced_generator(self):
        """Initialize the enhanced proposal generator for Claude modes."""
        if self.proposal_options.mode == ProposalGenerationMode.TEMPLATE:
            return  # No enhanced generator needed for template mode

        try:
            from .enhanced_proposal_generator import (
                ProposalQuality,
                create_enhanced_proposal_generator,
            )

            # Map mode to quality
            quality_map = {
                ProposalGenerationMode.CLAUDE_STANDARD: "standard",
                ProposalGenerationMode.CLAUDE_ENHANCED: "enhanced",
                ProposalGenerationMode.CLAUDE_PREMIUM: "premium",
            }
            quality = quality_map.get(self.proposal_options.mode, "enhanced")

            self.enhanced_generator = create_enhanced_proposal_generator(
                quality=quality,
                enable_thinking=self.proposal_options.enable_thinking,
                thinking_budget=self.proposal_options.thinking_budget,
                rag_engine=self.rag_engine,
                api_key=self.anthropic_api_key,
            )

            if self.enhanced_generator.is_available():
                self.logger.info(f"Enhanced proposal generator initialized in {quality} mode")
            else:
                self.logger.warning("Enhanced generator initialized but Claude not available - falling back to template mode")
                self.enhanced_generator = None

        except ImportError as e:
            self.logger.warning(f"Could not import enhanced proposal generator: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to initialize enhanced generator: {e}")
    def _load_content_library(self) -> dict[str, Any]:
        """Load or create content library with reusable content blocks."""
        # Company profile - LOAD from file if it exists, otherwise create default
        company_profile_path = os.path.join(self.content_library_dir, "company_profile.json")
        if os.path.exists(company_profile_path):
            try:
                with open(company_profile_path, 'r') as f:
                    company_profile = json.load(f)
                self.logger.info(f"Loaded company profile from {company_profile_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load company profile: {e}, using defaults")
                company_profile = self._get_default_company_profile()
        else:
            # Create default profile if file doesn't exist
            company_profile = self._get_default_company_profile()
            with open(company_profile_path, 'w') as f:
                json.dump(company_profile, f, indent=2)
            self.logger.info(f"Created default company profile at {company_profile_path}")
        
        # Normalize company profile structure for backward compatibility
        company_profile = self._normalize_company_profile(company_profile)
        # Standard clauses
        standard_clauses_path = os.path.join(self.content_library_dir, "standard_clauses.json")
        standard_clauses = {
            "terms_and_conditions": {
                "payment_terms": "Net 30 days from invoice date. Progress payments available for contracts exceeding $100,000.",
                "warranty": "We provide comprehensive warranty coverage for all deliverables as specified in the contract terms.",
                "performance_guarantee": "We guarantee performance according to all specified metrics and will provide remediation at no additional cost for any non-compliance.",
                "liability": "Professional liability insurance maintained at minimum $2M coverage as required by federal regulations.",
                "compliance": "Full compliance with all applicable federal, state, and local regulations including labor standards and safety requirements."
            },
            "technical_approach": {
                "methodology": "Our proven methodology combines industry best practices with innovative solutions tailored to government requirements.",
                "quality_assurance": "Comprehensive quality management system with regular audits, performance monitoring, and continuous improvement processes.",
                "project_management": "Dedicated project management using PMI standards with regular reporting, milestone tracking, and stakeholder communication.",
                "risk_management": "Proactive risk identification and mitigation strategies with contingency planning for all critical project elements.",
                "security": "Robust security protocols including background checks, secure facilities, and compliance with all federal security requirements."
            }
        }
        if not os.path.exists(standard_clauses_path):
            with open(standard_clauses_path, 'w') as f:
                json.dump(standard_clauses, f, indent=2)
        content_library = {
            "company_profile": company_profile,
            "standard_clauses": standard_clauses
        }
        self.logger.info(f"Content library loaded with {len(content_library)} sections")
        return content_library

    def _get_default_company_profile(self) -> dict[str, Any]:
        """Get default company profile structure using IBYTE Enterprises data."""
        # Default to IBYTE Enterprises real data if company_profile.json doesn't exist
        return {
            "company_name": "IBYTE Enterprises, LLC",
            "legal_name": "IBYTE Enterprises, LLC",
            "established": "2022",
            "established_year": 2022,
            "headquarters": "Austin, TX",
            "address": "1801 E 51st St. Ste 365-359, Austin, TX 78723",
            "employees": "1-10",
            "employee_count": "1-10",
            "website": "https://www.ibyteent.com",
            "certifications": [
                "Small Business",
                "Woman Owned Small Business (WOSB)",
                "PMP Certificate #3889480"
            ],
            "core_competencies": [
                "IT Infrastructure & Cloud Services",
                "Project Management",
                "Software Development",
                "Digital Transformation",
                "Construction Management",
                "Data Analytics",
                "Government Contracting"
            ],
            "past_performance": []  # Empty - should be populated from actual contract history
        }

    def _normalize_company_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        """Normalize company profile to expected structure, preserving all fields."""
        # Handle different JSON structures and preserve all available data
        normalized = {
            "company_name": profile.get("company_name") or profile.get("name", "Unknown Company"),
            "legal_name": profile.get("legal_name") or profile.get("company_name") or profile.get("name", ""),
            "established": str(profile.get("established") or profile.get("established_year", "Unknown")),
            "established_year": profile.get("established_year") or (int(profile.get("established", 0)) if str(profile.get("established", "")).isdigit() else None),
            "headquarters": profile.get("headquarters") or profile.get("address", "Unknown"),
            "address": profile.get("address") or profile.get("headquarters", ""),
            "employees": str(profile.get("employees") or profile.get("employee_count", "Unknown")),
            "employee_count": profile.get("employee_count") or profile.get("employees", ""),
            "website": profile.get("website", ""),
            "certifications": profile.get("certifications", []),
            "core_competencies": profile.get("core_competencies", []),
            "past_performance": profile.get("past_performance", []),
            # Preserve additional fields that might be useful
            "primary_contact": profile.get("primary_contact", {}),
            "identifiers": profile.get("identifiers", {}),
            "naics_codes": profile.get("naics_codes", []),
            "nigp_codes": profile.get("nigp_codes", []),
        }
        return normalized

    def _determine_category(self, rfp_data: dict[str, Any]) -> str:
        """Determine RFP category for appropriate content selection."""
        return determine_category(rfp_data)
    def _generate_executive_summary(self, rfp_data: dict[str, Any],
                                  compliance_summary: dict[str, Any],
                                  pricing_result: Any,
                                  compliance_matrix: dict[str, Any] | None = None) -> str:
        """Generate executive summary using available data or Claude enhanced generation."""
        # Try enhanced generation first if available
        if self.enhanced_generator and self.enhanced_generator.is_available():
            return self._generate_enhanced_executive_summary(
                rfp_data, compliance_summary, pricing_result, compliance_matrix
            )

        # Fallback to template-based generation
        return self._generate_template_executive_summary(
            rfp_data, compliance_summary, pricing_result
        )

    def _generate_enhanced_executive_summary(
        self,
        rfp_data: dict[str, Any],
        compliance_summary: dict[str, Any],
        pricing_result: Any,
        compliance_matrix: dict[str, Any] | None = None,
    ) -> str:
        """Generate executive summary using Claude with thinking mode."""
        # Prepare pricing data
        pricing_data = None
        if pricing_result:
            pricing_data = {
                "recommended_price": getattr(pricing_result, 'total_price', 0),
                "recommended_strategy": getattr(pricing_result, 'pricing_strategy', 'competitive'),
                "margin_percentage": getattr(pricing_result, 'margin_percentage', 0),
                "confidence_score": getattr(pricing_result, 'confidence_score', 0),
                "justification": getattr(pricing_result, 'justification', ''),
            }

        # Prepare compliance data including compliance signals
        compliance_data = None
        if compliance_matrix:
            compliance_data = compliance_matrix
        elif compliance_summary:
            compliance_data = {"compliance_summary": compliance_summary}

        # Add compliance signals if available
        if hasattr(self, '_current_compliance_signals') and self._current_compliance_signals:
            if compliance_data:
                compliance_data["compliance_signals"] = self._current_compliance_signals
            else:
                compliance_data = {"compliance_signals": self._current_compliance_signals}

        try:
            result = self.enhanced_generator.generate_enhanced_section(
                section_type="executive_summary",
                rfp_data=rfp_data,
                company_profile=self.content_library.get('company_profile', {}),
                compliance_data=compliance_data,
                pricing_data=pricing_data,
                qa_items=getattr(self, '_current_qa_items', None),
                compliance_signals=getattr(self, '_current_compliance_signals', None),
                document_content=getattr(self, '_current_document_content', None),
            )

            if result.get("status") == "success" and result.get("content"):
                self.logger.info(f"Generated enhanced executive summary: {result.get('word_count', 0)} words")
                return result["content"]
            else:
                self.logger.warning(f"Enhanced generation failed: {result.get('error')}, using template")

        except Exception as e:
            self.logger.warning(f"Enhanced executive summary failed: {e}, using template")

        # Fallback to template
        return self._generate_template_executive_summary(
            rfp_data, compliance_summary, pricing_result
        )

    def _generate_template_executive_summary(
        self,
        rfp_data: dict[str, Any],
        compliance_summary: dict[str, Any],
        pricing_result: Any,
    ) -> str:
        """Generate executive summary using template-based approach."""
        title = rfp_data.get('title', 'Government Contract')
        agency = rfp_data.get('agency', 'Government Agency')
        category = self._determine_category(rfp_data)
        summary_parts = []
        # Opening statement
        summary_parts.append(
            f"We are pleased to submit our comprehensive proposal for {title}. "
            f"We have designed a solution that directly addresses {agency}'s "
            f"specific requirements while delivering exceptional value and performance."
        )
        # Compliance highlights
        compliance_rate = compliance_summary.get('compliance_rate', 0) * 100
        if compliance_rate >= 80:
            summary_parts.append(
                f"Our proposal demonstrates {compliance_rate:.0f}% compliance with all identified requirements, "
                f"reflecting our thorough understanding of the project scope and commitment to excellence."
            )
        else:
            summary_parts.append(
                "We have carefully analyzed all requirements and provide detailed responses addressing "
                "the full scope of work with actionable compliance strategies."
            )
        # Pricing highlights
        if hasattr(pricing_result, 'pricing_strategy'):
            pricing_strategy = pricing_result.pricing_strategy
            margin = pricing_result.margin_percentage
            confidence = pricing_result.confidence_score * 100
            summary_parts.append(
                f"Our {pricing_strategy.replace('_', ' ')} pricing approach offers exceptional value "
                f"with a {margin:.0f}% margin that ensures sustainable service delivery. "
                f"This pricing is supported by {confidence:.0f}% confidence based on comprehensive "
                f"market analysis and historical performance data."
            )
        else:
            summary_parts.append(
                "Our competitive pricing approach offers exceptional value "
                "while ensuring sustainable service delivery and compliance with all requirements."
            )
        # Category-specific value proposition
        if category == 'bottled_water':
            summary_parts.append(
                "We specialize in reliable, cost-effective water supply solutions with "
                "24/7 delivery capabilities and comprehensive inventory management."
            )
        elif category == 'construction':
            summary_parts.append(
                "Our construction management expertise encompasses full project lifecycle "
                "from planning through completion with emphasis on safety, quality, and schedule adherence."
            )
        elif category == 'delivery':
            summary_parts.append(
                "We provide comprehensive logistics and delivery services with real-time "
                "tracking, flexible scheduling, and proven reliability for government operations."
            )
        else:
            summary_parts.append(
                "Our proven methodology combines industry best practices with innovative "
                "solutions specifically designed for government contracting requirements."
            )
        # Closing
        summary_parts.append(
            f"We look forward to partnering with {agency} to deliver outstanding results "
            f"that meet your mission-critical objectives while providing exceptional value."
        )
        return " ".join(summary_parts)
    def _generate_schedule_tasks(self, rfp_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate project schedule tasks based on RFP data."""
        # Parse dates from RFP
        posted_date = None
        response_deadline = None
        
        if rfp_data.get('posted_date'):
            try:
                if isinstance(rfp_data['posted_date'], str):
                    posted_date = pd.to_datetime(rfp_data['posted_date']).to_pydatetime()
                else:
                    posted_date = rfp_data['posted_date']
            except Exception:
                pass
        
        if rfp_data.get('response_deadline'):
            try:
                if isinstance(rfp_data['response_deadline'], str):
                    response_deadline = pd.to_datetime(rfp_data['response_deadline']).to_pydatetime()
                else:
                    response_deadline = rfp_data['response_deadline']
            except Exception:
                pass
        
        # Determine project duration based on award amount and category
        # Use RFP award amount, or estimate from description length/complexity if not available
        award_amount = rfp_data.get('award_amount', 0) or rfp_data.get('estimated_value', 0)
        if not award_amount or award_amount == 0:
            # Estimate from description complexity if award amount not available
            description = str(rfp_data.get('description', ''))
            if len(description) > 5000:
                award_amount = 500000  # Large complex project
            elif len(description) > 2000:
                award_amount = 150000  # Medium project
            else:
                award_amount = 50000   # Small project
        category = self._determine_category(rfp_data)
        
        # Estimate project duration based on contract value
        # Small: <50k = 30-60 days, Medium: 50k-500k = 90-180 days, Large: >500k = 180-365 days
        if award_amount < 50000:
            base_duration_days = 60
        elif award_amount < 500000:
            base_duration_days = 120
        else:
            base_duration_days = 240
        
        # Adjust for category
        category_multipliers = {
            'bottled_water': 0.8,  # Ongoing service, shorter initial setup
            'construction': 1.5,   # Longer projects
            'delivery': 0.9,       # Service delivery
            'general': 1.0
        }
        duration_days = int(base_duration_days * category_multipliers.get(category, 1.0))
        
        # Start date: use posted_date if available, otherwise now
        start_date = posted_date if posted_date else datetime.now()
        
        # Generate phase-based schedule
        phases = []
        current_date = start_date
        
        # Phase 1: Kickoff & Planning (10-15% of duration)
        phase1_days = max(7, int(duration_days * 0.12))
        phases.append({
            "task": "Project Kickoff & Planning",
            "start": current_date,
            "end": current_date + timedelta(days=phase1_days)
        })
        current_date += timedelta(days=phase1_days)
        
        # Phase 2: Design/Setup (15-20% of duration)
        phase2_days = max(10, int(duration_days * 0.18))
        phases.append({
            "task": "Design & Setup Phase",
            "start": current_date,
            "end": current_date + timedelta(days=phase2_days)
        })
        current_date += timedelta(days=phase2_days)
        
        # Phase 3: Main Execution (50-60% of duration)
        phase3_days = max(30, int(duration_days * 0.55))
        phases.append({
            "task": "Main Execution Phase",
            "start": current_date,
            "end": current_date + timedelta(days=phase3_days)
        })
        current_date += timedelta(days=phase3_days)
        
        # Phase 4: Quality Assurance & Testing (10-15% of duration)
        phase4_days = max(7, int(duration_days * 0.12))
        phases.append({
            "task": "Quality Assurance & Testing",
            "start": current_date,
            "end": current_date + timedelta(days=phase4_days)
        })
        current_date += timedelta(days=phase4_days)
        
        # Phase 5: Final Delivery & Transition (5-10% of duration)
        phase5_days = max(5, int(duration_days * 0.08))
        phases.append({
            "task": "Final Delivery & Transition",
            "start": current_date,
            "end": current_date + timedelta(days=phase5_days)
        })
        
        return phases

    def _generate_staff_structure(self, rfp_data: dict[str, Any], compliance_matrix: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Generate organization chart staff based on RFP requirements."""
        category = self._determine_category(rfp_data)
        # Use RFP award amount, or estimate from description if not available
        award_amount = rfp_data.get('award_amount', 0) or rfp_data.get('estimated_value', 0)
        if not award_amount or award_amount == 0:
            # Estimate from description complexity if award amount not available
            description = str(rfp_data.get('description', ''))
            if len(description) > 5000:
                award_amount = 500000  # Large complex project
            elif len(description) > 2000:
                award_amount = 150000  # Medium project
            else:
                award_amount = 50000   # Small project
        
        # Base staff structure
        staff = [
            {"name": "Project Manager", "role": "Project Manager", "reports_to": None}
        ]
        
        # Category-specific roles
        if category == 'bottled_water':
            staff.extend([
                {"name": "Operations Manager", "role": "Operations Manager", "reports_to": "Project Manager"},
                {"name": "Quality Assurance Lead", "role": "QA Lead", "reports_to": "Project Manager"},
                {"name": "Delivery Coordinator", "role": "Delivery Coordinator", "reports_to": "Operations Manager"},
                {"name": "Inventory Specialist", "role": "Inventory Specialist", "reports_to": "Operations Manager"},
            ])
        elif category == 'construction':
            staff.extend([
                {"name": "Construction Manager", "role": "Construction Manager", "reports_to": "Project Manager"},
                {"name": "Site Supervisor", "role": "Site Supervisor", "reports_to": "Construction Manager"},
                {"name": "Safety Officer", "role": "Safety Officer", "reports_to": "Project Manager"},
                {"name": "Quality Control Lead", "role": "QC Lead", "reports_to": "Construction Manager"},
            ])
            # Add more staff for larger construction projects
            if award_amount > 500000:
                staff.extend([
                    {"name": "Field Engineer", "role": "Field Engineer", "reports_to": "Construction Manager"},
                    {"name": "Equipment Manager", "role": "Equipment Manager", "reports_to": "Site Supervisor"},
                ])
        elif category == 'delivery':
            staff.extend([
                {"name": "Logistics Manager", "role": "Logistics Manager", "reports_to": "Project Manager"},
                {"name": "Fleet Coordinator", "role": "Fleet Coordinator", "reports_to": "Logistics Manager"},
                {"name": "Route Planner", "role": "Route Planner", "reports_to": "Logistics Manager"},
                {"name": "Customer Service Lead", "role": "Customer Service Lead", "reports_to": "Project Manager"},
            ])
        else:  # general
            staff.extend([
                {"name": "Technical Lead", "role": "Technical Lead", "reports_to": "Project Manager"},
                {"name": "Quality Assurance Lead", "role": "QA Lead", "reports_to": "Project Manager"},
                {"name": "Operations Lead", "role": "Operations Lead", "reports_to": "Project Manager"},
            ])
        
        # Add roles based on project size
        if award_amount > 200000:
            # Larger projects get additional support staff
            staff.append({"name": "Administrative Coordinator", "role": "Admin Coordinator", "reports_to": "Project Manager"})
        
        # Extract additional roles from compliance matrix if available
        if compliance_matrix and isinstance(compliance_matrix, dict):
            requirements = compliance_matrix.get('requirements_and_responses', [])
            # Look for specific role mentions in requirements
            for req in requirements[:10]:  # Check first 10 requirements
                req_text = str(req.get('requirement', '') + ' ' + str(req.get('response', ''))).lower()
                if 'security' in req_text and not any(s['role'].lower() == 'security' for s in staff):
                    staff.append({"name": "Security Specialist", "role": "Security Specialist", "reports_to": "Project Manager"})
                if 'compliance' in req_text and not any(s['role'].lower() == 'compliance' for s in staff):
                    staff.append({"name": "Compliance Officer", "role": "Compliance Officer", "reports_to": "Project Manager"})
        
        return staff

    def _generate_technical_approach(self, rfp_data: dict[str, Any],
                                   compliance_matrix: dict[str, Any],
                                   pricing_data: dict[str, Any] | None = None) -> dict[str, str]:
        """Generate technical approach section with visualizations."""
        category = self._determine_category(rfp_data)

        # Generate visualizations based on actual RFP data
        # 1. Schedule - now uses RFP data
        schedule_tasks = self._generate_schedule_tasks(rfp_data)
        rfp_id = rfp_data.get('rfp_id', rfp_data.get('solicitation_number', 'temp'))
        if not rfp_id or rfp_id == 'temp':
            # Generate a unique ID from title hash
            import hashlib
            title = str(rfp_data.get('title', 'unknown'))
            rfp_id = hashlib.md5(title.encode()).hexdigest()[:16]

        gantt_path = self.visualizer.generate_gantt_chart(schedule_tasks, f"schedule_{rfp_id}.png")
        gantt_rel_path = os.path.relpath(gantt_path, self.output_dir) if gantt_path else ""

        # 2. Org Chart - now uses RFP data
        staff = self._generate_staff_structure(rfp_data, compliance_matrix)
        org_path = self.visualizer.generate_org_chart(staff, f"org_{rfp_id}.png")
        org_rel_path = os.path.relpath(org_path, self.output_dir) if org_path else ""

        # Try enhanced generation for methodology if available
        methodology = self._generate_methodology_content(rfp_data, compliance_matrix, pricing_data, category)

        return {
            "methodology": methodology,
            "project_management": self._generate_project_management_content(rfp_data, compliance_matrix),
            "quality_assurance": self.content_library['standard_clauses']['technical_approach']['quality_assurance'],
            "risk_management": self.content_library['standard_clauses']['technical_approach']['risk_management'],
            "gantt_chart_path": gantt_rel_path,
            "org_chart_path": org_rel_path
        }

    def _generate_methodology_content(
        self,
        rfp_data: dict[str, Any],
        compliance_matrix: dict[str, Any],
        pricing_data: dict[str, Any] | None,
        category: str,
    ) -> str:
        """Generate methodology content using Claude or template."""
        # Try enhanced generation first
        if self.enhanced_generator and self.enhanced_generator.is_available():
            try:
                result = self.enhanced_generator.generate_enhanced_section(
                    section_type="technical_approach",
                    rfp_data=rfp_data,
                    company_profile=self.content_library.get('company_profile', {}),
                    compliance_data=compliance_matrix,
                    pricing_data=pricing_data,
                    qa_items=getattr(self, '_current_qa_items', None),
                    compliance_signals=getattr(self, '_current_compliance_signals', None),
                    document_content=getattr(self, '_current_document_content', None),
                )

                if result.get("status") == "success" and result.get("content"):
                    self.logger.info(f"Generated enhanced technical approach: {result.get('word_count', 0)} words")
                    return result["content"]

            except Exception as e:
                self.logger.warning(f"Enhanced methodology failed: {e}, using template")

        # Fallback to template-based
        if category == 'bottled_water':
            return (
                "Our water supply methodology encompasses comprehensive inventory management, "
                "reliable delivery scheduling, quality assurance testing, and customer service excellence. "
                "We utilize state-of-the-art tracking systems to ensure timely deliveries and maintain "
                "optimal inventory levels at all serviced locations. Our quality assurance program includes "
                "regular testing and compliance with all FDA and EPA regulations."
            )
        elif category == 'construction':
            return (
                "Our construction methodology follows proven project management principles "
                "with emphasis on safety, quality, and schedule adherence. We employ a phased approach "
                "that includes detailed planning, resource allocation, progress monitoring, and quality "
                "checkpoints at each milestone. Our safety program exceeds OSHA requirements and ensures "
                "zero-incident project delivery."
            )
        elif category == 'delivery':
            return (
                "Our delivery methodology combines advanced logistics planning, real-time "
                "tracking systems, and flexible routing optimization. We leverage GPS tracking, "
                "electronic proof of delivery, and automated scheduling to ensure consistent, "
                "reliable service. Our fleet management system optimizes routes for efficiency "
                "while maintaining strict adherence to delivery schedules."
            )
        else:
            return (
                "Our proven methodology combines industry best practices with innovative "
                "solutions tailored to government requirements. We employ a systematic approach "
                "that includes thorough requirements analysis, detailed planning, phased implementation, "
                "and continuous quality monitoring. Our experienced team ensures all deliverables "
                "meet or exceed specified standards."
            )

    def _generate_project_management_content(
        self,
        rfp_data: dict[str, Any],
        compliance_matrix: dict[str, Any],
    ) -> str:
        """Generate project management content using Claude or template."""
        # Try enhanced generation first
        if self.enhanced_generator and self.enhanced_generator.is_available():
            try:
                result = self.enhanced_generator.generate_enhanced_section(
                    section_type="management_approach",
                    rfp_data=rfp_data,
                    company_profile=self.content_library.get('company_profile', {}),
                    compliance_data=compliance_matrix,
                    qa_items=getattr(self, '_current_qa_items', None),
                    compliance_signals=getattr(self, '_current_compliance_signals', None),
                    document_content=getattr(self, '_current_document_content', None),
                )

                if result.get("status") == "success" and result.get("content"):
                    self.logger.info(f"Generated enhanced management approach: {result.get('word_count', 0)} words")
                    return result["content"]

            except Exception as e:
                self.logger.warning(f"Enhanced project management failed: {e}, using template")

        # Fallback to template
        return self.content_library['standard_clauses']['technical_approach']['project_management']
    def _format_pricing_for_document(self, pricing_results: dict[str, Any]) -> dict[str, Any]:
        """Format pricing results for document inclusion."""
        # Find recommended strategy (best confidence score)
        recommended = None
        best_score = 0
        for strategy_name, result in pricing_results.items():
            if hasattr(result, 'confidence_score'):
                score = result.confidence_score
                if score > best_score:
                    best_score = score
                    recommended = result
                    recommended_strategy = strategy_name
        if not recommended:
            # Fallback to first strategy
            recommended = list(pricing_results.values())[0]
            recommended_strategy = list(pricing_results.keys())[0]
        # Format for template - use actual pricing data, derive defaults from RFP if needed
        rfp_award = recommended.total_price if hasattr(recommended, 'total_price') and recommended.total_price else None
        if not rfp_award:
            # Try to get from RFP data as fallback
            rfp_award = recommended.pricing_result.get('award_amount', 0) if hasattr(recommended, 'pricing_result') else None
        
        # Calculate defaults based on RFP award amount if pricing engine didn't provide values
        default_price = rfp_award or 100000
        default_base = int(default_price * 0.75)
        default_profit = default_price - default_base
        
        formatted_pricing = {
            "recommended_price": getattr(recommended, 'total_price', default_price),
            "recommended_strategy": recommended_strategy,
            "margin_percentage": getattr(recommended, 'margin_percentage', 
                                        (default_profit / default_base * 100) if default_base > 0 else 25),
            "confidence_score": getattr(recommended, 'confidence_score', 0.7),
            "justification": getattr(recommended, 'justification', 'Competitive pricing based on market analysis'),
            "price_breakdown": getattr(recommended, 'price_breakdown', 
                                      {'base_cost': default_base, 'profit': default_profit}),
            "risk_factors": getattr(recommended, 'risk_factors', []),
        }
        return formatted_pricing
    def generate_bid_document(
        self,
        rfp_data: dict[str, Any],
        generation_mode: ProposalGenerationMode | str | None = None,
        enable_thinking: bool | None = None,
        qa_items: list[dict[str, Any]] | None = None,
        compliance_signals: dict[str, Any] | None = None,
        document_content: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate complete bid document integrating all pipeline components.

        Args:
            rfp_data: RFP data dictionary
            generation_mode: Override the default generation mode
                - "template": Fast template-based generation
                - "claude_standard": Claude Sonnet without thinking
                - "claude_enhanced": Claude Sonnet with thinking (recommended)
                - "claude_premium": Claude Opus with thinking (highest quality)
            enable_thinking: Override thinking mode setting
            qa_items: Q&A items from the RFP for context
            compliance_signals: Detected compliance signals (FEMA domestic preference, etc.)
            document_content: Extracted text from RFP attachments (PDFs, DOCX files)

        Returns:
            Complete bid document dictionary
        """
        self.logger.info(f"Generating bid document for: {rfp_data.get('title', 'Unknown RFP')}")
        generation_start = time.time()

        # Log compliance signals if detected
        if compliance_signals and compliance_signals.get('detected_signals'):
            self.logger.info(f"Compliance signals detected: {compliance_signals.get('detected_signals')}")

        # Handle mode override
        if generation_mode:
            if isinstance(generation_mode, str):
                mode_map = {
                    "template": ProposalGenerationMode.TEMPLATE,
                    "claude_standard": ProposalGenerationMode.CLAUDE_STANDARD,
                    "claude_enhanced": ProposalGenerationMode.CLAUDE_ENHANCED,
                    "claude_premium": ProposalGenerationMode.CLAUDE_PREMIUM,
                }
                generation_mode = mode_map.get(generation_mode.lower(), ProposalGenerationMode.TEMPLATE)

            # Reinitialize enhanced generator if mode changed
            if generation_mode != self.proposal_options.mode:
                self.proposal_options.mode = generation_mode
                if enable_thinking is not None:
                    self.proposal_options.enable_thinking = enable_thinking
                self._initialize_enhanced_generator()

        # Store compliance context for use in section generation
        self._current_qa_items = qa_items
        self._current_compliance_signals = compliance_signals
        self._current_document_content = document_content

        # Log document content availability
        if document_content and document_content.get('documents'):
            doc_count = document_content.get('document_count', 0)
            total_chars = document_content.get('total_chars', 0)
            self.logger.info(f"RFP attachments available: {doc_count} documents, {total_chars} chars")

        # Step 1: Generate compliance matrix
        compliance_matrix = None
        if self.compliance_generator:
            try:
                compliance_matrix = self.compliance_generator.generate_compliance_matrix(rfp_data)
                self.logger.info(f"Compliance matrix generated with {len(compliance_matrix['requirements_and_responses'])} requirements")
            except Exception as e:
                self.logger.error(f"Compliance matrix generation failed: {e}")
                compliance_matrix = self._create_default_compliance_matrix()
        else:
            compliance_matrix = self._create_default_compliance_matrix()

        # Step 2: Generate pricing
        pricing_results = None
        if self.pricing_engine:
            try:
                extracted_requirements = compliance_matrix.get('requirements_and_responses', [])
                pricing_results = self.pricing_engine.compare_strategies(rfp_data, extracted_requirements)
                self.logger.info(f"Pricing analysis completed with {len(pricing_results)} strategies")
            except Exception as e:
                self.logger.error(f"Pricing generation failed: {e}")
                pricing_results = self._create_default_pricing(rfp_data)
        else:
            pricing_results = self._create_default_pricing(rfp_data)

        # Step 3: Generate content sections with Claude enhancement if available
        formatted_pricing = self._format_pricing_for_document(pricing_results)

        executive_summary = self._generate_executive_summary(
            rfp_data,
            compliance_matrix['compliance_summary'],
            list(pricing_results.values())[0] if pricing_results else None,
            compliance_matrix  # Pass full compliance matrix for enhanced generation
        )

        technical_approach = self._generate_technical_approach(
            rfp_data, compliance_matrix, formatted_pricing
        )
        # Step 4: Create document content
        document_content = self._create_document_content(
            rfp_data, executive_summary, technical_approach,
            formatted_pricing, compliance_matrix
        )
        # Step 5: Create bid document package
        bid_document = {
            "rfp_info": {
                "title": rfp_data.get('title', 'Government Contract'),
                "agency": rfp_data.get('agency', 'Government Agency'),
                "solicitation_number": rfp_data.get('solicitation_number', 'TBD'),
                "naics_code": rfp_data.get('naics_code', 'TBD'),
                "rfp_id": rfp_data.get('rfp_id', 'unknown')
            },
            "content": {
                "markdown": document_content,
                "html": markdown.markdown(document_content, extensions=['tables']),
                "sections": {
                    "executive_summary": executive_summary,
                    "technical_approach": technical_approach,
                    "pricing": formatted_pricing,
                    "compliance_matrix": compliance_matrix
                }
            },
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "generator_version": "2.0.0",
                "generation_mode": self.proposal_options.mode.value,
                "thinking_enabled": self.proposal_options.enable_thinking if self.enhanced_generator else False,
                "claude_enhanced": self.enhanced_generator is not None and self.enhanced_generator.is_available(),
                "components_used": {
                    "rag_engine": self.rag_engine is not None,
                    "compliance_generator": self.compliance_generator is not None,
                    "pricing_engine": self.pricing_engine is not None,
                    "claude_llm": self.enhanced_generator is not None and self.enhanced_generator.is_available(),
                },
                "document_stats": {
                    "total_sections": 6,
                    "content_length": len(document_content),
                    "requirements_addressed": len(compliance_matrix.get('requirements_and_responses', [])),
                    "pricing_strategies_analyzed": len(pricing_results) if pricing_results else 0
                },
                "generation_time_seconds": time.time() - generation_start
            }
        }
        return bid_document
    def _create_document_content(self, rfp_data: dict[str, Any], executive_summary: str,
                               technical_approach: dict[str, str], pricing: dict[str, Any],
                               compliance_matrix: dict[str, Any]) -> str:
        """Create the main document content in markdown format."""
        content_parts = []
        # Header
        content_parts.append(f"# {rfp_data.get('title', 'Government Contract')}")
        content_parts.append("")
        content_parts.append(f"**Submitted to:** {rfp_data.get('agency', 'Government Agency')}")
        content_parts.append(f"**RFP Number:** {rfp_data.get('solicitation_number', 'TBD')}")
        content_parts.append(f"**Submitted by:** {self.content_library['company_profile']['company_name']}")
        content_parts.append(f"**Date:** {datetime.now().strftime('%B %d, %Y')}")
        content_parts.append(f"**NAICS Code:** {rfp_data.get('naics_code', 'TBD')}")
        content_parts.append("")
        content_parts.append("---")
        content_parts.append("")
        # Executive Summary
        content_parts.append("## Executive Summary")
        content_parts.append("")
        content_parts.append(executive_summary)
        content_parts.append("")
        # Key highlights
        content_parts.append("**Key Highlights:**")
        content_parts.append(f"- **Competitive Pricing:** ${pricing['recommended_price']:,.2f} ({pricing['recommended_strategy']} strategy)")
        content_parts.append(f"- **Compliance Rate:** {compliance_matrix['compliance_summary']['compliance_rate']:.1%} of requirements addressed")
        content_parts.append(f"- **Margin Efficiency:** {pricing['margin_percentage']:.1f}% margin ensuring sustainable delivery")
        content_parts.append(f"- **Confidence Level:** {pricing['confidence_score']:.1%} based on market analysis")
        content_parts.append("")
        content_parts.append("---")
        content_parts.append("")
        # Company Qualifications
        content_parts.append("## Company Qualifications")
        content_parts.append("")
        company = self.content_library['company_profile']
        company_name = company.get('company_name') or company.get('legal_name', 'Our Company')
        established = company.get('established') or company.get('established_year', 'Unknown')
        headquarters = company.get('headquarters') or company.get('address', 'Unknown')
        employees = company.get('employees') or company.get('employee_count', 'Unknown')
        website = company.get('website', '')
        
        content_parts.append(f"### About {company_name}")
        content_parts.append("")
        # Build company description from actual data
        description_parts = [f"Founded in {established}, {company_name}"]
        
        # Add website if available
        if website:
            description_parts.append(f"({website})")
        
        description_parts.append("is a provider of government contracting services.")
        
        # Add location and size info
        if headquarters != 'Unknown':
            description_parts.append(f"With headquarters in {headquarters}")
            if employees != 'Unknown':
                description_parts.append(f"and {employees} dedicated professionals,")
            description_parts.append("we are committed to delivering exceptional value and service.")
        else:
            description_parts.append("We are committed to delivering exceptional value and service.")
        
        content_parts.append(" ".join(description_parts))
        content_parts.append("")
        
        # Core Competencies (if available)
        competencies = company.get('core_competencies', [])
        if competencies:
            content_parts.append("### Core Competencies")
            content_parts.append("")
            for competency in competencies[:10]:  # Limit to top 10
                content_parts.append(f"- {competency}")
            content_parts.append("")
        
        # Certifications
        certifications = company.get('certifications', [])
        if certifications:
            content_parts.append("### Certifications and Credentials")
            content_parts.append("")
            for cert in certifications:
                content_parts.append(f"- {cert}")
            content_parts.append("")
        
        # Past Performance - only show if we have actual data
        past_performance = company.get('past_performance', [])
        if past_performance:
            content_parts.append("### Past Performance")
            content_parts.append("")
            for project in past_performance:
                # Handle different project data structures
                if isinstance(project, dict):
                    client = project.get('client') or project.get('agency', 'Client')
                    project_name = project.get('project') or project.get('title', 'Project')
                    value = project.get('value') or project.get('contract_value', 'N/A')
                    duration = project.get('duration') or project.get('contract_duration', 'N/A')
                    rating = project.get('performance_rating') or project.get('rating', 'N/A')
                    
                    content_parts.append(f"**{client}** - {project_name}")
                    content_parts.append(f"*Contract Value:* {value} | *Duration:* {duration} | *Rating:* {rating}")
                    content_parts.append("")
                else:
                    # Fallback for string or other formats
                    content_parts.append(f"- {project}")
                    content_parts.append("")
        # If no past performance, omit the section entirely (don't show empty section)
        
        content_parts.append("---")
        content_parts.append("")
        # Technical Approach
        content_parts.append("## Technical Approach")
        content_parts.append("")
        content_parts.append("### Methodology")
        content_parts.append("")
        content_parts.append(technical_approach['methodology'])
        content_parts.append("")

        if technical_approach.get('gantt_chart_path'):
            content_parts.append("### Implementation Schedule")
            content_parts.append("")
            content_parts.append(f"![Schedule]({technical_approach['gantt_chart_path']})")
            content_parts.append("")

        if technical_approach.get('org_chart_path'):
            content_parts.append("### Project Organization")
            content_parts.append("")
            content_parts.append(f"![Organization]({technical_approach['org_chart_path']})")
            content_parts.append("")

        content_parts.append("### Project Management")
        content_parts.append("")
        content_parts.append(technical_approach['project_management'])
        content_parts.append("")
        content_parts.append("---")
        content_parts.append("")
        # Pricing
        content_parts.append("## Pricing")
        content_parts.append("")
        content_parts.append(f"### Pricing Strategy: {pricing['recommended_strategy'].replace('_', ' ').title()}")
        content_parts.append("")
        content_parts.append(pricing['justification'])
        content_parts.append("")
        content_parts.append("### Cost Breakdown")
        content_parts.append("")
        content_parts.append("| Component | Amount |")
        content_parts.append("|-----------|--------|")
        for component, amount in pricing['price_breakdown'].items():
            content_parts.append(f"| {component.replace('_', ' ').title()} | ${amount:,.2f} |")
        content_parts.append(f"| **Total Contract Value** | **${pricing['recommended_price']:,.2f}** |")
        content_parts.append("")
        content_parts.append("---")
        content_parts.append("")
        # Compliance Matrix
        content_parts.append("## Compliance Matrix")
        content_parts.append("")
        content_parts.append("### Compliance Summary")
        content_parts.append("")
        summary = compliance_matrix['compliance_summary']
        content_parts.append(f"- **Total Requirements:** {summary['total_requirements']}")
        content_parts.append(f"- **Compliance Rate:** {summary['compliance_rate']:.1%}")
        content_parts.append(f"- **Overall Status:** {summary['overall_status'].replace('_', ' ').title()}")
        content_parts.append("")
        # Sample requirements
        content_parts.append("### Key Requirements and Responses")
        content_parts.append("")
        for i, response in enumerate(compliance_matrix.get('requirements_and_responses', [])[:3]):
            content_parts.append(f"**Requirement {i+1}:** {response['requirement_text'][:100]}...")
            content_parts.append(f"**Status:** {response['compliance_status'].title()}")
            content_parts.append(f"**Response:** {response['response_text'][:200]}...")
            content_parts.append("")
        content_parts.append("---")
        content_parts.append("")
        # Terms and Conditions
        content_parts.append("## Terms and Conditions")
        content_parts.append("")
        terms = self.content_library['standard_clauses']['terms_and_conditions']
        content_parts.append(f"**Payment Terms:** {terms['payment_terms']}")
        content_parts.append("")
        content_parts.append(f"**Warranty:** {terms['warranty']}")
        content_parts.append("")
        content_parts.append(f"**Performance Guarantee:** {terms['performance_guarantee']}")
        content_parts.append("")
        content_parts.append("---")
        content_parts.append("")
        # Conclusion
        content_parts.append("## Conclusion")
        content_parts.append("")
        content_parts.append(f"We are committed to delivering exceptional services that meet or exceed all requirements while providing outstanding value to {rfp_data.get('agency', 'the agency')}.")
        content_parts.append("")
        content_parts.append("**We respectfully request your favorable consideration of our proposal.**")
        content_parts.append("")
        content_parts.append("---")
        content_parts.append("")
        # Use RFP response deadline if available, otherwise default to 30 days
        response_deadline = None
        if rfp_data.get('response_deadline'):
            try:
                if isinstance(rfp_data['response_deadline'], str):
                    response_deadline = pd.to_datetime(rfp_data['response_deadline']).to_pydatetime()
                else:
                    response_deadline = rfp_data['response_deadline']
            except Exception:
                pass
        
        if response_deadline:
            valid_through = response_deadline.strftime('%B %d, %Y')
        else:
            valid_through = (datetime.now() + timedelta(days=30)).strftime('%B %d, %Y')
        content_parts.append(f"**Proposal Valid Through:** {valid_through}")
        return "\n".join(content_parts)
    def _create_default_compliance_matrix(self) -> dict[str, Any]:
        """Create default compliance matrix when compliance generator is not available."""
        return {
            "compliance_summary": {
                "total_requirements": 5,
                "compliant": 4,
                "partial": 1,
                "review_required": 0,
                "compliance_rate": 0.8,
                "overall_status": "compliant"
            },
            "requirements_and_responses": [
                {
                    "requirement_id": "default_req_1",
                    "requirement_text": "Meet all technical specifications",
                    "compliance_status": "compliant",
                    "response_text": "We fully comply with all technical specifications through proven methodologies.",
                    "category": "technical",
                    "mandatory": True
                }
            ]
        }
    def _create_default_pricing(self, rfp_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create default pricing when pricing engine is not available."""
        # Use RFP award amount if available, otherwise use reasonable default
        award_amount = 100000.0  # Default fallback
        if rfp_data:
            award_amount = float(rfp_data.get('award_amount', 0) or rfp_data.get('estimated_value', 0) or 100000)
        
        base_cost = int(award_amount * 0.75)
        profit = award_amount - base_cost
        margin = (profit / base_cost * 100) if base_cost > 0 else 25.0
        
        class MockPricingResult:
            def __init__(self, price, base, margin_val):
                self.total_price = price
                self.base_cost = base
                self.margin_percentage = margin_val
                self.pricing_strategy = 'competitive'
                self.confidence_score = 0.7
                self.justification = f'Competitive pricing based on RFP value of ${price:,.0f}'
                self.price_breakdown = {'base_cost': float(base), 'profit': float(profit)}
                self.risk_factors = []
        return {"competitive": MockPricingResult(award_amount, base_cost, margin)}
    def export_bid_document(self, bid_document: dict[str, Any],
                          output_format: str = "markdown") -> str:
        """Export bid document to various formats."""
        rfp_id = bid_document['rfp_info'].get('rfp_id', 'unknown')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_format.lower() == "markdown":
            filename = f"bid_document_{rfp_id}_{timestamp}.md"
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, 'w') as f:
                f.write(bid_document['content']['markdown'])
        elif output_format.lower() == "html":
            filename = f"bid_document_{rfp_id}_{timestamp}.html"
            filepath = os.path.join(self.output_dir, filename)
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Bid Document - {bid_document['rfp_info']['title']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        h1 {{ color: #1e3a8a; border-bottom: 3px solid #3b82f6; }}
        h2 {{ color: #1e40af; margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    {bid_document['content']['html']}
</body>
</html>"""
            with open(filepath, 'w') as f:
                f.write(html_content)
        elif output_format.lower() == "json":
            filename = f"bid_document_{rfp_id}_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(bid_document, f, indent=2)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        self.logger.info(f"Bid document exported to: {filepath}")
        return filepath
def main():
    """Main function for testing bid document generator."""
    print("Testing Fixed Bid Document Generator")
    print("=" * 50)
    try:
        # Initialize with integrated components
        from compliance.compliance_matrix import ComplianceMatrixGenerator
        from pricing.pricing_engine import PricingEngine
        compliance_gen = ComplianceMatrixGenerator()
        pricing_engine = PricingEngine()
        generator = BidDocumentGenerator(
            compliance_generator=compliance_gen,
            pricing_engine=pricing_engine
        )
        print("✅ Initialized with full pipeline integration")
        # Load test RFP
        df = pd.read_parquet(str(PathConfig.PROCESSED_DATA_DIR / "rfp_master_dataset.parquet"))
        test_rfp = df[df['description'].notna()].iloc[0].to_dict()
        print(f"\nTest RFP: {test_rfp['title']}")
        print(f"Agency: {test_rfp['agency']}")
        # Generate bid document
        print("\nGenerating complete bid document...")
        start_time = time.time()
        bid_document = generator.generate_bid_document(test_rfp)
        generation_time = time.time() - start_time
        # Export in multiple formats
        markdown_path = generator.export_bid_document(bid_document, "markdown")
        html_path = generator.export_bid_document(bid_document, "html")
        json_path = generator.export_bid_document(bid_document, "json")
        print("✅ Bid document generated successfully!")
        print(f"Generation time: {generation_time:.2f} seconds")
        print(f"Content length: {bid_document['metadata']['document_stats']['content_length']:,} characters")
        print(f"Requirements addressed: {bid_document['metadata']['document_stats']['requirements_addressed']}")
        print(f"Pricing strategies analyzed: {bid_document['metadata']['document_stats']['pricing_strategies_analyzed']}")
        print("\nExported files:")
        for path in [markdown_path, html_path, json_path]:
            if os.path.exists(path):
                size = os.path.getsize(path)
                print(f"✅ {os.path.basename(path)}: {size:,} bytes")
            else:
                print(f"❌ {os.path.basename(path)}: Not created")
        return True
    except Exception as e:
        print(f"❌ Error testing bid document generator: {e}")
        import traceback
        traceback.print_exc()
        return False
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
