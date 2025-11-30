"""
Comprehensive test suite for AI Pricing Engine
"""
import os
import sys
import time

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from pricing.pricing_engine import (
    PricingStrategy,
    calculate_bid_price,
    create_pricing_engine,
    validate_pricing_compliance,
)


def test_engine_initialization():
    """Test pricing engine initialization"""
    print("=" * 60)
    print("Testing Pricing Engine Initialization")
    print("=" * 60)
    try:
        engine = create_pricing_engine()
        print("✓ Pricing engine created successfully")
        stats = engine.get_pricing_statistics()
        print(f"✓ Engine status: {stats['engine_status']}")
        print(f"✓ Cost baselines loaded: {stats['cost_baselines_loaded']}")
        print(f"✓ Categories supported: {stats['categories_supported']}")
        print(f"✓ Historical data available: {stats['historical_data_available']}")
        return True
    except Exception as e:
        print(f"✗ Engine initialization failed: {e}")
        return False
def test_cost_baselines():
    """Test cost baseline functionality"""
    print("\n" + "=" * 60)
    print("Testing Cost Baselines")
    print("=" * 60)
    try:
        engine = create_pricing_engine()
        # Test each category
        categories = ['bottled_water', 'construction', 'delivery', 'general']
        for category in categories:
            if category in engine.cost_baselines:
                baseline = engine.cost_baselines[category]
                print(f"✓ {category}: ${baseline.base_cost}/_{baseline.unit_type} ({baseline.unit_description})")
            else:
                print(f"✗ Missing baseline for {category}")
                return False
        # Test cost calculation
        base_cost, breakdown = engine.calculate_cost_plus_price(
            category='bottled_water',
            quantity=500,
            duration_months=12,
            complexity_factor=1.0
        )
        print(f"✓ Cost calculation test: ${base_cost:,.2f}")
        print(f"✓ Cost breakdown: {breakdown}")
        return True
    except Exception as e:
        print(f"✗ Cost baselines test failed: {e}")
        return False
def test_historical_data_integration():
    """Test historical data loading and analysis"""
    print("\n" + "=" * 60)
    print("Testing Historical Data Integration")
    print("=" * 60)
    try:
        engine = create_pricing_engine()
        if engine.historical_data is not None:
            print(f"✓ Historical data loaded: {len(engine.historical_data)} records")
            # Test statistics for each category
            categories = ['bottled_water', 'construction', 'delivery']
            for category in categories:
                stats = engine._get_historical_statistics(category)
                if stats:
                    print(f"✓ {category} statistics: {stats['count']} contracts, avg ${stats['mean']:,.0f}")
                else:
                    print(f"⚠ No historical data for {category}")
        else:
            print("⚠ No historical data available - engine will use baselines only")
        return True
    except Exception as e:
        print(f"✗ Historical data test failed: {e}")
        return False
def test_pricing_strategies():
    """Test different pricing strategies"""
    print("\n" + "=" * 60)
    print("Testing Pricing Strategies")
    print("=" * 60)
    try:
        engine = create_pricing_engine()
        test_rfp = "Monthly delivery of 200 cases of bottled water to government offices"
        strategies = [
            PricingStrategy.COST_PLUS,
            PricingStrategy.MARKET_BASED,
            PricingStrategy.HYBRID,
            PricingStrategy.COMPETITIVE
        ]
        results = {}
        for strategy in strategies:
            result = engine.generate_pricing(
                rfp_description=test_rfp,
                category='bottled_water',
                strategy=strategy
            )
            results[strategy.value] = {
                'price': result.recommended_price,
                'margin': result.margin_percentage,
                'compliant': result.margin_compliance,
                'confidence': result.confidence_score
            }
            print(f"✓ {strategy.value}: ${result.recommended_price:,.2f} ({result.margin_percentage:.1%} margin)")
        # All strategies should produce valid results
        if all(r['price'] > 0 for r in results.values()):
            print("✓ All pricing strategies functional")
            return True
        else:
            print("✗ Some strategies failed to generate valid prices")
            return False
    except Exception as e:
        print(f"✗ Pricing strategies test failed: {e}")
        return False
def test_margin_compliance():
    """Test margin compliance validation"""
    print("\n" + "=" * 60)
    print("Testing Margin Compliance")
    print("=" * 60)
    try:
        engine = create_pricing_engine()
        # Test different margin scenarios
        test_cases = [
            {
                "description": "Standard bottled water delivery",
                "category": "bottled_water",
                "target_margin": 0.40,
                "expected_compliance": True
            },
            {
                "description": "Low-margin competitive bid",
                "category": "delivery",
                "target_margin": 0.15,
                "expected_compliance": True
            },
            {
                "description": "High-margin premium service",
                "category": "construction",
                "target_margin": 0.50,
                "expected_compliance": True
            }
        ]
        pricing_results = []
        for test_case in test_cases:
            result = engine.generate_pricing(
                rfp_description=test_case['description'],
                category=test_case['category'],
                target_margin=test_case['target_margin']
            )
            pricing_results.append(result)
            compliance_status = "✓" if result.margin_compliance else "✗"
            print(f"{compliance_status} {test_case['category']}: {result.margin_percentage:.1%} margin")
        # Validate overall compliance
        validation = engine.validate_margin_compliance(pricing_results)
        compliance_rate = validation['compliance_rate']
        print(f"\nOverall compliance rate: {compliance_rate:.1%}")
        print(f"Target compliance rate: {validation['target_rate']:.1%}")
        if validation['passes_requirement']:
            print("✓ Margin compliance requirement met")
            return True
        else:
            print("⚠ Margin compliance below target")
            return False
    except Exception as e:
        print(f"✗ Margin compliance test failed: {e}")
        return False
