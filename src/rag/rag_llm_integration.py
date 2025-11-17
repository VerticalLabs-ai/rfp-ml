"""
RAG-LLM Integration Module
This module integrates the RAG engine with the LLM infrastructure to provide
context-enhanced bid generation, requirement extraction, and pricing analysis.
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.rag.rag_engine import create_rag_engine, RAGEngine, RAGContext
from src.config.llm_adapter import create_llm_interface
@dataclass
class EnhancedGenerationResult:
    """Result from RAG-enhanced generation"""
    query: str
    generated_text: str
    context_used: str
    documents_retrieved: int
    retrieval_method: str
    llm_backend: str
    token_usage: Dict[str, int]
    metadata: Dict[str, Any]
class RAGLLMIntegrator:
    """Integrates RAG retrieval with LLM generation for enhanced bid content"""
    def __init__(self, rag_config_overrides: Optional[Dict] = None):
        """Initialize RAG-LLM integrator"""
        self.logger = logging.getLogger(__name__)
        # Initialize components
        self.rag_engine = create_rag_engine(rag_config_overrides)
        self.llm_interface = create_llm_interface()
        # Build RAG index if not already built
        if not self.rag_engine.is_built:
            self.logger.info("Building RAG index...")
            self.rag_engine.build_index()
        self.logger.info("RAG-LLM Integrator initialized")
    def _create_enhanced_prompt(self, query: str, context: RAGContext, use_case: str) -> str:
        """Create enhanced prompt with retrieved context"""
        if use_case == "bid_generation":
            prompt_template = f"""You are generating a professional bid response for a government RFP.
Query: {query}
Relevant Context from Similar RFPs:
{context.context_text[:1500]}
Based on the above context and query, generate a comprehensive, professional bid response that:
1. Addresses the specific requirements mentioned
2. Uses relevant information from similar contracts
3. Maintains a professional, government-appropriate tone
4. Includes specific details about capabilities and approach
Bid Response:"""
        elif use_case == "structured_extraction":
            prompt_template = f"""Extract and structure the key requirements from the following RFP information.
Query: {query}
Relevant RFP Context:
{context.context_text[:1500]}
Extract the following information in a structured format:
- Contract Type
- Quantities/Volumes Required
- Delivery Requirements
- Timeline/Duration
- Special Requirements
- Budget/Pricing Information
- Location/Geographic Scope
- Certifications Required
Extracted Requirements:"""
        elif use_case == "pricing":
            prompt_template = f"""Analyze pricing for the following RFP based on historical data.
Query: {query}
Historical Contract Context:
{context.context_text[:1500]}
Based on the historical data above, provide:
1. Market pricing analysis
2. Competitive pricing strategy
3. Cost factors to consider
4. Margin recommendations
5. Risk factors affecting pricing
Pricing Analysis:"""
        else:
            # Generic enhanced prompt
            prompt_template = f"""Query: {query}
