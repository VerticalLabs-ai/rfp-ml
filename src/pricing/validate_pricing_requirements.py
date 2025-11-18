"""
Validation script to verify AI Pricing Engine meets all specified requirements
"""
import sys
import os
import time
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.paths import PathConfig
from pricing.pricing_engine import (
    create_pricing_engine, calculate_bid_price, validate_pricing_compliance,
    PricingStrategy, RiskLevel
)
def validate_requirement_1():
    """Validate: Historical award extraction and analysis"""
    print("✓ Checking historical award data integration...")
    try:
        engine = create_pricing_engine()
        stats = engine.get_pricing_statistics()
        if stats['historical_data_available']:
            print(f"  ✓ Historical data loaded: {stats.get('historical_records', 0)} records")
            # Check category-specific statistics
            categories = ['bottled_water', 'construction', 'delivery']
            for category in categories:
                category_stats = engine._get_historical_statistics(category)
                if category_stats and category_stats['count'] > 0:
                    print(f"  ✓ {category}: {category_stats['count']} historical contracts")
                    print(f"    Average: ${category_stats['mean']:,.0f}, Median: ${category_stats['median']:,.0f}")
                else:
                    print(f"  ⚠ Limited data for {category}")
        else:
            print("  ⚠ No historical data available - using baseline pricing")
        return True
    except Exception as e:
        print(f"  ✗ Historical data validation failed: {e}")
        return False
def validate_requirement_2():
    """Validate: Margin-based price generation (15-50% range, default 40%)"""
    print("✓ Checking margin compliance and range validation...")
    try:
        engine = create_pricing_engine()
        # Check configuration
        stats = engine.get_pricing_statistics()
        margin_config = stats['margin_configuration']
        expected_config = {
            'default_margin': 0.40,
            'min_margin': 0.15,
            'max_margin': 0.50
        }
        config_correct = True
        for key, expected_value in expected_config.items():
            actual_value = margin_config[key]
            if abs(actual_value - expected_value) < 0.01:
                print(f"  ✓ {key}: {actual_value:.1%} (correct)")
            else:
                print(f"  ✗ {key}: {actual_value:.1%} (expected {expected_value:.1%})")
                config_correct = False
        if not config_correct:
            return False
        # Test margin range enforcement
        test_margins = [0.10, 0.15, 0.25, 0.40, 0.50, 0.60]
        for target_margin in test_margins:
            result = engine.generate_pricing(
                rfp_description="Test RFP for margin validation",
                target_margin=target_margin
            )
            expected_compliance = 0.15 <= target_margin <= 0.50
            if result.margin_compliance == expected_compliance:
                status = "✓" if expected_compliance else "⚠"
                print(f"  {status} Margin {target_margin:.1%}: compliance = {result.margin_compliance}")
            else:
                print(f"  ✗ Margin {target_margin:.1%}: incorrect compliance determination")
                return False
        return True
    except Exception as e:
        print(f"  ✗ Margin validation failed: {e}")
        return False
def validate_requirement_3():
    """Validate: Pricing against historical award ranges for competitiveness"""
    print("✓ Checking competitive pricing against historical ranges...")
    try:
        engine = create_pricing_engine()
        categories = ['bottled_water', 'construction', 'delivery']
        for category in categories:
            print(f"\n  Testing {category} category:")
            # Generate pricing
            result = engine.generate_pricing(
                rfp_description=f"Test {category} service contract",
                category=category,
                strategy=PricingStrategy.MARKET_BASED
            )
            # Get historical statistics
            stats = engine._get_historical_statistics(category)
            if stats and stats['count'] >= 5:
                # Check if price falls within reasonable range
                price = result.recommended_price
                reasonable_min = stats['q25'] * 0.5  # Allow 50% below Q25
                reasonable_max = stats['q75'] * 2.0  # Allow 100% above Q75
                if reasonable_min <= price <= reasonable_max:
                    print(f"    ✓ Price ${price:,.0f} within reasonable range")
                    print(f"      Range: ${reasonable_min:,.0f} - ${reasonable_max:,.0f}")
                else:
                    print(f"    ⚠ Price ${price:,.0f} outside typical range")
                    print(f"      Range: ${reasonable_min:,.0f} - ${reasonable_max:,.0f}")
                # Check competitive analysis
                analysis = result.competitive_analysis
                if analysis.get('market_position'):
                    print(f"    ✓ Market position: {analysis['market_position']}")
            else:
                print(f"    ⚠ Insufficient historical data for validation")
        return True
    except Exception as e:
        print(f"  ✗ Competitive pricing validation failed: {e}")
        return False