def test_category_detection():
    """Test automatic category detection"""
    print("\n" + "=" * 60)
    print("Testing Category Detection")
    print("=" * 60)
    try:
        engine = create_pricing_engine()
        test_descriptions = [
            ("Monthly delivery of 500 cases of bottled water", "bottled_water"),
            ("Construction of new office building", "construction"),
            ("Delivery and logistics services for medical supplies", "delivery"),
            ("General consulting services", "general")
        ]
        all_correct = True
        for description, expected_category in test_descriptions:
            detected = engine._detect_category_from_description(description)
            if detected == expected_category:
                print(f"✓ '{description[:40]}...' → {detected}")
            else:
                print(f"✗ '{description[:40]}...' → {detected} (expected {expected_category})")
                all_correct = False
        return all_correct
    except Exception as e:
        print(f"✗ Category detection test failed: {e}")
        return False
def test_pricing_performance():
    """Test pricing calculation performance"""
    print("\n" + "=" * 60)
    print("Testing Pricing Performance")
    print("=" * 60)
    try:
        engine = create_pricing_engine()
        test_descriptions = [
            "Bottled water delivery services",
            "Construction project management",
            "Medical supply delivery",
            "Office building maintenance",
            "Food service delivery"
        ]
        total_time = 0
        successful_calculations = 0
        for description in test_descriptions:
            start_time = time.time()
            try:
                _result = engine.generate_pricing(rfp_description=description)
                calc_time = time.time() - start_time
                total_time += calc_time
                successful_calculations += 1
                print(f"✓ '{description[:30]}...' - {calc_time:.3f}s")
            except Exception as e:
                print(f"✗ '{description[:30]}...' - Failed: {e}")
        if successful_calculations > 0:
            avg_time = total_time / successful_calculations
            print(f"\nAverage calculation time: {avg_time:.3f} seconds")
            # Performance requirement: should be fast for real-time use
            if avg_time < 2.0:
                print("✓ Performance meets requirement (<2s per calculation)")
                return True
            else:
                print("⚠ Performance slower than ideal")
                return False
        else:
            print("✗ No successful calculations")
            return False
    except Exception as e:
        print(f"✗ Performance test failed: {e}")
        return False
def test_rag_integration():
    """Test RAG engine integration for pricing context"""
    print("\n" + "=" * 60)
    print("Testing RAG Integration")
    print("=" * 60)
    try:
        engine = create_pricing_engine()
        # Test RAG loading
        engine._load_rag_engine()
        if engine.rag_engine:
            print("✓ RAG engine loaded successfully")
            # Test context retrieval
            context = engine._get_pricing_context(
                "Bottled water delivery for city offices",
                "bottled_water"
            )
            print(f"✓ Pricing context retrieved: {len(context['similar_rfps'])} similar RFPs")
            return True
        else:
            print("⚠ RAG engine not available - pricing will use baselines only")
            return True  # This is acceptable fallback behavior
    except Exception as e:
        print(f"✗ RAG integration test failed: {e}")
        return False
def test_convenience_functions():
    """Test convenience functions"""
    print("\n" + "=" * 60)
    print("Testing Convenience Functions")
    print("=" * 60)
    try:
        # Test calculate_bid_price function
        result = calculate_bid_price(
            rfp_description="Monthly bottled water delivery service",
            category="bottled_water",
            strategy=PricingStrategy.HYBRID
        )
        print(f"✓ calculate_bid_price: ${result.recommended_price:,.2f}")
        print(f"✓ Margin: {result.margin_percentage:.1%}")
        print(f"✓ Compliance: {result.margin_compliance}")
        # Test validation function
        test_results = [result]
        compliance = validate_pricing_compliance(test_results)
        print(f"✓ validate_pricing_compliance: {compliance}")
        return True
    except Exception as e:
        print(f"✗ Convenience functions test failed: {e}")
        return False
def run_comprehensive_test():
    """Run all pricing engine tests"""
    print("AI Pricing Engine Comprehensive Test Suite")
    print("=" * 80)
    tests = [
        ("Engine Initialization", test_engine_initialization),
        ("Cost Baselines", test_cost_baselines),
        ("Historical Data Integration", test_historical_data_integration),
        ("Pricing Strategies", test_pricing_strategies),
        ("Margin Compliance", test_margin_compliance),
        ("Category Detection", test_category_detection),
        ("Pricing Performance", test_pricing_performance),
        ("RAG Integration", test_rag_integration),
        ("Convenience Functions", test_convenience_functions)
    ]
    results = {}
    for test_name, test_func in tests:
        try:
            print(f"\n{'=' * 20} {test_name} {'=' * 20}")
            results[test_name] = test_func()
        except Exception as e:
            print(f"Test {test_name} failed with exception: {e}")
            results[test_name] = False
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    passed = sum(results.values())
    total = len(results)
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {test_name}")
    print(f"\nOverall: {passed}/{total} tests passed")
    if passed == total:
        print("🎉 All tests passed! Pricing engine is ready for production.")
    else:
        print("⚠️  Some tests failed. Review implementation and dependencies.")
    return passed == total
if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
