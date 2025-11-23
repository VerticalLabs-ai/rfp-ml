"""
RFP Processor Service - Integrates ML pipeline with API.
"""
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from uuid import uuid4

# Add src to path for ML components
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Background job tracking
processing_jobs = {}
generated_bids = {}  # Store generated bid documents


class RFPProcessor:
    """Processes RFPs through the ML pipeline."""
    
    def __init__(self):
        """Initialize ML components."""
        self.rag_engine = None
        self.compliance_generator = None
        self.pricing_engine = None
        self.go_nogo_engine = None
        self.bid_generator = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Lazy load ML components to avoid startup overhead."""
        try:
            from src.rag.rag_engine import RAGEngine
            from src.compliance.compliance_matrix import ComplianceMatrixGenerator
            from src.pricing.pricing_engine import PricingEngine
            from src.decision.go_nogo_engine import GoNoGoEngine
            from src.bid_generation.document_generator import BidDocumentGenerator
            
            # Initialize components
            self.rag_engine = RAGEngine()
            self.compliance_generator = ComplianceMatrixGenerator()
            self.pricing_engine = PricingEngine()
            self.go_nogo_engine = GoNoGoEngine(
                compliance_generator=self.compliance_generator,
                pricing_engine=self.pricing_engine
            )
            self.bid_generator = BidDocumentGenerator(
                rag_engine=self.rag_engine,
                compliance_generator=self.compliance_generator,
                pricing_engine=self.pricing_engine
            )
            print("✅ ML components initialized successfully")
        except Exception as e:
            print(f"⚠️  ML components not available: {e}")
            print("   Using mock processing mode")
    
    async def process_single_rfp(self, rfp_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single RFP through the ML pipeline.
        
        Args:
            rfp_data: RFP details (title, agency, description, etc.)
            
        Returns:
            Processed RFP with triage score, decision, pricing, etc.
        """
        try:
            result = {
                **rfp_data,
                "processed_at": datetime.now().isoformat(),
                "triage_score": None,
                "decision_recommendation": None,
                "pricing": None,
                "compliance_matrix": None
            }
            
            # If ML components available, process through pipeline
            if self.go_nogo_engine:
                # Run through Go/No-Go engine (includes compliance + pricing)
                decision = self.go_nogo_engine.analyze_rfp_opportunity(rfp_data)
                
                # Extract results
                if hasattr(decision, '__dict__'):
                    decision_dict = decision.__dict__
                elif isinstance(decision, dict):
                    decision_dict = decision
                else:
                    decision_dict = {}
                
                result.update({
                    "triage_score": decision_dict.get("overall_score", 75.0),
                    "decision_recommendation": decision_dict.get("recommendation", "review"),
                    "confidence_level": decision_dict.get("confidence_level", 0.8),
                    "justification": decision_dict.get("justification", ""),
                    "risk_factors": decision_dict.get("risk_factors", []),
                    "strengths": decision_dict.get("strengths", [])
                })
            else:
                # Mock processing - calculate simple triage score
                award_amount = rfp_data.get("award_amount", 0) or 0
                description_length = len(rfp_data.get("description", ""))
                
                # Simple scoring
                amount_score = min(award_amount / 1000000 * 50, 50)  # Up to 50 points
                complexity_score = min(description_length / 2000 * 30, 30)  # Up to 30 points
                base_score = 20  # Base 20 points
                
                triage_score = min(amount_score + complexity_score + base_score, 100)
                
                result.update({
                    "triage_score": round(triage_score, 2),
                    "decision_recommendation": "go" if triage_score >= 70 else "review" if triage_score >= 50 else "no-go",
                    "confidence_level": 0.7,
                    "justification": f"Mock scoring based on award amount and complexity",
                    "processing_mode": "mock"
                })
            
            return result
            
        except Exception as e:
            print(f"Error processing RFP: {e}")
            return {
                **rfp_data,
                "error": str(e),
                "triage_score": 0,
                "decision_recommendation": "error"
            }
    
    async def generate_bid_document(self, rfp_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a complete bid document for an RFP.
        
        Args:
            rfp_data: RFP details
            
        Returns:
            Generated bid document with content in multiple formats
        """
        try:
            if self.bid_generator:
                # Use full bid generator
                bid_document = self.bid_generator.generate_bid_document(rfp_data)
            else:
                # Mock bid generation
                bid_document = {
                    "rfp_info": {
                        "title": rfp_data.get("title", "Unknown"),
                        "agency": rfp_data.get("agency", "Unknown"),
                        "rfp_id": rfp_data.get("rfp_id", "unknown")
                    },
                    "content": {
                        "markdown": f"# Mock Bid Document\n\nFor RFP: {rfp_data.get('title')}",
                        "html": f"<h1>Mock Bid Document</h1><p>For RFP: {rfp_data.get('title')}</p>",
                        "sections": {}
                    },
                    "metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "processing_mode": "mock"
                    }
                }
            
            # Store in memory (in production, save to database)
            bid_id = f"BID-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            generated_bids[bid_id] = bid_document
            
            return {
                "bid_id": bid_id,
                "rfp_id": rfp_data.get("rfp_id"),
                **bid_document
            }
            
        except Exception as e:
            print(f"Error generating bid document: {e}")
            return {
                "error": str(e),
                "bid_id": None
            }
    
    def get_bid_document(self, bid_id: str) -> Optional[Dict]:
        """Get a generated bid document by ID."""
        return generated_bids.get(bid_id)

    def update_bid_document_content(self, bid_id: str, new_content_markdown: str):
        """
        Update the markdown content of an existing bid document.
        This is used for real-time collaborative editing.
        """
        if bid_id in generated_bids:
            generated_bids[bid_id]["content"]["markdown"] = new_content_markdown
            generated_bids[bid_id]["metadata"]["updated_at"] = datetime.now().isoformat()
            print(f"Updated bid document {bid_id} content.")
        else:
            print(f"Warning: Bid document {bid_id} not found for content update.")

    def export_bid_document(self, bid_id: str, format: str = "markdown") -> Optional[str]:
        """
        Export a bid document to a file.
        
        Args:
            bid_id: ID of the bid document
            format: Output format (markdown, html, json)
            
        Returns:
            File path of exported document
        """
        bid_document = generated_bids.get(bid_id)
        if not bid_document or not self.bid_generator:
            return None
            
        try:
            filepath = self.bid_generator.export_bid_document(bid_document, format)
            return filepath
        except Exception as e:
            print(f"Error exporting bid document: {e}")
            return None
    
    async def process_single_rfp(self, rfp_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single RFP through the ML pipeline.
        
        Args:
            rfp_data: RFP details (title, agency, description, etc.)
            
        Returns:
            Processed RFP with triage score, decision, pricing, etc.
        """
        try:
            result = {
                **rfp_data,
                "processed_at": datetime.now().isoformat(),
                "triage_score": None,
                "decision_recommendation": None,
                "pricing": None,
                "compliance_matrix": None
            }
            
            # If ML components available, process through pipeline
            if self.go_nogo_engine:
                # Run through Go/No-Go engine (includes compliance + pricing)
                decision = self.go_nogo_engine.analyze_rfp_opportunity(rfp_data)
                
                # Extract results
                if hasattr(decision, '__dict__'):
                    decision_dict = decision.__dict__
                elif isinstance(decision, dict):
                    decision_dict = decision
                else:
                    decision_dict = {}
                
                result.update({
                    "triage_score": decision_dict.get("overall_score", 75.0),
                    "decision_recommendation": decision_dict.get("recommendation", "review"),
                    "confidence_level": decision_dict.get("confidence_level", 0.8),
                    "justification": decision_dict.get("justification", ""),
                    "risk_factors": decision_dict.get("risk_factors", []),
                    "strengths": decision_dict.get("strengths", [])
                })
            else:
                # Mock processing - calculate simple triage score
                award_amount = rfp_data.get("award_amount", 0) or 0
                description_length = len(rfp_data.get("description", ""))
                
                # Simple scoring
                amount_score = min(award_amount / 1000000 * 50, 50)  # Up to 50 points
                complexity_score = min(description_length / 2000 * 30, 30)  # Up to 30 points
                base_score = 20  # Base 20 points
                
                triage_score = min(amount_score + complexity_score + base_score, 100)
                
                result.update({
                    "triage_score": round(triage_score, 2),
                    "decision_recommendation": "go" if triage_score >= 70 else "review" if triage_score >= 50 else "no-go",
                    "confidence_level": 0.7,
                    "justification": f"Mock scoring based on award amount and complexity",
                    "processing_mode": "mock"
                })
            
            return result
            
        except Exception as e:
            print(f"Error processing RFP: {e}")
            return {
                **rfp_data,
                "error": str(e),
                "triage_score": 0,
                "decision_recommendation": "error"
            }
    
    async def discover_rfps(self, filters: Optional[Dict] = None) -> str:
        """
        Trigger automated RFP discovery.
        
        Returns job_id for status tracking.
        """
        job_id = str(uuid4())
        
        processing_jobs[job_id] = {
            "status": "running",
            "discovered_count": 0,
            "processed_count": 0,
            "started_at": datetime.now().isoformat(),
            "rfps": []
        }
        
        # Run discovery in background
        asyncio.create_task(self._run_discovery(job_id, filters))
        
        return job_id
    
    async def _run_discovery(self, job_id: str, filters: Optional[Dict] = None):
        """Background task for RFP discovery."""
        try:
            from src.agents.discovery_agent import RFPDiscoveryAgent
            from app.core.config import settings
            
            agent = RFPDiscoveryAgent()
            
            # Extract parameters
            days_back = filters.get("days_back", 30) if filters else 30
            limit = filters.get("limit", 50) if filters else 50
            
            # Call actual discovery with API key from settings
            df_rfps = agent.discover_opportunities(
                days_window=days_back,
                limit=limit,
                api_key=settings.SAM_GOV_API_KEY
            )
            
            if df_rfps.empty:
                processing_jobs[job_id]["status"] = "completed"
                processing_jobs[job_id]["discovered_count"] = 0
                return

            # Convert DataFrame to list of dicts
            discovered_rfps = df_rfps.to_dict(orient="records")
            
            processing_jobs[job_id]["discovered_count"] = len(discovered_rfps)
            
            # Process each RFP
            processed = []
            for rfp in discovered_rfps:
                # Ensure rfp_id exists (if not in CSV, generate one or use solicitation number)
                if "rfp_id" not in rfp or not rfp["rfp_id"]:
                    rfp["rfp_id"] = rfp.get("solicitation_number") or f"RFP-{uuid4()}"
                
                # Ensure other required fields
                if "title" not in rfp: rfp["title"] = "Untitled RFP"
                if "agency" not in rfp: rfp["agency"] = "Unknown Agency"
                
                result = await self.process_single_rfp(rfp)
                processed.append(result)
                processing_jobs[job_id]["processed_count"] += 1
                await asyncio.sleep(0.1)  # Small yield
            
            processing_jobs[job_id]["rfps"] = processed
            processing_jobs[job_id]["status"] = "completed"
            processing_jobs[job_id]["completed_at"] = datetime.now().isoformat()
            
        except Exception as e:
            print(f"Discovery failed: {e}")
            processing_jobs[job_id]["status"] = "failed"
            processing_jobs[job_id]["error"] = str(e)
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a discovery job."""
        return processing_jobs.get(job_id)


# Global processor instance
processor = RFPProcessor()
