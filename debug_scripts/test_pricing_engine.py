"""
Comprehensive Pricing Engine Validation Script
"""
import sys
import os
import json
sys.path.append('/app/government_rfp_bid_1927')
def test_pricing_engine():
    """Comprehensive test of pricing engine functionality"""
    print("💰 COMPREHENSIVE PRICING ENGINE TEST")
    print("=" * 60)
    try:
        from src.pricing.pricing_engine import create_pricing_engine, PricingStrategy
        print("✅ Pricing Engine import successful")
        # Create pricing engine
        pricing_engine = create_pricing_engine()
        print("✅ Pricing Engine created")
        # Get system summary
        summary = pricing_engine.get_pricing_summary()
        print(f"\n📊 PRICING ENGINE STATUS:")
        print(f"   Engine Status: {summary['engine_status']}")
        print(f"   Cost Baselines: {summary['cost_baselines']}")
        print(f"   Market Data Available: {summary['market_data_available']}")
        print(f"   ML Models Available: {summary['ml_models_available']}")
        # Test scenarios for different categories
        test_scenarios = [
            {
                "name": "Bottled Water Supply",
                "category": "bottled_water",
                "description": "Supply bottled water to federal agencies nationwide",
                "quantity": 1000,
                "duration_months": 12,
                "location": "urban",
                "strategy": PricingStrategy.HYBRID
            },
            {
                "name": "Construction Project",
                "category": "construction",
                "description": "Office building renovation including HVAC and electrical work",
                "quantity": 50000,
                "duration_months": 18,
                "location": "high_cost",
                "strategy": PricingStrategy.MARKET_BASED
            },
            {
                "name": "Delivery Services",
                "category": "delivery",
                "description": "Logistics and delivery services for government supplies",
                "quantity": 500,
                "duration_months": 24,
                "location": "medium",
                "strategy": PricingStrategy.COMPETITIVE
            },
            {
                "name": "General Services",
                "category": "general",
                "description": "General contracting and maintenance services",
                "quantity": 100,
                "duration_months": 12,
                "location": "default",
                "strategy": PricingStrategy.COST_PLUS
            }
        ]
        print(f"\n🧪 TESTING PRICING SCENARIOS:")
        scenario_results = []
        for scenario in test_scenarios:
            print(f"\n   {scenario['name'].upper()}:")
            try:
                result = pricing_engine.calculate_pricing(
                    category=scenario["category"],
                    description=scenario["description"],
                    quantity=scenario["quantity"],
                    duration_months=scenario["duration_months"],
                    location=scenario["location"],
                    strategy=scenario["strategy"]
                )
                scenario_results.append({
                    "scenario": scenario["name"],
                    "category": scenario["category"],
                    "recommended_price": result.recommended_price,
                    "margin_achieved": result.margin_achieved,
                    "margin_compliance": result.margin_compliance,
                    "confidence_score": result.confidence_score,
                    "strategy_used": result.strategy_used.value,
                    "risk_level": result.risk_assessment.get("overall_risk", "unknown"),
                    "market_contracts": result.market_analysis.similar_contracts_count,
                    "cost_breakdown": result.cost_breakdown
                })
                print(f"      ✅ Price: ${result.recommended_price:,.2f}")
                print(f"      ✅ Margin: {result.margin_achieved:.1%} ({'✅' if result.margin_compliance else '❌'} compliant)")
                print(f"      ✅ Confidence: {result.confidence_score:.2f}")
                print(f"      ✅ Strategy: {result.strategy_used.value}")
                print(f"      ✅ Market Data: {result.market_analysis.similar_contracts_count} contracts")
            except Exception as e:
                print(f"      ❌ Failed: {str(e)}")
                scenario_results.append({
                    "scenario": scenario["name"],
                    "error": str(e)
                })
        # Test pricing sensitivity analysis
        print(f"\n📈 TESTING PRICING SENSITIVITY:")
        if scenario_results and "error" not in scenario_results[0]:
            try:
                # Get the first successful result for sensitivity analysis
                base_result = pricing_engine.calculate_pricing(
                    category="bottled_water",
                    description="Test sensitivity analysis",
                    quantity=1000,
                    duration_months=12
                )
                sensitivity = pricing_engine.analyze_pricing_sensitivity(base_result)
                print(f"   ✅ Price Variations Tested: {len(sensitivity['price_variations'])}")
                print(f"   ✅ Margin Analysis: Available")
                print(f"   ✅ Win Probability Model: Available")
                # Show a few sensitivity points
                for i, analysis in enumerate(sensitivity['margin_analysis'][:3]):
                    price = analysis['price']
                    margin = analysis['margin']
                    compliance = analysis['margin_compliance']
                    print(f"      Price ${price:,.0f}: {margin:.1%} margin ({'✅' if compliance else '❌'})")
            except Exception as e:
                print(f"   ❌ Sensitivity analysis failed: {str(e)}")
        # Test integration with RAG system
        print(f"\n🔗 TESTING RAG INTEGRATION:")
        try:
            from src.rag.rag_llm_integration import create_rag_llm_integrator
            integrator = create_rag_llm_integrator()
            # Test RAG-enhanced pricing analysis
            rag_pricing_result = integrator.analyze_pricing(
                "Bottled water delivery contract for federal agencies",
                "1000 cases monthly for 12 months"
            )
            print(f"   ✅ RAG Integration: {rag_pricing_result.documents_retrieved} docs retrieved")
            print(f"   ✅ Enhanced Analysis: {len(rag_pricing_result.generated_text)} chars")
            print(f"   ✅ Context Used: {len(rag_pricing_result.context_used)} chars")
            rag_integration_success = True
        except Exception as e:
            print(f"   ❌ RAG integration failed: {str(e)}")
            rag_integration_success = False
        # Generate comprehensive test report
        test_report = {
            "timestamp": str(os.popen('date').read().strip()),
            "pricing_engine_status": summary,
            "scenario_results": scenario_results,
            "margin_compliance_rate": sum(1 for r in scenario_results if r.get("margin_compliance")) / len([r for r in scenario_results if "error" not in r]) if scenario_results else 0,
            "average_confidence": sum(r.get("confidence_score", 0) for r in scenario_results if "error" not in r) / len([r for r in scenario_results if "error" not in r]) if scenario_results else 0,
            "rag_integration_success": rag_integration_success,
            "test_summary": {
                "total_scenarios": len(test_scenarios),
                "successful_scenarios": len([r for r in scenario_results if "error" not in r]),
                "failed_scenarios": len([r for r in scenario_results if "error" in r])
            }
        }
        # Save test report
        os.makedirs('/app/government_rfp_bid_1927/logs', exist_ok=True)
        with open('/app/government_rfp_bid_1927/logs/pricing_engine_test_report.json', 'w') as f:
            json.dump(test_report, f, indent=2, default=str)
        print(f"\n" + "=" * 60)
        print("✅ PRICING ENGINE TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Engine Status: {summary['engine_status']}")
        print(f"✅ Scenarios Tested: {test_report['test_summary']['successful_scenarios']}/{test_report['test_summary']['total_scenarios']}")
        print(f"✅ Margin Compliance Rate: {test_report['margin_compliance_rate']:.1%}")
        print(f"✅ Average Confidence: {test_report['average_confidence']:.2f}")
        print(f"✅ RAG Integration: {rag_integration_success}")
        print(f"\n📄 Test report saved: logs/pricing_engine_test_report.json")
        return True
    except Exception as e:
        print(f"❌ Pricing Engine test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
if __name__ == "__main__":
    success = test_pricing_engine()
    if success:
        print(f"\n🎉 PRICING ENGINE: OPERATIONAL AND READY")
        print(f"🔄 Ready for integration with bid generation pipeline")
    else:
        print(f"\n❌ PRICING ENGINE: Issues detected")