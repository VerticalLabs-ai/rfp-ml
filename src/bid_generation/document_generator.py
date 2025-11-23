"""
Fixed Bid Document Generator for AI-powered RFP bid generation system.
Integrates RAG, Compliance Matrix, and Pricing Engine outputs into structured bid documents.
"""
import os
import sys
import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from jinja2 import Template, Environment, FileSystemLoader
import markdown
from .visualizer import Visualizer

# Import path configuration
from config.paths import PathConfig
class BidDocumentGenerator:
    """
    Generate complete, structured bid documents integrating all pipeline components.
    """
    def __init__(
        self,
        rag_engine=None,
        compliance_generator=None,
        pricing_engine=None,
        templates_dir: str | None = None,
        content_library_dir: str | None = None,
        output_dir: str | None = None
    ):
        """Initialize bid document generator."""
        # Ensure PathConfig directories are initialized
        PathConfig.ensure_directories()

        self.rag_engine = rag_engine
        self.compliance_generator = compliance_generator
        self.pricing_engine = pricing_engine
        self.templates_dir = templates_dir or str(PathConfig.TEMPLATES_DIR)
        self.content_library_dir = content_library_dir or str(PathConfig.CONTENT_LIBRARY_DIR)
        self.output_dir = output_dir or str(PathConfig.BID_DOCUMENTS_DIR)
        
        # Initialize visualizer
        self.visualizer = Visualizer(output_dir=os.path.join(self.output_dir, "assets"))
        
        # Create directories
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.content_library_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        # Load content library
        self.content_library = self._load_content_library()
    def _load_content_library(self) -> Dict[str, Any]:
        """Load or create content library with reusable content blocks."""
        # Company profile
        company_profile_path = os.path.join(self.content_library_dir, "company_profile.json")
        company_profile = {
            "company_name": "Advanced Solutions Group LLC",
            "established": "2015",
            "headquarters": "Washington, DC",
            "employees": "150+",
            "certifications": [
                "GSA Schedule Contract Holder",
                "SBA 8(a) Certified",
                "ISO 9001:2015 Quality Management",
                "ISO 27001:2013 Information Security"
            ],
            "core_competencies": [
                "Government Contract Management",
                "Supply Chain Solutions", 
                "Facility Services Management",
                "Technology Integration",
                "Compliance and Quality Assurance"
            ],
            "past_performance": [
                {
                    "client": "General Services Administration",
                    "project": "Multi-State Facility Services Contract",
                    "value": "$2.5M",
                    "duration": "3 years",
                    "performance_rating": "Exceptional"
                },
                {
                    "client": "Department of Veterans Affairs",
                    "project": "Medical Equipment Maintenance Services", 
                    "value": "$1.8M",
                    "duration": "2 years",
                    "performance_rating": "Outstanding"
                }
            ]
        }
        if not os.path.exists(company_profile_path):
            with open(company_profile_path, 'w') as f:
                json.dump(company_profile, f, indent=2)
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
    def _determine_category(self, rfp_data: Dict[str, Any]) -> str:
        """Determine RFP category for appropriate content selection."""
        title = str(rfp_data.get('title', '')).lower()
        description = str(rfp_data.get('description', '')).lower()
        if any(keyword in title + description for keyword in ['water', 'beverage', 'bottle']):
            return 'bottled_water'
        elif any(keyword in title + description for keyword in ['construction', 'building', 'infrastructure']):
            return 'construction'
        elif any(keyword in title + description for keyword in ['delivery', 'transport', 'logistics']):
            return 'delivery'
        elif any(keyword in title + description for keyword in ['maintenance', 'repair']):
            return 'maintenance'
        else:
            return 'professional_services'
    def _generate_executive_summary(self, rfp_data: Dict[str, Any], 
                                  compliance_summary: Dict[str, Any],
                                  pricing_result: Any) -> str:
        """Generate executive summary using available data."""
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
                f"We have carefully analyzed all requirements and provide detailed responses addressing "
                f"the full scope of work with actionable compliance strategies."
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
                f"Our competitive pricing approach offers exceptional value "
                f"while ensuring sustainable service delivery and compliance with all requirements."
            )
        # Category-specific value proposition
        if category == 'bottled_water':
            summary_parts.append(
                f"We specialize in reliable, cost-effective water supply solutions with "
                f"24/7 delivery capabilities and comprehensive inventory management."
            )
        elif category == 'construction':
            summary_parts.append(
                f"Our construction management expertise encompasses full project lifecycle "
                f"from planning through completion with emphasis on safety, quality, and schedule adherence."
            )
        elif category == 'delivery':
            summary_parts.append(
                f"We provide comprehensive logistics and delivery services with real-time "
                f"tracking, flexible scheduling, and proven reliability for government operations."
            )
        else:
            summary_parts.append(
                f"Our proven methodology combines industry best practices with innovative "
                f"solutions specifically designed for government contracting requirements."
            )
        # Closing
        summary_parts.append(
            f"We look forward to partnering with {agency} to deliver outstanding results "
            f"that meet your mission-critical objectives while providing exceptional value."
        )
        return " ".join(summary_parts)
    def _generate_technical_approach(self, rfp_data: Dict[str, Any], 
                                   compliance_matrix: Dict[str, Any]) -> Dict[str, str]:
        """Generate technical approach section with visualizations."""
        category = self._determine_category(rfp_data)
        
        # Generate visualizations
        # 1. Schedule
        schedule_tasks = [
            {"task": "Project Kickoff", "start": datetime.now(), "end": datetime.now() + timedelta(days=7)},
            {"task": "Planning & Design", "start": datetime.now() + timedelta(days=7), "end": datetime.now() + timedelta(days=30)},
            {"task": "Execution Phase 1", "start": datetime.now() + timedelta(days=30), "end": datetime.now() + timedelta(days=90)},
            {"task": "Quality Assurance", "start": datetime.now() + timedelta(days=60), "end": datetime.now() + timedelta(days=100)},
            {"task": "Final Delivery", "start": datetime.now() + timedelta(days=100), "end": datetime.now() + timedelta(days=120)}
        ]
        gantt_path = self.visualizer.generate_gantt_chart(schedule_tasks, f"schedule_{rfp_data.get('rfp_id','temp')}.png")
        gantt_rel_path = os.path.relpath(gantt_path, self.output_dir) if gantt_path else ""

        # 2. Org Chart
        staff = [
            {"name": "Project Manager", "role": "Project Manager", "reports_to": None},
            {"name": "Technical Lead", "role": "Tech Lead", "reports_to": "Project Manager"},
            {"name": "QA Specialist", "role": "QA Lead", "reports_to": "Project Manager"},
            {"name": "Site Supervisor", "role": "Site Lead", "reports_to": "Project Manager"},
            {"name": "Team A", "role": "Operations", "reports_to": "Site Lead"}
        ]
        org_path = self.visualizer.generate_org_chart(staff, f"org_{rfp_data.get('rfp_id','temp')}.png")
        org_rel_path = os.path.relpath(org_path, self.output_dir) if org_path else ""

        if category == 'bottled_water':
            methodology = (
                "Our water supply methodology encompasses comprehensive inventory management, "
                "reliable delivery scheduling, quality assurance testing, and customer service excellence."
            )
        elif category == 'construction':
            methodology = (
                "Our construction methodology follows proven project management principles "
                "with emphasis on safety, quality, and schedule adherence."
            )
        elif category == 'delivery':
            methodology = (
                "Our delivery methodology combines advanced logistics planning, real-time "
                "tracking systems, and flexible routing optimization."
            )
        else:
            methodology = (
                "Our proven methodology combines industry best practices with innovative "
                "solutions tailored to government requirements."
            )
            
        return {
            "methodology": methodology,
            "project_management": self.content_library['standard_clauses']['technical_approach']['project_management'],
            "quality_assurance": self.content_library['standard_clauses']['technical_approach']['quality_assurance'],
            "risk_management": self.content_library['standard_clauses']['technical_approach']['risk_management'],
            "gantt_chart_path": gantt_rel_path,
            "org_chart_path": org_rel_path
        }
    def _format_pricing_for_document(self, pricing_results: Dict[str, Any]) -> Dict[str, Any]:
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
        # Format for template
        formatted_pricing = {
            "recommended_price": getattr(recommended, 'total_price', 100000),
            "recommended_strategy": recommended_strategy,
            "margin_percentage": getattr(recommended, 'margin_percentage', 25),
            "confidence_score": getattr(recommended, 'confidence_score', 0.7),
            "justification": getattr(recommended, 'justification', 'Competitive pricing based on market analysis'),
            "price_breakdown": getattr(recommended, 'price_breakdown', {'base_cost': 75000, 'profit': 25000}),
            "risk_factors": getattr(recommended, 'risk_factors', []),
        }
        return formatted_pricing
    def generate_bid_document(self, rfp_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complete bid document integrating all pipeline components."""
        self.logger.info(f"Generating bid document for: {rfp_data.get('title', 'Unknown RFP')}")
        generation_start = time.time()
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
                pricing_results = self._create_default_pricing()
        else:
            pricing_results = self._create_default_pricing()
        # Step 3: Generate content sections
        executive_summary = self._generate_executive_summary(
            rfp_data, 
            compliance_matrix['compliance_summary'], 
            list(pricing_results.values())[0] if pricing_results else None
        )
        technical_approach = self._generate_technical_approach(rfp_data, compliance_matrix)
        formatted_pricing = self._format_pricing_for_document(pricing_results)
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
                "generator_version": "1.0.0",
                "components_used": {
                    "rag_engine": self.rag_engine is not None,
                    "compliance_generator": self.compliance_generator is not None,
                    "pricing_engine": self.pricing_engine is not None
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
    def _create_document_content(self, rfp_data: Dict[str, Any], executive_summary: str,
                               technical_approach: Dict[str, str], pricing: Dict[str, Any],
                               compliance_matrix: Dict[str, Any]) -> str:
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
        content_parts.append(f"### About {company['company_name']}")
        content_parts.append("")
        content_parts.append(f"Founded in {company['established']}, {company['company_name']} is a leading provider of government contracting services.")
        content_parts.append(f"With headquarters in {company['headquarters']} and {company['employees']} dedicated professionals, we have established ourselves as a trusted partner for complex government contracting needs.")
        content_parts.append("")
        # Certifications
        content_parts.append("### Certifications and Credentials")
        content_parts.append("")
        for cert in company['certifications']:
            content_parts.append(f"- {cert}")
        content_parts.append("")
        # Past Performance
        content_parts.append("### Past Performance")
        content_parts.append("")
        for project in company['past_performance']:
            content_parts.append(f"**{project['client']}** - {project['project']}")
            content_parts.append(f"*Contract Value:* {project['value']} | *Duration:* {project['duration']} | *Rating:* {project['performance_rating']}")
            content_parts.append("")
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
        content_parts.append(f"**Proposal Valid Through:** {(datetime.now() + timedelta(days=30)).strftime('%B %d, %Y')}")
        return "\n".join(content_parts)
    def _create_default_compliance_matrix(self) -> Dict[str, Any]:
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
    def _create_default_pricing(self) -> Dict[str, Any]:
        """Create default pricing when pricing engine is not available."""
        class MockPricingResult:
            def __init__(self):
                self.total_price = 100000.0
                self.base_cost = 75000.0
                self.margin_percentage = 25.0
                self.pricing_strategy = 'competitive'
                self.confidence_score = 0.7
                self.justification = 'Competitive pricing based on industry standards'
                self.price_breakdown = {'base_cost': 75000.0, 'profit': 25000.0}
                self.risk_factors = []
        return {"competitive": MockPricingResult()}
    def export_bid_document(self, bid_document: Dict[str, Any], 
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
        print(f"\nGenerating complete bid document...")
        start_time = time.time()
        bid_document = generator.generate_bid_document(test_rfp)
        generation_time = time.time() - start_time
        # Export in multiple formats
        markdown_path = generator.export_bid_document(bid_document, "markdown")
        html_path = generator.export_bid_document(bid_document, "html")
        json_path = generator.export_bid_document(bid_document, "json")
        print(f"✅ Bid document generated successfully!")
        print(f"Generation time: {generation_time:.2f} seconds")
        print(f"Content length: {bid_document['metadata']['document_stats']['content_length']:,} characters")
        print(f"Requirements addressed: {bid_document['metadata']['document_stats']['requirements_addressed']}")
        print(f"Pricing strategies analyzed: {bid_document['metadata']['document_stats']['pricing_strategies_analyzed']}")
        print(f"\nExported files:")
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