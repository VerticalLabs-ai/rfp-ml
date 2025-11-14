"""
Comprehensive testing of AI pricing engine across all bid sectors
Validates margin compliance, award benchmarking, and pricing justification
"""
import sys
import os
import time
import json
from typing import Dict, Any, List
# Add project root to path
sys.path.append('/app/government_rfp_bid_1927')
from src.pricing.pricing_engine import PricingEngine, PricingConfig
class PricingEngineValidator:
    """Comprehensive validator for pricing engine across all sectors"""
    def __init__(self):
        self.pricing_engine = None
        self.test_scenarios = self._create_test_scenarios()
        self.validation_results = {}
    def _create_test_scenarios(self) -> List[Dict[str, Any]]:
        """Create comprehensive test scenarios for all RFP sectors"""
        return [
            # Bottled Water Scenarios
            {
                "name": "Small Office Water Delivery",
                "sector": "bottled_water",
                "rfp_requirements": {
                    "duration": "12 months",
                    "delivery_frequency": "weekly",
                    "locations": "5",
                    "gallons": "5"
                },
                "contract_characteristics": {
                    "estimated_value": 15000,
                    "duration_months": 12,
                    "location": "urban"
                },
                "expected_range": (12000, 25000)
            },
            {
                "name": "Large Government Water Contract",
                "sector": "bottled_water", 
                "rfp_requirements": {
                    "duration": "24 months",
                    "delivery_frequency": "weekly",
                    "locations": "25",
                    "gallons": "5"
                },
                "contract_characteristics": {
                    "estimated_value": 180000,
                    "duration_months": 24,
                    "location": "metro"
                },
                "expected_range": (150000, 250000)
            },
            # Construction Scenarios
            {
                "name": "Building Maintenance Contract",
                "sector": "construction",
                "rfp_requirements": {
                    "duration": "24 months", 
                    "scope": "general maintenance",
                    "estimated_value": 500000
                },
                "contract_characteristics": {
                    "estimated_value": 500000,
                    "duration_months": 24,
                    "location": "urban"
                },
                "expected_range": (400000, 700000)
            },
            {
                "name": "Major Renovation Project",
                "sector": "construction",
                "rfp_requirements": {
                    "duration": "36 months",
                    "scope": "major renovation HVAC electrical",
                    "estimated_value": 2500000
                },
                "contract_characteristics": {
                    "estimated_value": 2500000,
                    "duration_months": 36,
                    "location": "urban"
                },
                "expected_range": (2000000, 3500000)
            },
            # Delivery Scenarios
            {
                "name": "Local Delivery Services",
                "sector": "delivery",
                "rfp_requirements": {
                    "duration": "12 months",
                    "frequency": "50",
                    "service_area": "local"
                },
                "contract_characteristics": {
                    "estimated_value": 80000,
                    "duration_months": 12,
                    "location": "city"
                },
                "expected_range": (60000, 120000)
            },
            {
                "name": "Regional Logistics Contract",
                "sector": "delivery",
                "rfp_requirements": {
                    "duration": "24 months",
                    "frequency": "200", 
                    "service_area": "regional"
                },
                "contract_characteristics": {
                    "estimated_value": 400000,
                    "duration_months": 24,
                    "location": "regional"
                },
                "expected_range": (300000, 600000)
            }
        ]
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation across all test scenarios"""
        print("💰 COMPREHENSIVE PRICING ENGINE VALIDATION")
        print("=" * 60)
        # Initialize pricing engine
        print("\n1️⃣ Initializing Pricing Engine...")
        try:
            self.pricing_engine = PricingEngine()
            init_success = self.pricing_engine.initialize()
            if not init_success:
                return {"status": "error", "message": "Failed to initialize pricing engine"}
            print("   ✓ Pricing engine initialized with historical data")
            print(f"   ✓ Benchmarks loaded for {len(self.pricing_engine.benchmarks)} datasets")
        except Exception as e:
            print(f"   ❌ Initialization failed: {e}")
            return {"status": "error", "message": str(e)}
        # Test scenarios across all sectors
        print("\n2️⃣ Testing Pricing Across All Sectors...")
        sector_results = {}
        overall_metrics = {
            "total_scenarios": len(self.test_scenarios),
            "successful_pricing": 0,
            "margin_compliant": 0,
            "competitive_positioning": 0,
            "generation_times": [],
            "pricing_accuracy": []
        }
        for i, scenario in enumerate(self.test_scenarios, 1):
            print(f"\n   💼 Scenario {i}: {scenario['name']} ({scenario['sector'].upper()})")
            try:
                # Generate pricing
                start_time = time.time()
                pricing_result = self.pricing_engine.generate_competitive_bid(
                    scenario['sector'],
                    scenario['rfp_requirements'],
                    scenario['contract_characteristics']
                )
                generation_time = time.time() - start_time
                # Validate results
                validation = self._validate_pricing_result(scenario, pricing_result)
                # Record metrics
                overall_metrics["generation_times"].append(generation_time)
                if pricing_result:
                    overall_metrics["successful_pricing"] += 1
                    margin_compliant = pricing_result["margin_validation"]["margin_compliant"]
                    if margin_compliant:
                        overall_metrics["margin_compliant"] += 1
                    # Check if pricing is within expected range
                    bid_amount = pricing_result["recommended_bid"]
                    expected_min, expected_max = scenario["expected_range"]
                    within_range = expected_min <= bid_amount <= expected_max * 1.5  # Allow 50% buffer
                    if within_range:
                        overall_metrics["competitive_positioning"] += 1
                        overall_metrics["pricing_accuracy"].append(1.0)
                    else:
                        overall_metrics["pricing_accuracy"].append(0.0)
                    # Display results
                    margin = pricing_result["margin_validation"]["actual_margin"]
                    position = pricing_result["competitive_position"]
                    print(f"      ✓ Generated bid: ${bid_amount:,.2f}")
                    print(f"      ✓ Margin: {margin:.1%} ({'✅ Compliant' if margin_compliant else '❌ Non-compliant'})")
                    print(f"      ✓ Position: {position}")
                    print(f"      ✓ Generation time: {generation_time:.3f}s")
                    print(f"      ✓ Within range: {'Yes' if within_range else 'No'}")
                # Store detailed results
                scenario_result = {
                    "scenario": scenario,
                    "pricing_result": pricing_result,
                    "validation": validation,
                    "generation_time": generation_time
                }
                sector_results[f"scenario_{i}"] = scenario_result
            except Exception as e:
                print(f"      ❌ Pricing generation failed: {e}")
                error_result = {
                    "scenario": scenario,
                    "error": str(e),
                    "generation_time": 0
                }
                sector_results[f"scenario_{i}"] = error_result
        # Performance Assessment
        print("\n3️⃣ Performance Assessment...")
        success_rate = overall_metrics["successful_pricing"] / overall_metrics["total_scenarios"]
        margin_compliance_rate = overall_metrics["margin_compliant"] / overall_metrics["total_scenarios"]
        competitive_accuracy = overall_metrics["competitive_positioning"] / overall_metrics["total_scenarios"]
        avg_generation_time = sum(overall_metrics["generation_times"]) / len(overall_metrics["generation_times"]) if overall_metrics["generation_times"] else 0
        print(f"   📊 Success Rate: {success_rate:.1%} ({overall_metrics['successful_pricing']}/{overall_metrics['total_scenarios']})")
        print(f"   📊 Margin Compliance: {margin_compliance_rate:.1%} ({overall_metrics['margin_compliant']}/{overall_metrics['total_scenarios']})")
        print(f"   📊 Competitive Accuracy: {competitive_accuracy:.1%} ({overall_metrics['competitive_positioning']}/{overall_metrics['total_scenarios']})")
        print(f"   📊 Avg Generation Time: {avg_generation_time:.3f}s")
        # Sector-specific analysis
        print("\n4️⃣ Sector-Specific Analysis...")
        sector_performance = {}
        for sector in ['bottled_water', 'construction', 'delivery']:
            sector_scenarios = [r for r in sector_results.values() 
                              if r.get('scenario', {}).get('sector') == sector]
            if sector_scenarios:
                successful = sum(1 for s in sector_scenarios if 'pricing_result' in s and s['pricing_result'])
                total = len(sector_scenarios)
                sector_performance[sector] = {
                    "success_rate": successful / total,
                    "total_scenarios": total,
                    "successful_scenarios": successful
                }
                print(f"   🎯 {sector.upper().replace('_', ' ')}: {successful}/{total} successful ({successful/total:.1%})")
        # Overall Assessment
        print("\n" + "=" * 60)
        print("📊 PRICING ENGINE VALIDATION SUMMARY")
        print("=" * 60)
        overall_score = (success_rate + margin_compliance_rate + competitive_accuracy) / 3
        if overall_score >= 0.9 and avg_generation_time < 5.0:
            assessment = "EXCELLENT"
            print("🎉 PRICING ENGINE STATUS: EXCELLENT")
        elif overall_score >= 0.8 and avg_generation_time < 10.0:
            assessment = "VERY_GOOD" 
            print("✅ PRICING ENGINE STATUS: VERY GOOD")
        elif overall_score >= 0.7:
            assessment = "GOOD"
            print("⚠️  PRICING ENGINE STATUS: GOOD")
        else:
            assessment = "NEEDS_IMPROVEMENT"
            print("❌ PRICING ENGINE STATUS: NEEDS IMPROVEMENT")
        print(f"\n📈 Key Metrics:")
        print(f"   • Overall Score: {overall_score:.1%}")
        print(f"   • Success Rate: {success_rate:.1%}")
        print(f"   • Margin Compliance: {margin_compliance_rate:.1%}")
        print(f"   • Competitive Accuracy: {competitive_accuracy:.1%}")
        print(f"   • Generation Speed: {avg_generation_time:.3f}s avg")
        # Compile final results
        final_results = {
            "assessment": assessment,
            "overall_score": overall_score,
            "overall_metrics": overall_metrics,
            "sector_performance": sector_performance,
            "sector_results": sector_results,
            "system_benchmarks": self.pricing_engine.benchmarks,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        # Save results
        results_path = "/app/government_rfp_bid_1927/logs/pricing_validation_results.json"
        os.makedirs(os.path.dirname(results_path), exist_ok=True)
        with open(results_path, 'w') as f:
            json.dump(final_results, f, indent=2, default=str)
        print(f"\n📄 Detailed results saved to: {results_path}")
        if assessment in ["EXCELLENT", "VERY_GOOD"]:
            print(f"\n🚀 PRICING ENGINE IS PRODUCTION READY!")
        else:
            print(f"\n⚠️  Pricing engine needs optimization before production use")
        return final_results
    def _validate_pricing_result(self, scenario: Dict[str, Any], pricing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual pricing result"""
        validation = {
            "scenario_name": scenario["name"],
            "sector": scenario["sector"],
            "pricing_generated": pricing_result is not None,
            "margin_compliant": False,
            "within_expected_range": False,
            "has_justification": False,
            "competitive_position_assessed": False
        }
        if pricing_result:
            # Check margin compliance
            margin_val = pricing_result.get("margin_validation", {})
            validation["margin_compliant"] = margin_val.get("margin_compliant", False)
            # Check expected range
            bid_amount = pricing_result.get("recommended_bid", 0)
            expected_min, expected_max = scenario["expected_range"]
            validation["within_expected_range"] = expected_min <= bid_amount <= expected_max * 1.5
            # Check justification
            justification = pricing_result.get("pricing_justification", "")
            validation["has_justification"] = len(justification) > 50
            # Check competitive position
            position = pricing_result.get("competitive_position", "")
            validation["competitive_position_assessed"] = len(position) > 0
        return validation
def main():
    """Main validation function"""
    validator = PricingEngineValidator()
    results = validator.run_comprehensive_validation()
    # Determine success
    success = results.get("assessment") in ["EXCELLENT", "VERY_GOOD", "GOOD"]
    return success
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)