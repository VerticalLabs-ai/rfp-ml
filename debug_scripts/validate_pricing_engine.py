import json
import os
import sys
from datetime import datetime

# Add src to path
sys.path.append('/app/government_rfp_bid_1927/src')
from pricing.pricing_engine import PricingEngine, PricingStrategy


def comprehensive_pricing_validation():
    """
    Comprehensive validation of pricing engine across all categories and strategies
    """
    print("=== PRICING ENGINE COMPREHENSIVE VALIDATION ===")
    print(f"Validation started at: {datetime.now()}")
    # Initialize pricing engine
    engine = PricingEngine()
    print("\n1. Cost Baselines Verification:")
    for category, baseline in engine.cost_baselines.items():
        print(f"   {category}:")
        for key, value in baseline.items():
            if isinstance(value, (int, float)):
                if 'rate' in key or 'cost' in key:
                    print(f"     {key}: ${value:.2f}")
                else:
                    print(f"     {key}: {value}")
            else:
                print(f"     {key}: {value}")
    print("\n2. Historical Data Coverage:")
    for category, data in engine.historical_data.items():
        if 'statistics' in data:
            stats = data['statistics']
            print(f"   {category}: {stats['count']:,} samples, "
                  f"median: ${stats['median']:,.0f}, "
                  f"range: ${stats['q25']:,.0f} - ${stats['q75']:,.0f}")
        else:
            print(f"   {category}: No historical data available")
    # Define comprehensive test scenarios
    test_scenarios = {
        'bottled_water': [
            {
                'name': 'Small Office Water Service',
                'requirements': {
                    'cases_per_month': 25,
                    'contract_months': 12,
                    'delivery_distance_miles': 15,
                    'competitiveness': 'medium'
                }
            },
            {
                'name': 'Large Government Facility',
                'requirements': {
                    'cases_per_month': 150,
                    'contract_months': 36,
                    'delivery_distance_miles': 35,
                    'competitiveness': 'high'
                }
            }
        ],
        'construction': [
            {
                'name': 'Office Renovation Project',
                'requirements': {
                    'square_footage': 5000,
                    'duration_months': 6,
                    'complexity_factor': 1.0,
                    'competitiveness': 'medium'
                }
            },
            {
                'name': 'Large Infrastructure Project',
                'requirements': {
                    'square_footage': 25000,
                    'duration_months': 18,
                    'complexity_factor': 1.5,
                    'competitiveness': 'low'
                }
            }
        ],
        'delivery': [
            {
                'name': 'Standard Courier Service',
                'requirements': {
                    'deliveries_per_month': 80,
                    'contract_months': 12,
                    'average_distance_miles': 10,
                    'competitiveness': 'high'
                }
            },
            {
                'name': 'Large Scale Logistics',
                'requirements': {
                    'deliveries_per_month': 300,
                    'contract_months': 24,
                    'average_distance_miles': 25,
                    'competitiveness': 'medium'
                }
            }
        ]
    }
    validation_results = {
        'validation_timestamp': datetime.now().isoformat(),
        'test_results': {},
        'margin_compliance': {},
        'strategy_comparison': {},
        'performance_metrics': {}
    }
    print("\n3. Testing Pricing Scenarios:")
    all_results = []
    strategy_comparisons = []
    for category, scenarios in test_scenarios.items():
        print(f"\n   --- {category.upper()} CATEGORY ---")
        category_results = []
        for scenario in scenarios:
            print(f"\n   Scenario: {scenario['name']}")
            scenario_results = {}
            # Test all three pricing strategies
            for strategy in [PricingStrategy.COST_PLUS, PricingStrategy.MARKET_BASED, PricingStrategy.HYBRID]:
                try:
                    result = engine.generate_pricing(
                        category,
                        scenario['requirements'],
                        strategy
                    )
                    scenario_results[strategy.value] = {
                        'final_price': result.final_price,
                        'margin_percentage': result.margin_percentage,
                        'confidence_score': result.confidence_score,
                        'margin_compliant': result.margin_compliant,
                        'pricing_strategy': result.pricing_strategy,
                        'justification_length': len(result.justification)
                    }
                    all_results.append(result)
                    print(f"     {strategy.value}: ${result.final_price:,.0f} "
                          f"({result.margin_percentage:.0%} margin, "
                          f"conf: {result.confidence_score:.2f}, "
                          f"compliant: {result.margin_compliant})")
                except Exception as e:
                    print(f"     {strategy.value}: ERROR - {e}")
                    scenario_results[strategy.value] = {'error': str(e)}
            # Compare strategy results for this scenario
            if len(scenario_results) >= 2:
                prices = [r.get('final_price', 0) for r in scenario_results.values() if 'final_price' in r]
                if prices:
                    price_range = max(prices) - min(prices)
                    price_variance = price_range / min(prices) * 100 if min(prices) > 0 else 0
                    print(f"     Price variance across strategies: ${price_range:,.0f} ({price_variance:.1f}%)")
                    strategy_comparisons.append({
                        'category': category,
                        'scenario': scenario['name'],
                        'price_range': price_range,
                        'price_variance_percent': price_variance,
                        'strategies': scenario_results
                    })
            category_results.append({
                'scenario_name': scenario['name'],
                'requirements': scenario['requirements'],
                'results': scenario_results
            })
        validation_results['test_results'][category] = category_results
    # Margin compliance analysis
    print("\n4. Margin Compliance Analysis:")
    compliance_validation = engine.validate_margin_compliance(all_results)
    print(f"   Total pricing results: {compliance_validation['total_results']}")
    print(f"   Margin compliant results: {compliance_validation['compliant_results']}")
    print(f"   Compliance rate: {compliance_validation['compliance_rate']:.1%}")
    print(f"   Meets target (>90%): {compliance_validation['meets_target']}")
    print(f"   Margin range: {compliance_validation['margin_statistics']['min_margin']:.1%} - "
          f"{compliance_validation['margin_statistics']['max_margin']:.1%}")
    print(f"   Average margin: {compliance_validation['margin_statistics']['avg_margin']:.1%}")
    validation_results['margin_compliance'] = compliance_validation
    # Strategy comparison analysis
    print("\n5. Strategy Comparison Analysis:")
    if strategy_comparisons:
        avg_variance = sum(s['price_variance_percent'] for s in strategy_comparisons) / len(strategy_comparisons)
        max_variance = max(s['price_variance_percent'] for s in strategy_comparisons)
        print(f"   Average price variance across strategies: {avg_variance:.1f}%")
        print(f"   Maximum price variance: {max_variance:.1f}%")
        # Identify most consistent categories
        category_variances = {}
        for comp in strategy_comparisons:
            cat = comp['category']
            if cat not in category_variances:
                category_variances[cat] = []
            category_variances[cat].append(comp['price_variance_percent'])
        print("   Strategy consistency by category:")
        for cat, variances in category_variances.items():
            avg_var = sum(variances) / len(variances)
            print(f"     {cat}: {avg_var:.1f}% average variance")
    validation_results['strategy_comparison'] = {
        'comparisons': strategy_comparisons,
        'average_variance_percent': avg_variance if strategy_comparisons else 0,
        'max_variance_percent': max_variance if strategy_comparisons else 0
    }
    # Performance metrics
    print("\n6. Performance Metrics:")
    # Calculate success rates by strategy
    strategy_success = {}
    strategy_confidence = {}
    for result in all_results:
        strategy = result.pricing_strategy
        if strategy not in strategy_success:
            strategy_success[strategy] = {'total': 0, 'compliant': 0}
            strategy_confidence[strategy] = []
        strategy_success[strategy]['total'] += 1
        if result.margin_compliant:
            strategy_success[strategy]['compliant'] += 1
        strategy_confidence[strategy].append(result.confidence_score)
    print("   Strategy performance:")
    for strategy, data in strategy_success.items():
        success_rate = data['compliant'] / data['total'] if data['total'] > 0 else 0
        avg_confidence = sum(strategy_confidence[strategy]) / len(strategy_confidence[strategy])
        print(f"     {strategy}: {success_rate:.1%} compliance, "
              f"{avg_confidence:.2f} avg confidence")
    validation_results['performance_metrics'] = {
        'strategy_success_rates': {k: v['compliant']/v['total'] if v['total'] > 0 else 0
                                  for k, v in strategy_success.items()},
        'strategy_avg_confidence': {k: sum(v)/len(v) if v else 0
                                   for k, v in strategy_confidence.items()},
        'total_scenarios_tested': len(all_results)
    }
    # Save validation report
    report_path = "/app/government_rfp_bid_1927/analysis/pricing_validation_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(validation_results, f, indent=2)
    print(f"\n7. Validation Report Saved: {report_path}")
    # Overall assessment
    overall_success = (
        compliance_validation['meets_target'] and  # >90% margin compliance
        len(all_results) >= 18 and  # All scenarios tested (3 categories × 2 scenarios × 3 strategies)
        avg_variance < 50  # Price variance reasonable
    )
    print(f"\n=== VALIDATION RESULT: {'SUCCESS' if overall_success else 'NEEDS IMPROVEMENT'} ===")
    if overall_success:
        print("✅ Pricing engine meets all validation criteria")
    else:
        print("❌ Pricing engine needs improvement in some areas")
    return overall_success, validation_results
if __name__ == "__main__":
    success, results = comprehensive_pricing_validation()
    if success:
        print("\n🚀 Pricing engine validation PASSED - ready for integration")
    else:
        print("\n⚠️ Pricing engine validation requires attention")