Relevant Context:
{context.context_text[:1500]}
Based on the context above, provide a comprehensive response to the query:
Response:"""
        return prompt_template
    def generate_enhanced_content(
        self, 
        query: str, 
        use_case: str = "bid_generation",
        k: int = 5,
        include_metadata: bool = True
    ) -> EnhancedGenerationResult:
        """Generate content using RAG-enhanced prompts"""
        # Retrieve relevant context
        context = self.rag_engine.generate_context(query, k=k)
        # Create enhanced prompt
        enhanced_prompt = self._create_enhanced_prompt(query, context, use_case)
        # Generate with LLM
        result = self.llm_interface.generate_text(enhanced_prompt, use_case=use_case)
        # Prepare metadata
        metadata = {
            "context_length": len(context.context_text),
            "similarity_scores": [doc.similarity_score for doc in context.retrieved_documents],
            "source_datasets": list(set(doc.source_dataset for doc in context.retrieved_documents)),
            "document_ids": [doc.document_id for doc in context.retrieved_documents]
        }
        if include_metadata:
            metadata.update({
                "retrieved_documents": [
                    {
                        "id": doc.document_id,
                        "score": doc.similarity_score,
                        "source": doc.source_dataset,
                        "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
                    }
                    for doc in context.retrieved_documents
                ]
            })
        return EnhancedGenerationResult(
            query=query,
            generated_text=result["text"],
            context_used=context.context_text,
            documents_retrieved=context.total_retrieved,
            retrieval_method=context.retrieval_method,
            llm_backend=result["backend"],
            token_usage=result["usage"],
            metadata=metadata
        )
    def generate_bid_response(self, rfp_description: str, requirements: str = "") -> EnhancedGenerationResult:
        """Generate comprehensive bid response for an RFP"""
        query = f"RFP: {rfp_description}"
        if requirements:
            query += f" Requirements: {requirements}"
        return self.generate_enhanced_content(query, use_case="bid_generation", k=7)
    def extract_rfp_requirements(self, rfp_text: str) -> EnhancedGenerationResult:
        """Extract and structure RFP requirements using similar RFPs as context"""
        query = f"Extract requirements from: {rfp_text}"
        return self.generate_enhanced_content(query, use_case="structured_extraction", k=5)
    def analyze_pricing(self, contract_description: str, quantity_info: str = "") -> EnhancedGenerationResult:
        """Analyze pricing based on historical contract data"""
        query = f"Pricing analysis for: {contract_description}"
        if quantity_info:
            query += f" Quantities: {quantity_info}"
        return self.generate_enhanced_content(query, use_case="pricing", k=8)
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        rag_stats = self.rag_engine.get_statistics()
        llm_status = self.llm_interface.get_status()
        return {
            "rag_engine": rag_stats,
            "llm_interface": llm_status,
            "integration_ready": rag_stats["is_built"] and llm_status.get("current_backend") is not None,
            "total_indexed_documents": rag_stats["total_documents"],
            "embedding_model": rag_stats["embedding_model"],
            "llm_backend": llm_status.get("current_backend"),
            "capabilities": {
                "bid_generation": True,
                "requirement_extraction": True,
                "pricing_analysis": True,
                "context_retrieval": rag_stats["is_built"]
            }
        }
def create_rag_llm_integrator(rag_config_overrides: Optional[Dict] = None) -> RAGLLMIntegrator:
    """Factory function to create RAG-LLM integrator"""
    return RAGLLMIntegrator(rag_config_overrides)
# Example usage and testing
if __name__ == "__main__":
    print("=== RAG-LLM Integration Test ===")
    try:
        # Create integrator
        integrator = create_rag_llm_integrator()
        print("✓ RAG-LLM Integrator created")
        # Get system status
        status = integrator.get_system_status()
        print(f"✓ System Status: {status['integration_ready']}")
        print(f"  - RAG Documents: {status['total_indexed_documents']}")
        print(f"  - LLM Backend: {status['llm_backend']}")
        print(f"  - Embedding Model: {status['embedding_model']}")
        # Test bid generation
        print("\n--- Testing Bid Generation ---")
        bid_result = integrator.generate_bid_response(
            "Supply bottled water to federal agencies",
            "1000 cases per month for 12 months"
        )
        print(f"✓ Generated bid ({bid_result.documents_retrieved} docs retrieved)")
        print(f"  Backend: {bid_result.llm_backend}")
        print(f"  Method: {bid_result.retrieval_method}")
        print(f"  Output: {bid_result.generated_text[:150]}...")
        # Test requirement extraction
        print("\n--- Testing Requirement Extraction ---")
        req_result = integrator.extract_rfp_requirements(
            "RFP for delivery services: Supply and deliver 500 cases of bottled water monthly to 10 federal locations. Must have insurance coverage of $2M minimum. Contract duration 24 months."
        )
        print(f"✓ Extracted requirements ({req_result.documents_retrieved} docs retrieved)")
        print(f"  Output: {req_result.generated_text[:150]}...")
        # Test pricing analysis
        print("\n--- Testing Pricing Analysis ---")
        pricing_result = integrator.analyze_pricing(
            "Bottled water delivery contract",
            "500 cases monthly"
        )
        print(f"✓ Analyzed pricing ({pricing_result.documents_retrieved} docs retrieved)")
        print(f"  Output: {pricing_result.generated_text[:150]}...")
        print("\n✅ RAG-LLM Integration test completed successfully!")
    except Exception as e:
        print(f"❌ RAG-LLM Integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()