# Bid Document Generator for AI-powered RFP bid generation system.
"""Integrates RAG, Compliance Matrix, and Pricing Engine outputs into structured bid documents."""
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
from io import BytesIO
import base64
# Add src to path for imports
sys.path.insert(0, '/app/government_rfp_bid_1927/src')
class BidDocumentGenerator:
"""
Generate complete, structured bid documents integrating all pipeline components.

This class creates bid documents using retrieved content (RAG),
compliance matrices, and pricing analysis, formatting outputs for government RFP submission.
"""

def __init__(
self,
rag_engine=None,
compliance_generator=None,
pricing_engine=None,
templates_dir: str = "/app/government_rfp_bid_1927/data/templates",
content_library_dir: str = "/app/government_rfp_bid_1927/data/content_library",
output_dir: str = "/app/government_rfp_bid_1927/data/bid_documents"
):
"""
Initialize bid document generator.

Args:
rag_engine (object): RAG engine for content retrieval
compliance_generator (object): Compliance matrix generator
pricing_engine (object): Pricing engine for cost analysis
templates_dir (str): Directory containing document templates
content_library_dir (str): Directory with reusable content blocks
output_dir (str): Directory for generated bid documents
"""
self.rag_engine = rag_engine
self.compliance_generator = compliance_generator
self.pricing_engine = pricing_engine
self.templates_dir = templates_dir
self.content_library_dir = content_library_dir
self.output_dir = output_dir
self.rag_engine = rag_engine
self.compliance_generator = compliance_generator
self.pricing_engine = pricing_engine
self.templates_dir = templates_dir
self.content_library_dir = content_library_dir
self.output_dir = output_dir
# Create directories
os.makedirs(self.templates_dir, exist_ok=True)
os.makedirs(self.content_library_dir, exist_ok=True)
os.makedirs(self.output_dir, exist_ok=True)
# Initialize logging
logging.basicConfig(level=logging.INFO)
self.logger = logging.getLogger(__name__)
# Initialize Jinja2 environment
self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
# Load content library and templates
self.content_library = self._load_content_library()
self.templates = self._create_document_templates()
def _load_content_library(self) -> Dict[str, Any]:
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
],
"core_competencies": [
"Government Contract Management",
"Supply Chain Solutions",
"Facility Services Management",
"Technology Integration",
"past_performance": [
{
"client": "General Services Administration",
"project": "Multi-State Facility Services Contract",
"value": "$2.5M",
"duration": "3 years"
},
{
"client": "Department of Veterans Affairs",
"project": "Medical Equipment Maintenance Services",
"value": "$1.8M",
"duration": "2 years"
},
{
"client": "Department of Defense",
"project": "Logistics and Supply Chain Management",
"value": "$4.2M",
"duration": "5 years"
}
]
"key_personnel": [
"name": "Sarah Johnson",
"title": "Project Manager",
"experience": "12 years government contracting",
"certifications": ["PMP", "CPSM"]
"name": "Michael Chen",
"title": "Technical Lead",
"experience": "15 years systems integration",
"certifications": ["CISSP", "AWS Solutions Architect"]
]
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
"technical_approach": {
"methodology": "Our proven methodology combines industry best practices with innovative solutions tailored to government requirements.",
"quality_assurance": "Comprehensive quality management system with regular audits, performance monitoring, and continuous improvement processes.",
"project_management": "Dedicated project management using PMI standards with regular reporting, milestone tracking, and stakeholder communication.",
"risk_management": "Proactive risk identification and mitigation strategies with contingency planning for all critical project elements.",
"value_propositions": {
"cost_effectiveness": "Competitive pricing with transparent cost structure and proven ability to deliver within budget.",
"expertise": "Deep domain expertise with specialized knowledge of government requirements and industry best practices.",
"reliability": "Consistent track record of on-time, on-budget delivery with exceptional customer satisfaction ratings.",
"innovation": "Cutting-edge solutions leveraging latest technologies and methodologies to enhance performance and efficiency.",
if not os.path.exists(standard_clauses_path):
with open(standard_clauses_path, 'w') as f:
json.dump(standard_clauses, f, indent=2)
# Load content library
content_library = {
"company_profile": company_profile,
"standard_clauses": standard_clauses
self.logger.info(f"Content library loaded with {len(content_library)} sections")
return content_library
def _create_document_templates(self) -> Dict[str, str]:
# Main bid document template
bid_template_path = os.path.join(self.templates_dir, "bid_document_template.jinja2")
bid_template_content = """
# {{ rfp_info.title }}
**Submitted to:** {{ rfp_info.agency }}
**RFP Number:** {{ rfp_info.solicitation_number }}
**Submitted by:** {{ company_profile.company_name }}
**Date:** {{ submission_date }}
**NAICS Code:** {{ rfp_info.naics_code }}
---
## Executive Summary
{{ executive_summary }}
Our company is uniquely positioned to deliver exceptional results for this {{ rfp_category }} contract. With {{ company_profile.experience_years }}+ years of government contracting experience and a proven track record of {{ company_profile.success_rate }}% successful project completion, we offer the expertise, reliability, and value that {{ rfp_info.agency }} requires.
**Key Highlights:**
- **Competitive Pricing:** ${{ pricing.recommended_price | number_format }} ({{ pricing.recommended_strategy }} strategy)
- **Compliance Rate:** {{ compliance.compliance_rate }}% of requirements fully addressed
- **Margin Efficiency:** {{ pricing.margin_percentage }}% margin ensuring sustainable service delivery
- **Confidence Level:** {{ pricing.confidence_score }}% based on comprehensive market analysis
## Company Qualifications
### About {{ company_profile.company_name }}
Founded in {{ company_profile.established }}, {{ company_profile.company_name }} is a leading provider of {{ rfp_category }} services to government agencies. With headquarters in {{ company_profile.headquarters }} and {{ company_profile.employees }} dedicated professionals, we have established ourselves as a trusted partner for complex government contracting needs.
### Certifications and Credentials
{% for cert in company_profile.certifications %}
- {{ cert }}
{% endfor %}
### Core Competencies
{% for competency in company_profile.core_competencies %}
- **{{ competency }}:** Proven expertise with multiple successful implementations
### Past Performance
{% for project in company_profile.past_performance %}
**{{ project.client }}** - {{ project.project }}
*Contract Value:* {{ project.value }} | *Duration:* {{ project.duration }} | *Rating:* {{ project.performance_rating }}
### Key Personnel
{% for person in company_profile.key_personnel %}
**{{ person.name }}**, {{ person.title }}
*Experience:* {{ person.experience }}
*Certifications:* {{ person.certifications | join(', ') }}
## Technical Approach
### Methodology
{{ technical_approach.methodology }}
### Project Management Approach
{{ technical_approach.project_management }}
### Quality Assurance
{{ technical_approach.quality_assurance }}
### Risk Management
{{ technical_approach.risk_management }}
{% if technical_approach.security %}
### Security and Compliance
{{ technical_approach.security }}
{% endif %}
## Pricing
### Pricing Strategy: {{ pricing.recommended_strategy | title }}
{{ pricing.justification }}
### Cost Breakdown
| Component | Amount | Percentage |
|-----------|--------|------------|
{% for component, amount in pricing.price_breakdown.items() %}
| {{ component | title | replace('_', ' ') }} | ${{ amount | number_format }} | {{ ((amount / pricing.total_price) * 100) | round(1) }}% |
| **Total Contract Value** | **${{ pricing.total_price | number_format }}** | **100%** |
### Pricing Justification
Our pricing reflects:
- **Market Analysis:** Based on {{ pricing.historical_context.count }}+ similar contracts
- **Competitive Position:** {{ pricing.competitive_positioning }}
- **Value Delivery:** {{ pricing.value_proposition }}
- **Risk Assessment:** {{ pricing.risk_factors | length }} risk factors evaluated and mitigated
## Compliance Matrix
### Compliance Summary
- **Total Requirements Identified:** {{ compliance.total_requirements }}
- **Fully Compliant:** {{ compliance.compliant_count }}
- **Partially Compliant:** {{ compliance.partial_count }}
- **Review Required:** {{ compliance.review_required_count }}
- **Overall Compliance Rate:** {{ compliance.compliance_rate }}%
- **Compliance Status:** {{ compliance.overall_status | title }}
### Detailed Requirements and Responses
{% for requirement in compliance.requirements_and_responses %}
#### Requirement {{ loop.index }}: {{ requirement.category | title }}
**Requirement:** {{ requirement.requirement_text }}
**Compliance Status:** {{ requirement.compliance_status | title }}
**Our Response:** {{ requirement.response_text }}
{% if requirement.supporting_evidence %}
**Supporting Evidence:** Based on similar project experience and industry best practices.
## Terms and Conditions
### Payment Terms
{{ terms_conditions.payment_terms }}
### Warranty and Performance Guarantee
{{ terms_conditions.warranty }}
{{ terms_conditions.performance_guarantee }}
### Liability and Insurance
{{ terms_conditions.liability }}
### Regulatory Compliance
{{ terms_conditions.compliance }}
## Conclusion
We are committed to delivering exceptional {{ rfp_category }} services that meet or exceed all requirements while providing outstanding value to {{ rfp_info.agency }}. Our comprehensive approach, proven track record, and competitive pricing make us the ideal partner for this important contract.
**We respectfully request your favorable consideration of our proposal.**
**Contact Information:**
{{ company_profile.company_name }}
{{ company_profile.headquarters }}
Phone: (555) 123-4567
Email: contracts@advancedsolutionsgroup.com
**Proposal Valid Through:** {{ proposal_validity_date }}
*This proposal is submitted in response to {{ rfp_info.solicitation_number }} and contains proprietary and confidential information.*
if not os.path.exists(bid_template_path):
with open(bid_template_path, 'w') as f:
f.write(bid_template_content)
return {
"main_bid_template": bid_template_content
def _generate_executive_summary(self, rfp_data: Dict[str, Any],
compliance_summary: Dict[str, Any],
pricing_result: Dict[str, Any]) -> str:
# Get category and basic info
title = rfp_data.get('title', 'Government Contract')
agency = rfp_data.get('agency', 'Government Agency')
category = self._determine_category(rfp_data)
# Use RAG to find similar successful bids if available
rag_context = ""
if self.rag_engine:
try:
query = f"successful bid {category} {title}"
similar_bids = self.rag_engine.retrieve(query, k=3)
if similar_bids:
rag_context = f"Based on analysis of {len(similar_bids)} similar successful contracts, "
except Exception as e:
self.logger.warning(f"RAG context retrieval failed: {e}")
# Generate executive summary content
summary_parts = []
# Opening statement
summary_parts.append(
f"We are pleased to submit our comprehensive proposal for {title}. "
f"{rag_context}we have designed a solution that directly addresses {agency}'s "
f"specific requirements while delivering exceptional value and performance."
)
# Compliance highlights
compliance_rate = compliance_summary.get('compliance_rate', 0) * 100
if compliance_rate >= 80:
f"Our proposal demonstrates {compliance_rate:.0f}% compliance with all identified requirements, "
f"reflecting our thorough understanding of the project scope and commitment to excellence."
else:
f"We have carefully analyzed all requirements and provide detailed responses addressing "
f"the full scope of work with actionable compliance strategies."
# Pricing highlights
pricing_strategy = getattr(pricing_result, 'pricing_strategy', 'competitive')
margin = getattr(pricing_result, 'margin_percentage', 25)
confidence = getattr(pricing_result, 'confidence_score', 0.5) * 100
f"Our {pricing_strategy.replace('_', ' ')} pricing approach offers exceptional value "
f"with a {margin:.0f}% margin that ensures sustainable service delivery. "
f"This pricing is supported by {confidence:.0f}% confidence based on comprehensive "
f"market analysis and historical performance data."
# Value proposition
if category == 'bottled_water':
f"We specialize in reliable, cost-effective water supply solutions with "
f"24/7 delivery capabilities and comprehensive inventory management."
elif category == 'construction':
f"Our construction management expertise encompasses full project lifecycle "
f"from planning through completion with emphasis on safety, quality, and schedule adherence."
elif category == 'delivery':
f"We provide comprehensive logistics and delivery services with real-time "
f"tracking, flexible scheduling, and proven reliability for government operations."
f"Our proven methodology combines industry best practices with innovative "
f"solutions specifically designed for government contracting requirements."
# Closing
f"We look forward to partnering with {agency} to deliver outstanding results "
f"that meet your mission-critical objectives while providing exceptional value."
return " ".join(summary_parts)
def _determine_category(self, rfp_data: Dict[str, Any]) -> str:
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
elif any(keyword in title + description for keyword in ['technology', 'software', 'system']):
return 'it_services'
return 'professional_services'
def _generate_technical_approach(self, rfp_data: Dict[str, Any],
compliance_matrix: Dict[str, Any]) -> Dict[str, str]:
# Base technical approach by category
methodology = (
project_management = (
# Enhanced content based on compliance requirements
technical_requirements = [r for r in compliance_matrix.get('requirements_and_responses', [])
if r.get('category') == 'technical']
if technical_requirements:
methodology += (
f" Our approach specifically addresses the {len(technical_requirements)} "
f"technical requirements identified, ensuring full compliance and optimal performance."
"methodology": methodology,
"project_management": project_management,
"quality_assurance": self.content_library['standard_clauses']['technical_approach']['quality_assurance'],
"risk_management": self.content_library['standard_clauses']['technical_approach']['risk_management'],
"security": self.content_library['standard_clauses']['technical_approach']['security']
def _format_pricing_for_document(self, pricing_results: Dict[str, Any]) -> Dict[str, Any]:
# Find recommended strategy
recommended = None
best_score = 0
for strategy_name, result in pricing_results.items():
score = result.confidence_score * 0.7 + (result.margin_percentage / 100) * 0.3
if score > best_score:
best_score = score
recommended = result
recommended['strategy_name'] = strategy_name
if not recommended:
# Fallback to first strategy
recommended = list(pricing_results.values())[0]
recommended['strategy_name'] = list(pricing_results.keys())[0]
# Format for template
formatted_pricing = {
"recommended_price": recommended.total_price,
"recommended_strategy": recommended['strategy_name'],
"margin_percentage": recommended.margin_percentage,
"confidence_score": recommended.confidence_score,
"justification": recommended.justification,
"price_breakdown": recommended.price_breakdown,
"risk_factors": recommended.risk_factors,
"historical_context": {
"count": "1000+",  # Placeholder - would be filled from actual historical analysis
"competitive_positioning": f"{recommended['strategy_name'].replace('_', ' ').title()} market positioning",
return formatted_pricing
def generate_bid_document(self, rfp_data: Dict[str, Any]) -> Dict[str, Any]:
Generate complete bid document integrating all pipeline components.
rfp_data: RFP information dictionary
Returns:
Dictionary containing generated bid document and metadata
self.logger.info(f"Generating bid document for: {rfp_data.get('title', 'Unknown RFP')}")
generation_start = time.time()
except ImportError:
generation_start = 0
# Step 1: Generate compliance matrix
compliance_matrix = None
if self.compliance_generator:
compliance_matrix = self.compliance_generator.generate_compliance_matrix(rfp_data)
self.logger.info(f"Compliance matrix generated with {len(compliance_matrix['requirements_and_responses'])} requirements")
self.logger.error(f"Compliance matrix generation failed: {e}")
compliance_matrix = self._create_default_compliance_matrix()
# Step 2: Generate pricing
pricing_results = None
if self.pricing_engine:
extracted_requirements = compliance_matrix.get('requirements_and_responses', [])
pricing_results = self.pricing_engine.compare_strategies(rfp_data, extracted_requirements)
self.logger.info(f"Pricing analysis completed with {len(pricing_results)} strategies")
self.logger.error(f"Pricing generation failed: {e}")
pricing_results = self._create_default_pricing()
# Step 3: Generate content sections
executive_summary = self._generate_executive_summary(
rfp_data, compliance_matrix['compliance_summary'],
list(pricing_results.values())[0] if pricing_results else {}
technical_approach = self._generate_technical_approach(rfp_data, compliance_matrix)
formatted_pricing = self._format_pricing_for_document(pricing_results)
# Step 4: Prepare template variables
template_vars = {
"rfp_info": {
"title": rfp_data.get('title', 'Government Contract'),
"agency": rfp_data.get('agency', 'Government Agency'),
"solicitation_number": rfp_data.get('solicitation_number', 'TBD'),
"naics_code": rfp_data.get('naics_code', 'TBD'),
"rfp_id": rfp_data.get('rfp_id', 'unknown')
"company_profile": self.content_library['company_profile'],
"executive_summary": executive_summary,
"technical_approach": technical_approach,
"pricing": formatted_pricing,
"compliance": compliance_matrix['compliance_summary'],
"compliance_details": compliance_matrix,
"terms_conditions": self.content_library['standard_clauses']['terms_and_conditions'],
"submission_date": datetime.now().strftime("%B %d, %Y"),
"proposal_validity_date": (datetime.now() + timedelta(days=30)).strftime("%B %d, %Y"),
"rfp_category": category.replace('_', ' ').title()
# Step 5: Generate document content
template = Template(self.templates["main_bid_template"])
# Add custom filters
def number_format(value):
return f"{float(value):,.2f}"
except:
return str(value)
template.globals['number_format'] = number_format
document_content = template.render(**template_vars)
# Step 6: Create bid document package
bid_document = {
"rfp_info": template_vars["rfp_info"],
"content": {
"markdown": document_content,
"html": markdown.markdown(document_content, extensions=['tables']),
"sections": {
"company_qualifications": self._format_company_qualifications(),
"compliance_matrix": compliance_matrix,
"terms_conditions": self.content_library['standard_clauses']['terms_and_conditions']
"metadata": {
"generated_at": datetime.now().isoformat(),
"generator_version": "1.0.0",
"components_used": {
"rag_engine": self.rag_engine is not None,
"compliance_generator": self.compliance_generator is not None,
"pricing_engine": self.pricing_engine is not None
"document_stats": {
"total_sections": 6,
"content_length": len(document_content),
"requirements_addressed": len(compliance_matrix.get('requirements_and_responses', [])),
"pricing_strategies_analyzed": len(pricing_results) if pricing_results else 0
# Calculate generation time
generation_time = time.time() - generation_start
bid_document['metadata']['generation_time_seconds'] = generation_time
self.logger.info(f"Bid document generated in {generation_time:.2f} seconds")
bid_document['metadata']['generation_time_seconds'] = 0
return bid_document
def _create_default_compliance_matrix(self) -> Dict[str, Any]:
"compliance_summary": {
"total_requirements": 5,
"compliant": 4,
"partial": 1,
"review_required": 0,
"compliance_rate": 0.8,
"requirements_and_responses": [
"requirement_id": "default_req_1",
"requirement_text": "Meet all technical specifications",
"compliance_status": "compliant",
"response_text": "We fully comply with all technical specifications through proven methodologies.",
"category": "technical",
"mandatory": True
def _create_default_pricing(self) -> Dict[str, Any]:
"competitive": type('PricingResult', (), {
'total_price': 100000.0,
'base_cost': 75000.0,
'margin_percentage': 25.0,
'pricing_strategy': 'competitive',
'confidence_score': 0.7,
'justification': 'Competitive pricing based on industry standards',
'price_breakdown': {
'overhead': 15000.0,
'profit': 10000.0
'risk_factors': []
})
def _format_company_qualifications(self) -> str:
company = self.content_library['company_profile']
qualifications = []
qualifications.append(f"**Experience:** {company['established']} - Present")
qualifications.append(f"**Team Size:** {company['employees']} professionals")
qualifications.append(f"**Certifications:** {', '.join(company['certifications'])}")
return "\n".join(qualifications)
def export_bid_document(self, bid_document: Dict[str, Any],
output_format: str = "markdown") -> str:
Export bid document to various formats.
bid_document: Generated bid document
output_format: Output format (markdown, html, pdf)
Path to exported file
rfp_id = bid_document['rfp_info'].get('rfp_id', 'unknown')
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
if output_format.lower() == "markdown":
filename = f"bid_document_{rfp_id}_{timestamp}.md"
filepath = os.path.join(self.output_dir, filename)
with open(filepath, 'w') as f:
f.write(bid_document['content']['markdown'])
elif output_format.lower() == "html":
filename = f"bid_document_{rfp_id}_{timestamp}.html"
# Create professional HTML with CSS
html_content = f"""
# [REMOVED: Invalid HTML/CSS block; this content should be in a Jinja2/template or an actual HTML file, not in Python logic.]
</html>
f.write(html_content)
elif output_format.lower() == "json":
filename = f"bid_document_{rfp_id}_{timestamp}.json"
json.dump(bid_document, f, indent=2)
raise ValueError(f"Unsupported output format: {output_format}")
self.logger.info(f"Bid document exported to: {filepath}")
return filepath
def main():
print("Testing Bid Document Generator")
print("=" * 50)
# Initialize integrated system
generator = BidDocumentGenerator()
# Try to load other components
from compliance.compliance_matrix import ComplianceMatrixGenerator
from pricing.pricing_engine import PricingEngine
compliance_gen = ComplianceMatrixGenerator()
pricing_engine = PricingEngine()
# Initialize with integrated components
generator = BidDocumentGenerator(
compliance_generator=compliance_gen,
pricing_engine=pricing_engine
print("✅ Initialized with full pipeline integration")
print(f"⚠️  Initialized in standalone mode: {e}")
# Load test RFP
df = pd.read_parquet('/app/government_rfp_bid_1927/data/processed/rfp_master_dataset.parquet')
test_rfp = df[df['description'].notna()].iloc[0].to_dict()
print(f"\nTest RFP: {test_rfp['title']}")
print(f"Agency: {test_rfp['agency']}")
print(f"NAICS: {test_rfp.get('naics_code', 'N/A')}")
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
print(f"Markdown: {markdown_path}")
print(f"HTML: {html_path}")
print(f"JSON: {json_path}")
# Validate file creation
for path in [markdown_path, html_path, json_path]:
if os.path.exists(path):
size = os.path.getsize(path)
print(f"✅ {os.path.basename(path)}: {size:,} bytes")
print(f"❌ {os.path.basename(path)}: Not created")
# Show content preview
print(f"\nDocument Content Preview:")
content_preview = bid_document['content']['markdown'][:500]
print(f"{content_preview}...")
return True
print(f"❌ Error testing bid document generator: {e}")
import traceback
traceback.print_exc()
return False
if __name__ == "__main__":
success = main()
sys.exit(0 if success else 1)