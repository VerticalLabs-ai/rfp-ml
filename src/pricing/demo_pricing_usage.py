"""
Demonstration of AI Pricing Engine usage for bid generation
"""
import os
import sys

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from pricing.pricing_engine import PricingStrategy, calculate_bid_price, create_pricing_engine


def demo_basic_pricing():
    """Demonstrate basic pricing functionality"""
    print("=" * 70)
    print("DEMO: Basic Pricing Functionality")
    print("=" * 70)
    sample_rfps = [
        {
            "title": "City Parks Water Supply",
            "description": "Monthly delivery of 300 cases of bottled water to 8 city parks for public consumption",
            "category": "bottled_water"
        },
        {
            "title": "School Building Renovation",
            "description": "Renovation of 20,000 sq ft elementary school including HVAC, electrical, and interior work",
            "category": "construction"
        },
        {
            "title": "Hospital Supply Delivery",
            "description": "Daily delivery of medical supplies and equipment to 3 regional hospitals",
            "category": "delivery"
        }
    ]
    for rfp in sample_rfps:
        print(f"\nRFP: {rfp['title']}")
        print(f"Description: {rfp['description']}")
        print("-" * 50)
        try:
            result = calculate_bid_price(
                rfp_description=rfp['description'],
                category=rfp['category'],
                strategy=PricingStrategy.HYBRID
            )
            print(f"Category: {result.category}")
            print(f"Base Cost: ${result.base_cost:,.2f}")
            print(f"Recommended Price: ${result.recommended_price:,.2f}")
            print(f"Margin: {result.margin_percentage:.1%}")
            print(f"Compliance: {'✓' if result.margin_compliance else '✗'}")
            print(f"Risk Level: {result.risk_level.value}")
            print(f"Confidence: {result.confidence_score:.2f}")
            print(f"Strategy: {result.strategy_used.value}")
            print(f"Justification: {result.justification}")
        except Exception as e:
            print(f"Pricing failed: {e}")
def demo_strategy_comparison():
    """Demonstrate different pricing strategies"""
    print("\n" + "=" * 70)
    print("DEMO: Pricing Strategy Comparison")
    print("=" * 70)
    test_rfp = "Monthly delivery of 500 cases of spring water to government office buildings"
    strategies = [
        (PricingStrategy.COST_PLUS, "Cost-Plus (Standard)"),
        (PricingStrategy.MARKET_BASED, "Market-Based (Competitive)"),
        (PricingStrategy.HYBRID, "Hybrid (Balanced)"),
        (PricingStrategy.COMPETITIVE, "Competitive (Aggressive)")
    ]
    print(f"RFP: {test_rfp}")
    print("-" * 70)
    engine = create_pricing_engine()
    results = []
    for strategy, description in strategies:
        try:
            result = engine.generate_pricing(
                rfp_description=test_rfp,
                category="bottled_water",
                strategy=strategy
            )
            results.append((description, result))
            print(f"\n{description}:")
            print(f"  Price: ${result.recommended_price:,.2f}")
            print(f"  Margin: {result.margin_percentage:.1%}")
            print(f"  Risk: {result.risk_level.value}")
            print(f"  Confidence: {result.confidence_score:.2f}")
        except Exception as e:
            print(f"\n{description}: Failed - {e}")
    # Analysis
    if results:
        prices = [r[1].recommended_price for r in results]
        print(f"\nPrice Range: ${min(prices):,.2f} - ${max(prices):,.2f}")
        print(f"Price Spread: {((max(prices) - min(prices)) / min(prices)) * 100:.1f}%")
def demo_margin_compliance():
    """Demonstrate margin compliance validation"""
    print("\n" + "=" * 70)
    print("DEMO: Margin Compliance Validation")
    print("=" * 70)
    test_scenarios = [
        {
            "description": "Low-risk standard water delivery",
            "target_margin": 0.40,
            "expected": "compliant"
        },
        {
            "description": "Competitive construction bid",
            "target_margin": 0.20,
            "expected": "compliant"
        },
        {
            "description": "Minimum margin delivery service",
            "target_margin": 0.15,
            "expected": "compliant"
        },
        {
            "description": "High-margin premium service",
            "target_margin": 0.45,
            "expected": "compliant"
        }
    ]
    engine = create_pricing_engine()
    pricing_results = []
    for scenario in test_scenarios:
        try:
            result = engine.generate_pricing(
                rfp_description=scenario['description'],
                target_margin=scenario['target_margin']
            )
            pricing_results.append(result)
            status = "✓" if result.margin_compliance else "✗"
            print(f"{status} {scenario['description'][:40]}...")
            print(f"   Target: {scenario['target_margin']:.1%}, Actual: {result.margin_percentage:.1%}")
            print(f"   Risk: {result.risk_level.value}")
        except Exception as e:
            print(f"✗ Scenario failed: {e}")
    # Overall compliance validation
    if pricing_results:
        validation = engine.validate_margin_compliance(pricing_results)
        print("\nCompliance Summary:")
        print(f"  Total bids: {validation['total_bids']}")
        print(f"  Compliant bids: {validation['compliant_bids']}")
        print(f"  Compliance rate: {validation['compliance_rate']:.1%}")
        print(f"  Target rate: {validation['target_rate']:.1%}")
        print(f"  Requirement met: {'✓' if validation['passes_requirement'] else '✗'}")
