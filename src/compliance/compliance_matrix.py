"""
Compliance Matrix Generator for RFP bid generation system.
Extracts requirements from RFPs and generates compliance responses using RAG and LLM.
"""
import os
import sys
import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
# Add src to path for imports
sys.path.insert(0, '/app/government_rfp_bid_1927/src')
class ComplianceMatrixGenerator:
    """
    Generate compliance matrices that map RFP requirements to bid responses.
    Uses LLM for requirement extraction and RAG for response generation.
    """
    def __init__(
        self,
        rag_engine=None,
        llm_config=None,
        output_dir: str = "/app/government_rfp_bid_1927/data/compliance",
        templates_dir: str = "/app/government_rfp_bid_1927/data/templates"
    ):
        """
        Initialize compliance matrix generator.
        Args:
            rag_engine: RAG engine instance for context retrieval
            llm_config: LLM configuration for requirement extraction
            output_dir: Directory for compliance matrix outputs
            templates_dir: Directory for response templates
        """
        self.rag_engine = rag_engine
        self.llm_config = llm_config
        self.output_dir = output_dir
        self.templates_dir = templates_dir
        # Create directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.templates_dir, exist_ok=True)
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        # Load response templates
        self.response_templates = self._load_response_templates()
        # Requirement extraction patterns
        self.requirement_patterns = self._get_requirement_patterns()
    def _load_response_templates(self) -> Dict[str, Any]:
        """Load or create response templates for common compliance items."""
        templates_path = os.path.join(self.templates_dir, "compliance_response_templates.json")
        # Default templates if file doesn't exist
        default_templates = {
            "technical_requirements": {
                "pattern_keywords": ["technical", "specification", "requirement", "standard"],
                "response_template": "Our solution meets this technical requirement through {approach}. We have {experience} experience with {technology} and can deliver {outcome}."
            },
            "financial_requirements": {
                "pattern_keywords": ["cost", "price", "budget", "financial", "payment"],
                "response_template": "We comply with the financial requirements by {pricing_approach}. Our pricing structure includes {cost_breakdown} with total cost of {amount}."
            },
            "legal_requirements": {
                "pattern_keywords": ["legal", "regulation", "compliance", "law", "statute"],
                "response_template": "We fully comply with all legal requirements including {regulations}. Our compliance program ensures {compliance_measures}."
            },
            "administrative_requirements": {
                "pattern_keywords": ["submission", "deadline", "format", "document", "administrative"],
                "response_template": "We will meet all administrative requirements by {approach}. Our submission will include {deliverables} by {timeline}."
            },
            "performance_requirements": {
                "pattern_keywords": ["performance", "metric", "kpi", "benchmark", "target"],
                "response_template": "We commit to meeting performance requirements with {performance_approach}. Our track record shows {metrics} with {success_rate}."
            },
            "security_requirements": {
                "pattern_keywords": ["security", "clearance", "background", "confidential", "classified"],
                "response_template": "We maintain compliance with security requirements through {security_measures}. Our personnel have {clearance_level} and follow {protocols}."
            }
        }
        if os.path.exists(templates_path):
            try:
                with open(templates_path, 'r') as f:
                    templates = json.load(f)
                self.logger.info(f"Loaded response templates from {templates_path}")
                return templates
            except Exception as e:
                self.logger.warning(f"Failed to load templates: {e}, using defaults")
        # Save default templates
        with open(templates_path, 'w') as f:
            json.dump(default_templates, f, indent=2)
        self.logger.info(f"Created default response templates at {templates_path}")
        return default_templates
    def _get_requirement_patterns(self) -> List[Dict[str, Any]]:
        """Define patterns for extracting requirements from RFP text."""
        return [
            {
                "name": "mandatory_requirements",
                "patterns": [
                    r"(?i)\b(?:must|shall|required|mandatory|essential)\b.*?(?:[.!?]|\n)",
                    r"(?i)(?:requirement|specification|standard).*?(?:[.!?]|\n)",
                    r"(?i)\b(?:minimum|maximum)\b.*?(?:[.!?]|\n)"
                ],
                "category": "mandatory"
            },
            {
                "name": "technical_specifications",
                "patterns": [
                    r"(?i)(?:technical|specification|standard|protocol).*?(?:[.!?]|\n)",
                    r"(?i)(?:system|software|hardware|equipment).*?(?:[.!?]|\n)",
                    r"(?i)(?:capability|feature|function).*?(?:[.!?]|\n)"
                ],
                "category": "technical"
            },
            {
                "name": "submission_requirements",
                "patterns": [
                    r"(?i)(?:submit|provide|include|attach).*?(?:[.!?]|\n)",
                    r"(?i)(?:deadline|due date|submission date).*?(?:[.!?]|\n)",
                    r"(?i)(?:format|template|structure).*?(?:[.!?]|\n)"
                ],
                "category": "administrative"
            },
            {
                "name": "qualification_requirements",
                "patterns": [
                    r"(?i)(?:experience|qualification|certification).*?(?:[.!?]|\n)",
                    r"(?i)(?:years?\s+of|minimum.*experience).*?(?:[.!?]|\n)",
                    r"(?i)(?:licensed|certified|qualified).*?(?:[.!?]|\n)"
                ],
                "category": "qualification"
            },
            {
                "name": "performance_requirements",
                "patterns": [
                    r"(?i)(?:performance|metric|kpi|target).*?(?:[.!?]|\n)",
                    r"(?i)(?:delivery time|timeline|schedule).*?(?:[.!?]|\n)",
                    r"(?i)(?:sla|service level|availability).*?(?:[.!?]|\n)"
                ],
                "category": "performance"
            }
        ]
    def extract_requirements_rule_based(self, rfp_text: str) -> List[Dict[str, Any]]:
        """
        Extract requirements using rule-based pattern matching.
        Args:
            rfp_text: RFP description text
        Returns:
            List of extracted requirements with metadata
        """
        requirements = []
        if not rfp_text or not isinstance(rfp_text, str):
            return requirements
        # Clean text
        clean_text = re.sub(r'\s+', ' ', rfp_text.strip())
        for pattern_group in self.requirement_patterns:
            for pattern in pattern_group["patterns"]:
                matches = re.findall(pattern, clean_text, re.MULTILINE | re.DOTALL)
                for match in matches:
                    if len(match.strip()) > 20:  # Filter out very short matches
                        requirement = {
                            "id": f"req_{len(requirements) + 1}",
                            "text": match.strip(),
                            "category": pattern_group["category"],
                            "extraction_method": "rule_based",
                            "pattern_type": pattern_group["name"],
                            "mandatory": pattern_group["category"] == "mandatory",
                            "confidence": 0.7  # Rule-based confidence
                        }
                        requirements.append(requirement)
        # Remove duplicates and very similar requirements
        requirements = self._deduplicate_requirements(requirements)
        return requirements
    def extract_requirements_llm(self, rfp_text: str) -> List[Dict[str, Any]]:
        """
        Extract requirements using LLM-based analysis.
        Note: This is a placeholder for LLM integration. 
        In production, this would use the configured LLM API.
        Args:
            rfp_text: RFP description text
        Returns:
            List of extracted requirements with metadata
        """
        # Placeholder LLM-based extraction
        # In a real implementation, this would call an LLM API
        requirements = []
        # For now, use enhanced rule-based extraction with LLM-style analysis
        sentences = re.split(r'[.!?]+', rfp_text)
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) < 30:  # Skip very short sentences
                continue
            # LLM-style requirement detection
            requirement_indicators = [
                'must', 'shall', 'required', 'mandatory', 'essential',
                'minimum', 'maximum', 'specification', 'standard',
                'provide', 'submit', 'include', 'demonstrate'
            ]
            if any(indicator in sentence.lower() for indicator in requirement_indicators):
                # Determine category based on content
                category = self._categorize_requirement(sentence)
                requirement = {
                    "id": f"llm_req_{len(requirements) + 1}",
                    "text": sentence,
                    "category": category,
                    "extraction_method": "llm_based",
                    "mandatory": any(word in sentence.lower() for word in ['must', 'shall', 'required', 'mandatory']),
                    "confidence": 0.8  # Higher confidence for LLM-based
                }
                requirements.append(requirement)
        return requirements
    def _categorize_requirement(self, text: str) -> str:
        """Categorize a requirement based on its content."""
        text_lower = text.lower()
        if any(word in text_lower for word in ['technical', 'specification', 'system', 'software', 'hardware']):
            return 'technical'
        elif any(word in text_lower for word in ['cost', 'price', 'budget', 'financial', 'payment']):
            return 'financial'
        elif any(word in text_lower for word in ['experience', 'qualification', 'certification', 'licensed']):
            return 'qualification'
        elif any(word in text_lower for word in ['performance', 'metric', 'kpi', 'delivery', 'timeline']):
            return 'performance'
        elif any(word in text_lower for word in ['security', 'clearance', 'confidential', 'classified']):
            return 'security'
        elif any(word in text_lower for word in ['legal', 'regulation', 'compliance', 'law']):
            return 'legal'
        elif any(word in text_lower for word in ['submit', 'format', 'deadline', 'administrative']):
            return 'administrative'
        else:
            return 'general'
    def _deduplicate_requirements(self, requirements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate and very similar requirements."""
        if not requirements:
            return requirements
        # Simple deduplication based on text similarity
        unique_requirements = []
        seen_texts = set()
        for req in requirements:
            # Normalize text for comparison
            normalized_text = re.sub(r'\s+', ' ', req['text'].lower().strip())
            # Check if we've seen very similar text
            is_duplicate = False
            for seen_text in seen_texts:
                # Simple similarity check - could be enhanced with more sophisticated methods
                if len(set(normalized_text.split()) & set(seen_text.split())) / max(len(normalized_text.split()), len(seen_text.split())) > 0.8:
                    is_duplicate = True
                    break
            if not is_duplicate and len(normalized_text) > 20:
                unique_requirements.append(req)
                seen_texts.add(normalized_text)
        return unique_requirements
    def generate_compliance_response(self, requirement: Dict[str, Any], rfp_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a compliance response for a specific requirement.
        Args:
            requirement: Requirement dictionary
            rfp_context: RFP context information
        Returns:
            Response dictionary with compliance information
        """
        # Get relevant context from RAG if available
        rag_context = None
        if self.rag_engine:
            try:
                rag_results = self.rag_engine.retrieve(requirement['text'], k=3)
                if rag_results:
                    rag_context = [r['text'] for r in rag_results[:2]]  # Top 2 results
            except Exception as e:
                self.logger.warning(f"RAG retrieval failed: {e}")
        # Get appropriate template
        category = requirement.get('category', 'general')
        template_info = self.response_templates.get(category + '_requirements', 
                                                  self.response_templates.get('technical_requirements'))
        # Generate response based on category and context
        response_text = self._generate_category_response(requirement, rfp_context, rag_context, template_info)
        # Determine compliance status
        compliance_status = self._assess_compliance_status(requirement, rfp_context)
        response = {
            "requirement_id": requirement['id'],
            "requirement_text": requirement['text'],
            "compliance_status": compliance_status,
            "response_text": response_text,
            "category": requirement['category'],
            "mandatory": requirement.get('mandatory', False),
            "confidence_score": requirement.get('confidence', 0.5),
            "supporting_evidence": rag_context[:1] if rag_context else [],
            "generated_at": datetime.now().isoformat()
        }
        return response
    def _generate_category_response(self, requirement: Dict[str, Any], rfp_context: Dict[str, Any], 
                                  rag_context: Optional[List[str]], template_info: Dict[str, Any]) -> str:
        """Generate category-specific response text."""
        category = requirement.get('category', 'general')
        if category == 'technical':
            return self._generate_technical_response(requirement, rfp_context, rag_context)
        elif category == 'financial':
            return self._generate_financial_response(requirement, rfp_context, rag_context)
        elif category == 'qualification':
            return self._generate_qualification_response(requirement, rfp_context, rag_context)
        elif category == 'performance':
            return self._generate_performance_response(requirement, rfp_context, rag_context)
        elif category == 'administrative':
            return self._generate_administrative_response(requirement, rfp_context, rag_context)
        else:
            return self._generate_general_response(requirement, rfp_context, rag_context)
    def _generate_technical_response(self, requirement: Dict[str, Any], rfp_context: Dict[str, Any], 
                                   rag_context: Optional[List[str]]) -> str:
        """Generate technical requirement response."""
        base_response = f"We fully comply with this technical requirement. "
        if 'system' in requirement['text'].lower():
            base_response += "Our system architecture is designed to meet all specified technical standards. "
        if 'software' in requirement['text'].lower():
            base_response += "Our software solution incorporates industry best practices and proven technologies. "
        if 'security' in requirement['text'].lower():
            base_response += "We implement comprehensive security measures including encryption, access controls, and monitoring. "
        if rag_context:
            base_response += f"Based on our experience with similar projects, we have successfully implemented comparable solutions. "
        base_response += "Our technical team has extensive experience and will ensure full compliance throughout the project lifecycle."
        return base_response
    def _generate_financial_response(self, requirement: Dict[str, Any], rfp_context: Dict[str, Any], 
                                   rag_context: Optional[List[str]]) -> str:
        """Generate financial requirement response."""
        return ("We comply with all financial requirements and pricing structures outlined in the RFP. "
                "Our pricing is competitive and transparent, with detailed cost breakdowns provided. "
                "We offer flexible payment terms and maintain strong financial standing with proven capability "
                "to complete projects of this scope and duration.")
    def _generate_qualification_response(self, requirement: Dict[str, Any], rfp_context: Dict[str, Any], 
                                       rag_context: Optional[List[str]]) -> str:
        """Generate qualification requirement response."""
        return ("Our team meets all qualification requirements with extensive relevant experience. "
                "We hold all necessary certifications and licenses required for this project. "
                "Our staff includes certified professionals with proven track records in similar engagements. "
                "We can provide detailed resumes and certification documentation upon request.")
    def _generate_performance_response(self, requirement: Dict[str, Any], rfp_context: Dict[str, Any], 
                                     rag_context: Optional[List[str]]) -> str:
        """Generate performance requirement response."""
        return ("We commit to meeting all performance requirements and service level agreements. "
                "Our performance management system includes regular monitoring, reporting, and continuous improvement. "
                "We have consistently exceeded performance targets in similar projects and will provide "
                "detailed performance metrics and reporting as specified.")
    def _generate_administrative_response(self, requirement: Dict[str, Any], rfp_context: Dict[str, Any], 
                                        rag_context: Optional[List[str]]) -> str:
        """Generate administrative requirement response."""
        return ("We will comply with all administrative requirements including submission formats, deadlines, and documentation. "
                "Our project management processes ensure timely delivery of all required documents and reports. "
                "We maintain comprehensive record-keeping and quality assurance procedures to ensure full compliance.")
    def _generate_general_response(self, requirement: Dict[str, Any], rfp_context: Dict[str, Any], 
                                 rag_context: Optional[List[str]]) -> str:
        """Generate general requirement response."""
        return ("We acknowledge and commit to full compliance with this requirement. "
                "Our approach will ensure all specified criteria are met through proven methodologies and best practices. "
                "We will provide regular updates and documentation to demonstrate ongoing compliance.")
    def _assess_compliance_status(self, requirement: Dict[str, Any], rfp_context: Dict[str, Any]) -> str:
        """Assess compliance status for a requirement."""
        # Simple heuristic-based assessment
        # In production, this could be enhanced with more sophisticated analysis
        mandatory = requirement.get('mandatory', False)
        confidence = requirement.get('confidence', 0.5)
        if confidence > 0.8:
            return 'compliant'
        elif confidence > 0.6:
            return 'partial'
        elif mandatory:
            return 'review_required'
        else:
            return 'compliant'
    def generate_compliance_matrix(self, rfp_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate complete compliance matrix for an RFP.
        Args:
            rfp_data: Dictionary containing RFP information
        Returns:
            Complete compliance matrix with all requirements and responses
        """
        self.logger.info(f"Generating compliance matrix for RFP: {rfp_data.get('title', 'Unknown')}")
        # Extract RFP text for analysis
        rfp_text = rfp_data.get('description', '')
        if not rfp_text:
            rfp_text = rfp_data.get('title', '') + ' ' + rfp_data.get('agency', '')
        # Extract requirements using both methods
        rule_requirements = self.extract_requirements_rule_based(rfp_text)
        llm_requirements = self.extract_requirements_llm(rfp_text)
        # Combine and deduplicate requirements
        all_requirements = rule_requirements + llm_requirements
        unique_requirements = self._deduplicate_requirements(all_requirements)
        self.logger.info(f"Extracted {len(unique_requirements)} unique requirements")
        # Generate responses for each requirement
        compliance_responses = []
        for requirement in unique_requirements:
            response = self.generate_compliance_response(requirement, rfp_data)
            compliance_responses.append(response)
        # Calculate overall compliance metrics
        total_requirements = len(compliance_responses)
        compliant_count = len([r for r in compliance_responses if r['compliance_status'] == 'compliant'])
        partial_count = len([r for r in compliance_responses if r['compliance_status'] == 'partial'])
        review_count = len([r for r in compliance_responses if r['compliance_status'] == 'review_required'])
        compliance_rate = compliant_count / total_requirements if total_requirements > 0 else 0
        # Create compliance matrix
        compliance_matrix = {
            "rfp_info": {
                "title": rfp_data.get('title', 'Unknown'),
                "agency": rfp_data.get('agency', 'Unknown'),
                "rfp_id": rfp_data.get('rfp_id', 'Unknown'),
                "naics_code": rfp_data.get('naics_code', ''),
                "solicitation_number": rfp_data.get('solicitation_number', '')
            },
            "extraction_summary": {
                "total_requirements": total_requirements,
                "rule_based_count": len(rule_requirements),
                "llm_based_count": len(llm_requirements),
                "extraction_method": "hybrid"
            },
            "compliance_summary": {
                "total_requirements": total_requirements,
                "compliant": compliant_count,
                "partial": partial_count,
                "review_required": review_count,
                "compliance_rate": compliance_rate,
                "overall_status": "compliant" if compliance_rate >= 0.8 else "needs_review"
            },
            "requirements_and_responses": compliance_responses,
            "generated_at": datetime.now().isoformat(),
            "generator_version": "1.0.0"
        }
        return compliance_matrix
    def export_compliance_matrix(self, compliance_matrix: Dict[str, Any], 
                                output_format: str = "json") -> str:
        """
        Export compliance matrix to various formats.
        Args:
            compliance_matrix: Compliance matrix data
            output_format: Output format (json, csv, html)
        Returns:
            Path to exported file
        """
        rfp_id = compliance_matrix['rfp_info'].get('rfp_id', 'unknown')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_format.lower() == "json":
            filename = f"compliance_matrix_{rfp_id}_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(compliance_matrix, f, indent=2)
        elif output_format.lower() == "csv":
            filename = f"compliance_matrix_{rfp_id}_{timestamp}.csv"
            filepath = os.path.join(self.output_dir, filename)
            # Convert to DataFrame for CSV export
            responses_data = []
            for response in compliance_matrix['requirements_and_responses']:
                responses_data.append({
                    'Requirement_ID': response['requirement_id'],
                    'Category': response['category'],
                    'Mandatory': response['mandatory'],
                    'Requirement_Text': response['requirement_text'],
                    'Compliance_Status': response['compliance_status'],
                    'Response_Text': response['response_text'],
                    'Confidence_Score': response['confidence_score']
                })
            df = pd.DataFrame(responses_data)
            df.to_csv(filepath, index=False)
        elif output_format.lower() == "html":
            filename = f"compliance_matrix_{rfp_id}_{timestamp}.html"
            filepath = os.path.join(self.output_dir, filename)
            html_content = self._generate_html_matrix(compliance_matrix)
            with open(filepath, 'w') as f:
                f.write(html_content)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        self.logger.info(f"Compliance matrix exported to: {filepath}")
        return filepath
    def _generate_html_matrix(self, compliance_matrix: Dict[str, Any]) -> str:
        """Generate HTML formatted compliance matrix."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Compliance Matrix - {compliance_matrix['rfp_info']['title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; padding: 15px; background-color: #e8f4f8; border-radius: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .compliant {{ background-color: #d4edda; }}
                .partial {{ background-color: #fff3cd; }}
                .review {{ background-color: #f8d7da; }}
                .mandatory {{ font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Compliance Matrix</h1>
                <p><strong>RFP Title:</strong> {compliance_matrix['rfp_info']['title']}</p>
                <p><strong>Agency:</strong> {compliance_matrix['rfp_info']['agency']}</p>
                <p><strong>RFP ID:</strong> {compliance_matrix['rfp_info']['rfp_id']}</p>
                <p><strong>Generated:</strong> {compliance_matrix['generated_at']}</p>
            </div>
            <div class="summary">
                <h2>Compliance Summary</h2>
                <p><strong>Total Requirements:</strong> {compliance_matrix['compliance_summary']['total_requirements']}</p>
                <p><strong>Compliant:</strong> {compliance_matrix['compliance_summary']['compliant']}</p>
                <p><strong>Partial:</strong> {compliance_matrix['compliance_summary']['partial']}</p>
                <p><strong>Review Required:</strong> {compliance_matrix['compliance_summary']['review_required']}</p>
                <p><strong>Compliance Rate:</strong> {compliance_matrix['compliance_summary']['compliance_rate']:.1%}</p>
                <p><strong>Overall Status:</strong> {compliance_matrix['compliance_summary']['overall_status']}</p>
            </div>
            <h2>Requirements and Responses</h2>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Category</th>
                    <th>Requirement</th>
                    <th>Status</th>
                    <th>Response</th>
                    <th>Confidence</th>
                </tr>
        """
        for response in compliance_matrix['requirements_and_responses']:
            status_class = response['compliance_status']
            mandatory_class = "mandatory" if response['mandatory'] else ""
            html += f"""
                <tr class="{status_class}">
                    <td class="{mandatory_class}">{response['requirement_id']}</td>
                    <td>{response['category']}</td>
                    <td class="{mandatory_class}">{response['requirement_text']}</td>
                    <td>{response['compliance_status']}</td>
                    <td>{response['response_text']}</td>
                    <td>{response['confidence_score']:.2f}</td>
                </tr>
            """
        html += """
            </table>
        </body>
        </html>
        """
        return html
def main():
    """Main function for testing compliance matrix generator."""
    import sys
    sys.path.insert(0, '/app/government_rfp_bid_1927/src')
    # Initialize compliance matrix generator
    generator = ComplianceMatrixGenerator()
    # Load a sample RFP for testing
    try:
        df = pd.read_parquet('/app/government_rfp_bid_1927/data/processed/rfp_master_dataset.parquet')
        sample_rfp = df[df['description'].notna()].iloc[0].to_dict()
        print("Testing Compliance Matrix Generator")
        print("=" * 50)
        print(f"Sample RFP: {sample_rfp['title']}")
        print(f"Agency: {sample_rfp['agency']}")
        # Generate compliance matrix
        compliance_matrix = generator.generate_compliance_matrix(sample_rfp)
        # Export in multiple formats
        json_path = generator.export_compliance_matrix(compliance_matrix, "json")
        csv_path = generator.export_compliance_matrix(compliance_matrix, "csv")
        html_path = generator.export_compliance_matrix(compliance_matrix, "html")
        print(f"\nCompliance matrix generated successfully!")
        print(f"Total requirements extracted: {compliance_matrix['compliance_summary']['total_requirements']}")
        print(f"Compliance rate: {compliance_matrix['compliance_summary']['compliance_rate']:.1%}")
        print(f"Overall status: {compliance_matrix['compliance_summary']['overall_status']}")
        print(f"\nExported files:")
        print(f"JSON: {json_path}")
        print(f"CSV: {csv_path}")
        print(f"HTML: {html_path}")
        # Show sample requirements
        print(f"\nSample requirements:")
        for i, response in enumerate(compliance_matrix['requirements_and_responses'][:3]):
            print(f"\n{i+1}. [{response['category']}] {response['requirement_text'][:100]}...")
            print(f"   Status: {response['compliance_status']}")
            print(f"   Response: {response['response_text'][:150]}...")
        return True
    except Exception as e:
        print(f"Error testing compliance matrix generator: {e}")
        return False
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)