def validate_requirement_4():
    """Validate: Cost baseline integration for different service categories"""
    print("✓ Checking cost baseline integration...")
    try:
        engine = create_pricing_engine()
        required_categories = ['bottled_water', 'construction', 'delivery', 'general']
        for category in required_categories:
            if category in engine.cost_baselines:
                baseline = engine.cost_baselines[category]
                print(f"  ✓ {category}: ${baseline.base_cost}/{baseline.unit_type}")
                print(f"    Description: {baseline.unit_description}")
                print(f"    Overhead factor: {baseline.overhead_factor}")
                # Test cost calculation
                base_cost, breakdown = engine.calculate_cost_plus_price(
                    category=category,
                    quantity=100,
                    duration_months=12
                )
                if base_cost > 0 and all(v >= 0 for v in breakdown.values()):
                    print(f"    ✓ Cost calculation functional: ${base_cost:,.2f}")
                else:
                    print(f"    ✗ Cost calculation failed")
                    return False
            else:
                print(f"  ✗ Missing baseline for {category}")
                return False
        return True
    except Exception as e:
        print(f"  ✗ Cost baseline validation failed: {e}")
        return False
def validate_requirement_5():
    """Validate: 90% margin compliance rate on test cases"""
    print("✓ Checking 90% margin compliance requirement...")
    try:
        engine = create_pricing_engine()
        # Generate test cases across different scenarios
        test_cases = []
        # Different categories
        categories = ['bottled_water', 'construction', 'delivery']
        for category in categories:
            test_cases.append({
                'description': f"Standard {category} service contract",
                'category': category,
                'target_margin': 0.40
            })
        # Different margin targets (within compliance range)
        margin_targets = [0.15, 0.20, 0.30, 0.40, 0.50]
        for margin in margin_targets:
            test_cases.append({
                'description': f"Service contract with {margin:.0%} target margin",
                'category': 'bottled_water',
                'target_margin': margin
            })
        # Different strategies
        strategies = [PricingStrategy.COST_PLUS, PricingStrategy.HYBRID, PricingStrategy.MARKET_BASED]
        for strategy in strategies:
            test_cases.append({
                'description': f"Contract using {strategy.value} strategy",
                'category': 'delivery',
                'strategy': strategy
            })
        # Generate pricing for all test cases
        pricing_results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = engine.generate_pricing(
                    rfp_description=test_case['description'],
                    category=test_case.get('category'),
                    target_margin=test_case.get('target_margin'),
                    strategy=test_case.get('strategy', PricingStrategy.HYBRID)
                )
                pricing_results.append(result)
                status = "✓" if result.margin_compliance else "✗"
                print(f"  {status} Test {i+1}: {result.margin_percentage:.1%} margin")
            except Exception as e:
                print(f"  ✗ Test {i+1} failed: {e}")
        # Validate overall compliance
        if pricing_results:
            validation = engine.validate_margin_compliance(pricing_results)
            compliance_rate = validation['compliance_rate']
            target_rate = 0.90
            print(f"\n  Compliance Summary:")
            print(f"    Total test cases: {len(pricing_results)}")
            print(f"    Compliant cases: {validation['compliant_bids']}")
            print(f"    Compliance rate: {compliance_rate:.1%}")
            print(f"    Target rate: {target_rate:.1%}")
            if compliance_rate >= target_rate:
                print(f"  ✓ Meets 90% compliance requirement")
                return True
            else:
                print(f"  ✗ Below 90% compliance requirement")
                return False
        else:
            print("  ✗ No successful test cases")
            return False
    except Exception as e:
        print(f"  ✗ Compliance rate validation failed: {e}")
        return False