def demo_competitive_analysis():
    """Demonstrate competitive analysis features"""
    print("\n" + "=" * 70)
    print("DEMO: Competitive Analysis")
    print("=" * 70)
    analysis_cases = [
        {
            "description": "Large volume water delivery contract",
            "category": "bottled_water"
        },
        {
            "description": "Multi-phase construction project",
            "category": "construction"
        },
        {
            "description": "Regional delivery network services",
            "category": "delivery"
        }
    ]
    engine = create_pricing_engine()
    for case in analysis_cases:
        print(f"\nAnalyzing: {case['description']}")
        print("-" * 40)
        try:
            result = engine.generate_pricing(
                rfp_description=case['description'],
                category=case['category']
            )
            analysis = result.competitive_analysis
            print(f"Recommended Price: ${result.recommended_price:,.2f}")
            print(f"Market Position: {analysis.get('market_position', 'unknown')}")
            if analysis.get('price_percentile'):
                percentile = analysis['price_percentile'] * 100
                print(f"Price Percentile: {percentile:.0f}%")
            if analysis.get('competitive_advantage'):
                print(f"Advantages: {', '.join(analysis['competitive_advantage'])}")
            if analysis.get('risk_factors'):
                print(f"Risk Factors: {', '.join(analysis['risk_factors'])}")
            # Cost breakdown
            breakdown = result.cost_breakdown
            print("Cost Structure:")
            for component, value in breakdown.items():
                if component != 'total':
                    pct = (value / breakdown['total']) * 100
                    print(f"  {component.title()}: ${value:,.2f} ({pct:.1f}%)")
        except Exception as e:
            print(f"Analysis failed: {e}")
def demo_integration_with_rag():
    """Demonstrate integration with RAG engine for pricing context"""
    print("\n" + "=" * 70)
    print("DEMO: RAG Integration for Pricing Context")
    print("=" * 70)
    engine = create_pricing_engine()
    # Load RAG engine if available
    engine._load_rag_engine()
    if engine.rag_engine:
        print("RAG engine available - using contextual pricing")
        test_rfp = "Quarterly delivery of bottled water to government facilities"
        # Get pricing context
        context = engine._get_pricing_context(test_rfp, "bottled_water")
        print(f"\nRFP: {test_rfp}")
        print(f"Similar RFPs found: {len(context['similar_rfps'])}")
        if context['similar_rfps']:
            print("\nSimilar contracts for context:")
            for i, rfp in enumerate(context['similar_rfps'][:3], 1):
                print(f"  {i}. Score: {rfp['score']:.3f}")
                print(f"     Agency: {rfp.get('agency', 'Unknown')}")
                print(f"     Value: ${rfp.get('contract_value', 0):,.2f}")
                print(f"     Content: {rfp['content'][:80]}...")
        # Generate pricing with RAG context
        result = engine.generate_pricing(rfp_description=test_rfp)
        print("\nContextual Pricing Result:")
        print(f"  Price: ${result.recommended_price:,.2f}")
        print(f"  Margin: {result.margin_percentage:.1%}")
        print(f"  Confidence: {result.confidence_score:.2f}")
        print(f"  Justification: {result.justification}")
    else:
        print("RAG engine not available - using baseline pricing only")
        result = engine.generate_pricing(
            rfp_description="Quarterly delivery of bottled water to government facilities"
        )
        print("Baseline Pricing Result:")
        print(f"  Price: ${result.recommended_price:,.2f}")
        print(f"  Margin: {result.margin_percentage:.1%}")
def demo_engine_statistics():
    """Show pricing engine capabilities and statistics"""
    print("\n" + "=" * 70)
    print("DEMO: Pricing Engine Statistics")
    print("=" * 70)
    engine = create_pricing_engine()
    stats = engine.get_pricing_statistics()
    print("Engine Configuration:")
    print(f"  Status: {stats['engine_status']}")
    print(f"  Cost baselines: {stats['cost_baselines_loaded']}")
    print(f"  Categories: {', '.join(stats['categories_supported'])}")
    print(f"  Historical data: {stats['historical_data_available']}")
    print("\nMargin Configuration:")
    margin_config = stats['margin_configuration']
    print(f"  Default margin: {margin_config['default_margin']:.1%}")
    print(f"  Minimum margin: {margin_config['min_margin']:.1%}")
    print(f"  Maximum margin: {margin_config['max_margin']:.1%}")
    print(f"\nStrategies Available: {', '.join(stats['strategies_available'])}")
    if 'historical_records' in stats:
        print("\nHistorical Data:")
        print(f"  Total records: {stats['historical_records']:,}")
        if 'category_distribution' in stats:
            print("  Category distribution:")
            for category, count in stats['category_distribution'].items():
                print(f"    {category}: {count:,} contracts")
if __name__ == "__main__":
    print("AI Pricing Engine Usage Demonstration")
    print("=" * 80)
    try:
        # Show engine statistics first
        demo_engine_statistics()
        # Run demonstrations
        demo_basic_pricing()
        demo_strategy_comparison()
        demo_margin_compliance()
        demo_competitive_analysis()
        demo_integration_with_rag()
        print("\n" + "=" * 80)
        print("Pricing Engine demonstration completed successfully!")
        print("The system can now generate competitive, compliant pricing for bids.")
        print("=" * 80)
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
