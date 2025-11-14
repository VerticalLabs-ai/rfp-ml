import sys
import os
sys.path.append('/app/government_rfp_bid_1927/src')
from pricing.pricing_engine import PricingEngine, PricingStrategy
def test_pricing_examples():
    """Test pricing engine with practical examples"""
    print("=== PRICING ENGINE PRACTICAL EXAMPLES ===\n")
    engine = PricingEngine()
    # Example 1: Bottled Water Service
    print("Example 1: Office Bottled Water Service")
    print("Requirements: 50 cases/month, 12-month contract, 20-mile delivery")
    water_requirements = {
        'cases_per_month': 50,
        'contract_months': 12,
        'delivery_distance_miles': 20,
        'competitiveness': 'medium'
    }
    water_result = engine.generate_pricing('bottled_water', water_requirements, PricingStrategy.HYBRID)
    print(f"  Final Price: ${water_result.final_price:,.2f}")
    print(f"  Base Cost: ${water_result.base_price:,.2f}")
    print(f"  Margin: {water_result.margin_percentage:.1%}")
    print(f"  Strategy: {water_result.pricing_strategy}")
    print(f"  Confidence: {water_result.confidence_score:.2f}")
    print(f"  Margin Compliant: {water_result.margin_compliant}")
    print(f"  Justification: {water_result.justification[:150]}...")
    # Example 2: Construction Project
    print(f"\nExample 2: Government Building Renovation")
    print("Requirements: 8,000 sq ft, 8-month duration, standard complexity")
    construction_requirements = {
        'square_footage': 8000,
        'duration_months': 8,
        'complexity_factor': 1.0,
        'competitiveness': 'high'
    }
    construction_result = engine.generate_pricing('construction', construction_requirements, PricingStrategy.HYBRID)
    print(f"  Final Price: ${construction_result.final_price:,.2f}")
    print(f"  Base Cost: ${construction_result.base_price:,.2f}")
    print(f"  Margin: {construction_result.margin_percentage:.1%}")
    print(f"  Strategy: {construction_result.pricing_strategy}")
    print(f"  Confidence: {construction_result.confidence_score:.2f}")
    print(f"  Margin Compliant: {construction_result.margin_compliant}")
    print(f"  Justification: {construction_result.justification[:150]}...")
    # Example 3: Delivery Service
    print(f"\nExample 3: Government Courier Service")
    print("Requirements: 120 deliveries/month, 24-month contract, 15-mile average")
    delivery_requirements = {
        'deliveries_per_month': 120,
        'contract_months': 24,
        'average_distance_miles': 15,
        'competitiveness': 'medium'
    }
    delivery_result = engine.generate_pricing('delivery', delivery_requirements, PricingStrategy.HYBRID)
    print(f"  Final Price: ${delivery_result.final_price:,.2f}")
    print(f"  Base Cost: ${delivery_result.base_price:,.2f}")
    print(f"  Margin: {delivery_result.margin_percentage:.1%}")
    print(f"  Strategy: {delivery_result.pricing_strategy}")
    print(f"  Confidence: {delivery_result.confidence_score:.2f}")
    print(f"  Margin Compliant: {delivery_result.margin_compliant}")
    print(f"  Justification: {delivery_result.justification[:150]}...")
    # Test margin compliance
    print(f"\n=== MARGIN COMPLIANCE TEST ===")
    results = [water_result, construction_result, delivery_result]
    compliance = engine.validate_margin_compliance(results)
    print(f"Overall Compliance Rate: {compliance['compliance_rate']:.1%}")
    print(f"Average Margin: {compliance['margin_statistics']['avg_margin']:.1%}")
    print(f"Meets Target (>90%): {compliance['meets_target']}")
    # Test different strategies for same project
    print(f"\n=== STRATEGY COMPARISON ===")
    print("Comparing all strategies for construction project:")
    for strategy in [PricingStrategy.COST_PLUS, PricingStrategy.MARKET_BASED, PricingStrategy.HYBRID]:
        result = engine.generate_pricing('construction', construction_requirements, strategy)
        print(f"  {strategy.value}: ${result.final_price:,.0f} "
              f"(margin: {result.margin_percentage:.0%}, conf: {result.confidence_score:.2f})")
    print(f"\n=== TEST COMPLETE ===")
    return True
if __name__ == "__main__":
    test_pricing_examples()