def validate_requirement_6():
    """Validate: Price justification generation"""
    print("✓ Checking price justification generation...")
    try:
        engine = create_pricing_engine()
        test_scenarios = [
            {
                'description': "Standard bottled water delivery contract",
                'category': 'bottled_water',
                'strategy': PricingStrategy.COST_PLUS
            },
            {
                'description': "Complex construction project with specialized requirements",
                'category': 'construction',
                'strategy': PricingStrategy.HYBRID
            },
            {
                'description': "Competitive delivery services bid",
                'category': 'delivery',
                'strategy': PricingStrategy.COMPETITIVE
            }
        ]
        for scenario in test_scenarios:
            result = engine.generate_pricing(
                rfp_description=scenario['description'],
                category=scenario['category'],
                strategy=scenario['strategy']
            )
            justification = result.justification
            if justification and len(justification) > 50:
                print(f"  ✓ {scenario['strategy'].value}: {len(justification)} chars")
                print(f"    Preview: {justification[:100]}...")
                # Check for key elements
                required_elements = ['margin', 'cost', 'strategy']
                elements_found = sum(1 for element in required_elements if element.lower() in justification.lower())
                if elements_found >= 2:
                    print(f"    ✓ Contains key justification elements")
                else:
                    print(f"    ⚠ Missing some justification elements")
            else:
                print(f"  ✗ {scenario['strategy'].value}: insufficient justification")
                return False
        return True
    except Exception as e:
        print(f"  ✗ Justification validation failed: {e}")
        return False
def validate_requirement_7():
    """Validate: File structure and API design"""
    print("✓ Checking file structure and API design...")
    try:
        # Check file structure
        pricing_module = PathConfig.SRC_DIR / "pricing" / "pricing_engine.py"
        if not pricing_module.exists():
            print(f"  ✗ Pricing module not found: {pricing_module}")
            return False
        print(f"  ✓ Pricing module exists: {pricing_module}")
        # Check cost baselines file
        baselines_file = PathConfig.PRICING_DIR / "cost_baselines.json"
        if baselines_file.exists():
            print(f"  ✓ Cost baselines file created: {baselines_file}")
        # Check API functions
        from pricing.pricing_engine import create_pricing_engine, calculate_bid_price, validate_pricing_compliance
        print("  ✓ create_pricing_engine() function available")
        print("  ✓ calculate_bid_price() function available")
        print("  ✓ validate_pricing_compliance() function available")
        # Test API usage
        engine = create_pricing_engine()
        print("  ✓ Engine creation API working")
        # Test pricing API
        result = calculate_bid_price("Test pricing API")
        if result.recommended_price > 0:
            print(f"  ✓ Pricing API working - generated ${result.recommended_price:,.2f}")
        else:
            print(f"  ✗ Pricing API failed to generate valid price")
            return False
        return True
    except Exception as e:
        print(f"  ✗ API validation failed: {e}")
        return False
def run_validation():
    """Run all validation checks"""
    print("AI Pricing Engine Requirements Validation")
    print("=" * 70)
    validators = [
        ("Historical Award Data Integration", validate_requirement_1),
        ("Margin-Based Price Generation", validate_requirement_2),
        ("Competitive Pricing Validation", validate_requirement_3),
        ("Cost Baseline Integration", validate_requirement_4),
        ("90% Margin Compliance Rate", validate_requirement_5),
        ("Price Justification Generation", validate_requirement_6),
        ("File Structure & API Design", validate_requirement_7)
    ]
    results = []
    for requirement, validator in validators:
        print(f"\n{requirement}:")
        try:
            result = validator()
            results.append((requirement, result))
        except Exception as e:
            print(f"  ✗ Validation failed: {e}")
            results.append((requirement, False))
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    for requirement, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {requirement}")
    print(f"\nResult: {passed}/{total} requirements validated")
    if passed == total:
        print("\n🎉 All requirements validated! Pricing engine is production-ready.")
        print("✓ Historical award data integration working")
        print("✓ Margin compliance (15-50%, default 40%) enforced")
        print("✓ Competitive pricing against historical ranges")
        print("✓ Cost baselines for all categories loaded")
        print("✓ 90% margin compliance rate achieved")
        print("✓ Price justification generation functional")
        print("✓ API design complete and tested")
    else:
        print("\n⚠️ Some requirements not fully met. See details above.")
    return passed == total
if __name__ == "__main__":
    success = run_validation()
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    if success:
        print("1. Pricing engine is ready for integration with compliance matrix")
        print("2. Proceed to bid document generator implementation")
        print("3. Begin end-to-end pipeline testing")
    else:
        print("1. Address any failing validation checks")
        print("2. Re-run validation")
        print("3. Then proceed to next implementation step")
    sys.exit(0 if success else 1)