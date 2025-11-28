"""
RAG-Enhanced Pricing Integration Module
This module integrates the AI Pricing Engine with the RAG system to provide
context-enhanced pricing analysis using historical contract data and market intelligence.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.pricing.pricing_engine import PricingEngine, PricingResult
from src.rag.rag_llm_integration import create_rag_llm_integrator


class PricingStrategy(Enum):
    """Enum for pricing strategy types used in RAG integration."""

    COST_PLUS = "cost_plus"
    MARKET_BASED = "market_based"
    COMPETITIVE = "competitive"
    HYBRID = "hybrid"


def create_pricing_engine() -> PricingEngine:
    """Factory function to create PricingEngine instance."""
    return PricingEngine()


@dataclass
class EnhancedPricingResult:
    """Enhanced pricing result with RAG context"""

    pricing_result: PricingResult
    rag_analysis: str
    historical_context: str
    market_insights: list[str]
    pricing_recommendations: list[str]
    competitive_intelligence: dict[str, Any]
    documents_analyzed: int
    confidence_enhancement: float


class RAGPricingIntegrator:
    """Integrates RAG system with pricing engine for enhanced analysis"""

    def __init__(self):
        """Initialize RAG-Pricing integrator"""
        self.logger = logging.getLogger(__name__)
        # Initialize components
        self.pricing_engine = create_pricing_engine()
        self.rag_integrator = create_rag_llm_integrator()
        self.logger.info("RAG-Pricing Integrator initialized")

    def analyze_enhanced_pricing(
        self,
        category: str,
        description: str,
        quantity: float = 1.0,
        duration_months: int = 12,
        location: str = "default",
        strategy: PricingStrategy = PricingStrategy.HYBRID,
        target_margin: float | None = None,
        **additional_params,
    ) -> EnhancedPricingResult:
        """Perform enhanced pricing analysis with RAG context"""
        # Step 1: Get base pricing analysis
        rfp_data = {
            "category": category,
            "description": description,
            "quantity": quantity,
            "duration_months": duration_months,
            "location": location,
            "strategy": strategy.value,
            "target_margin": target_margin,
            **additional_params,
        }
        pricing_result = self.pricing_engine.generate_pricing(rfp_data, strategy.value)
        # Step 2: Get RAG-enhanced market analysis
        rag_analysis_result = self.rag_integrator.analyze_pricing(
            f"{description} - {category} contract",
            f"Quantity: {quantity}, Duration: {duration_months} months, Location: {location}",
        )
        # Step 3: Extract market insights from retrieved documents
        market_insights = self._extract_market_insights(
            rag_analysis_result.metadata.get("retrieved_documents", [])
        )
        # Step 4: Generate competitive intelligence
        competitive_intelligence = self._analyze_competitive_landscape(
            rag_analysis_result.metadata.get("retrieved_documents", []), pricing_result
        )
        # Step 5: Generate enhanced recommendations
        pricing_recommendations = self._generate_enhanced_recommendations(
            pricing_result, rag_analysis_result.generated_text, market_insights
        )
        # Step 6: Calculate confidence enhancement
        confidence_enhancement = self._calculate_confidence_enhancement(
            pricing_result.confidence_score,
            rag_analysis_result.documents_retrieved,
            competitive_intelligence,
        )
        return EnhancedPricingResult(
            pricing_result=pricing_result,
            rag_analysis=rag_analysis_result.generated_text,
            historical_context=(
                rag_analysis_result.context_used[:500] + "..."
                if len(rag_analysis_result.context_used) > 500
                else rag_analysis_result.context_used
            ),
            market_insights=market_insights,
            pricing_recommendations=pricing_recommendations,
            competitive_intelligence=competitive_intelligence,
            documents_analyzed=rag_analysis_result.documents_retrieved,
            confidence_enhancement=confidence_enhancement,
        )

    def _extract_market_insights(self, retrieved_documents: list[dict]) -> list[str]:
        """Extract market insights from retrieved documents"""
        insights = []
        if not retrieved_documents:
            return ["Limited historical data available for market analysis"]
        # Analyze document sources and patterns
        datasets = set()
        price_patterns = []
        for doc in retrieved_documents:
            if "source" in doc:
                datasets.add(doc["source"])
            # Look for pricing-related content in previews
            content = doc.get("content_preview", "").lower()
            if "award" in content or "contract" in content or "$" in content:
                price_patterns.append(doc.get("score", 0))
        # Generate insights based on analysis
        if len(datasets) > 1:
            insights.append(
                f"Analysis includes data from {len(datasets)} different contract categories for comprehensive market view"
            )
        if price_patterns:
            avg_relevance = sum(price_patterns) / len(price_patterns)
            if avg_relevance > 0.7:
                insights.append(
                    "High relevance pricing data found in historical contracts"
                )
            elif avg_relevance > 0.5:
                insights.append(
                    "Moderate relevance pricing data available for reference"
                )
            else:
                insights.append(
                    "Limited directly relevant pricing data, general market trends applied"
                )
        if len(retrieved_documents) >= 5:
            insights.append(
                f"Robust dataset with {len(retrieved_documents)} similar contracts analyzed"
            )
        elif len(retrieved_documents) >= 3:
            insights.append(
                f"Moderate dataset with {len(retrieved_documents)} contracts for comparison"
            )
        else:
            insights.append(
                "Limited historical data - recommendations based on cost models and general market trends"
            )
        return insights

    def _analyze_competitive_landscape(
        self, retrieved_documents: list[dict], pricing_result: PricingResult
    ) -> dict[str, Any]:
        """Analyze competitive landscape from retrieved documents"""
        competitive_intel = {
            "market_saturation": "unknown",
            "key_competitors": [],
            "pricing_patterns": {},
            "competitive_advantages": [],
            "market_positioning": "unknown",
        }
        if not retrieved_documents:
            competitive_intel["market_saturation"] = "insufficient_data"
            return competitive_intel
        # Analyze market saturation based on number of similar contracts
        contract_count = len(retrieved_documents)
        if contract_count >= 10:
            competitive_intel["market_saturation"] = "high"
        elif contract_count >= 5:
            competitive_intel["market_saturation"] = "medium"
        else:
            competitive_intel["market_saturation"] = "low"
        # Analyze pricing positioning
        market_median = pricing_result.market_analysis.median_price
        recommended_price = pricing_result.recommended_price
        if market_median > 0:
            price_ratio = recommended_price / market_median
            if price_ratio <= 0.9:
                competitive_intel["market_positioning"] = "aggressive_low"
            elif price_ratio <= 1.1:
                competitive_intel["market_positioning"] = "competitive"
            else:
                competitive_intel["market_positioning"] = "premium"
        # Generate competitive advantages based on pricing strategy
        if pricing_result.margin_achieved > 0.3:
            competitive_intel["competitive_advantages"].append(
                "Strong margin allows for service quality investment"
            )
        if pricing_result.confidence_score > 0.7:
            competitive_intel["competitive_advantages"].append(
                "High confidence pricing based on robust market data"
            )
        if pricing_result.risk_assessment.get("overall_risk", "medium") == "low":
            competitive_intel["competitive_advantages"].append(
                "Low risk pricing strategy enhances bid attractiveness"
            )
        return competitive_intel

    def _generate_enhanced_recommendations(
        self,
        pricing_result: PricingResult,
        rag_analysis: str,
        market_insights: list[str],
    ) -> list[str]:
        """Generate enhanced pricing recommendations"""
        recommendations = []
        # Base recommendations from pricing result
        if pricing_result.margin_compliance:
            recommendations.append(
                f"Recommended price of ${pricing_result.recommended_price:,.2f} meets margin requirements with {pricing_result.margin_achieved:.1%} margin"
            )
        else:
            recommendations.append(
                "WARNING: Recommended price does not meet minimum margin requirements - consider cost reduction or pricing strategy adjustment"
            )
        # Strategy-specific recommendations
        if pricing_result.strategy_used == PricingStrategy.HYBRID:
            recommendations.append(
                "Hybrid pricing strategy balances market competitiveness with cost coverage"
            )
        elif pricing_result.strategy_used == PricingStrategy.MARKET_BASED:
            recommendations.append(
                "Market-based pricing aligns with industry standards for competitive positioning"
            )
        elif pricing_result.strategy_used == PricingStrategy.COST_PLUS:
            recommendations.append(
                "Cost-plus pricing ensures full cost recovery with transparent margin structure"
            )
        # Risk-based recommendations
        overall_risk = pricing_result.risk_assessment.get("overall_risk", "medium")
        if overall_risk == "high" or overall_risk == "critical":
            recommendations.append(
                "High pricing risk detected - consider alternative pricing strategies or additional market research"
            )
        # Market data recommendations
        if pricing_result.market_analysis.similar_contracts_count < 3:
            recommendations.append(
                "Limited market data available - monitor competitor responses and adjust pricing as needed"
            )
        # Confidence-based recommendations
        if pricing_result.confidence_score < 0.5:
            recommendations.append(
                "Lower confidence in pricing due to limited data - consider conservative margin approach"
            )
        elif pricing_result.confidence_score > 0.8:
            recommendations.append(
                "High confidence pricing - well-supported by market data and cost analysis"
            )
        # RAG-enhanced recommendations
        if "competitive" in rag_analysis.lower():
            recommendations.append(
                "Historical data suggests competitive market - pricing strategy should emphasize value proposition"
            )
        if "premium" in rag_analysis.lower():
            recommendations.append(
                "Market analysis indicates potential for premium pricing based on quality differentiation"
            )
        return recommendations

    def _calculate_confidence_enhancement(
        self,
        base_confidence: float,
        documents_retrieved: int,
        competitive_intelligence: dict[str, Any],
    ) -> float:
        """Calculate confidence enhancement from RAG analysis"""
        enhancement_factors = []
        # Document quantity enhancement
        if documents_retrieved >= 5:
            enhancement_factors.append(0.2)  # 20% boost for good data
        elif documents_retrieved >= 3:
            enhancement_factors.append(0.1)  # 10% boost for moderate data
        else:
            enhancement_factors.append(-0.1)  # 10% reduction for limited data
        # Market saturation enhancement
        market_saturation = competitive_intelligence.get("market_saturation", "unknown")
        if market_saturation == "high":
            enhancement_factors.append(0.15)  # More data points available
        elif market_saturation == "medium":
            enhancement_factors.append(0.05)
        # Positioning clarity enhancement
        positioning = competitive_intelligence.get("market_positioning", "unknown")
        if positioning != "unknown":
            enhancement_factors.append(0.1)  # Clear positioning understanding
        total_enhancement = sum(enhancement_factors)
        enhanced_confidence = min(1.0, base_confidence + total_enhancement)
        return enhanced_confidence - base_confidence

    def compare_pricing_strategies(
        self, category: str, description: str, **params
    ) -> dict[str, EnhancedPricingResult]:
        """Compare different pricing strategies with RAG enhancement"""
        strategies = [
            PricingStrategy.COST_PLUS,
            PricingStrategy.MARKET_BASED,
            PricingStrategy.COMPETITIVE,
            PricingStrategy.HYBRID,
        ]
        strategy_comparison = {}
        for strategy in strategies:
            try:
                result = self.analyze_enhanced_pricing(
                    category=category,
                    description=description,
                    strategy=strategy,
                    **params,
                )
                strategy_comparison[strategy.value] = result
            except Exception as e:
                self.logger.error(f"Strategy {strategy.value} failed: {str(e)}")
        return strategy_comparison

    def get_system_status(self) -> dict[str, Any]:
        """Get comprehensive system status"""
        # PricingEngine doesn't have get_pricing_summary, provide basic status
        pricing_summary = {
            "engine_status": "operational",
            "historical_data_loaded": (
                len(self.pricing_engine.historical_data) > 0
                if hasattr(self.pricing_engine, "historical_data")
                else False
            ),
        }
        rag_status = self.rag_integrator.get_system_status()
        return {
            "pricing_engine": pricing_summary,
            "rag_integration": rag_status,
            "integration_ready": pricing_summary["engine_status"] == "operational"
            and rag_status.get("integration_ready", False),
            "enhanced_capabilities": {
                "market_intelligence": True,
                "competitive_analysis": True,
                "historical_context": True,
                "confidence_enhancement": True,
                "strategy_comparison": True,
            },
        }


def create_rag_pricing_integrator() -> RAGPricingIntegrator:
    """Factory function to create RAG-Pricing integrator"""
    return RAGPricingIntegrator()


# Example usage and testing
if __name__ == "__main__":
    print("=== RAG-Enhanced Pricing Integration Test ===")
    try:
        # Create integrator
        integrator = create_rag_pricing_integrator()
        print("✓ RAG-Pricing Integrator created")
        # Get system status
        status = integrator.get_system_status()
        print(f"✓ Integration Ready: {status['integration_ready']}")
        print(
            f"✓ Enhanced Capabilities: {list(status['enhanced_capabilities'].keys())}"
        )
        # Test enhanced pricing analysis
        print("\n--- Testing Enhanced Bottled Water Pricing ---")
        enhanced_result = integrator.analyze_enhanced_pricing(
            category="bottled_water",
            description="Supply bottled water to federal agencies with monthly delivery",
            quantity=1000,
            duration_months=12,
            location="urban",
            strategy=PricingStrategy.HYBRID,
        )
        print(
            f"✓ Enhanced Price: ${enhanced_result.pricing_result.recommended_price:,.2f}"
        )
        print(
            f"✓ Base Confidence: {enhanced_result.pricing_result.confidence_score:.2f}"
        )
        print(
            f"✓ Confidence Enhancement: +{enhanced_result.confidence_enhancement:.2f}"
        )
        print(f"✓ Documents Analyzed: {enhanced_result.documents_analyzed}")
        print(f"✓ Market Insights: {len(enhanced_result.market_insights)}")
        print(f"✓ Recommendations: {len(enhanced_result.pricing_recommendations)}")
        # Test strategy comparison
        print("\n--- Testing Strategy Comparison ---")
        comparison = integrator.compare_pricing_strategies(
            category="construction",
            description="Office building renovation project",
            quantity=25000,
            duration_months=18,
        )
        print(f"✓ Strategies Compared: {len(comparison)}")
        for strategy, result in comparison.items():
            price = result.pricing_result.recommended_price
            margin = result.pricing_result.margin_achieved
            print(f"  {strategy}: ${price:,.0f} ({margin:.1%} margin)")
        print("\n✅ RAG-Enhanced Pricing Integration test completed successfully!")
    except Exception as e:
        print(f"❌ RAG-Enhanced Pricing Integration test failed: {str(e)}")
        import traceback

        traceback.print_exc()
