import pytest
import time
from typing import Dict, Any

from src.pricing.pricing_engine import PricingEngine

class TestPricingEngine:
    """Comprehensive testing of AI pricing engine across all bid sectors"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.pricing_engine = PricingEngine()

    def test_initialization(self):
        """Test that the pricing engine initializes correctly."""
        assert self.pricing_engine is not None
        assert len(self.pricing_engine.cost_baselines) > 0

    @pytest.mark.parametrize("scenario", [
        {
            "name": "IT Services Bid",
            "title": "IT Support Services",
            "description": "Provide network maintenance and helpdesk support.",
            "sector": "Technology",
            "rfp_requirements": ["24/7 Support", "ISO 27001"],
            "contract_characteristics": {"duration_months": 12},
            "expected_range": (100.0, 600.0)  # Hourly rate
        },
        {
            "name": "Construction Project",
            "title": "Office Renovation",
            "description": "Renovation of office building including HVAC and electrical.",
            "sector": "Construction",
            "rfp_requirements": ["Bonding", "Safety Plan"],
            "contract_characteristics": {"duration_months": 6},
            "expected_range": (100.0, 500.0)  # Sq ft rate or similar
        },
        {
            "name": "Consulting Services",
            "title": "Strategic Planning",
            "description": "Management consulting for strategic planning.",
            "sector": "Professional Services",
            "rfp_requirements": ["PhD Required", "Security Clearance"],
            "contract_characteristics": {"duration_months": 3},
            "expected_range": (150.0, 400.0)  # Hourly rate
        }
    ])
    def test_generate_competitive_bid(self, scenario):
        """Test bid generation for various scenarios."""
        print(f"\nTesting scenario: {scenario['name']}")
        
        start_time = time.time()
        pricing_result = self.pricing_engine.generate_pricing(
            scenario,
            strategy_name="competitive"
        )
        generation_time = time.time() - start_time
        
        assert pricing_result is not None, "Pricing result should not be None"
        
        # Check margin compliance
        # PricingResult has margin_percentage
        margin_percent = pricing_result.margin_percentage
        assert margin_percent >= 15.0, f"Margin should be compliant (>=15%) for {scenario['name']}"
        
        # Check expected range
        bid_amount = pricing_result.total_price
        expected_min, expected_max = scenario["expected_range"]
        # Allow 50% buffer as per original test
        assert expected_min <= bid_amount <= expected_max * 1.5, f"Bid ${bid_amount} out of range {expected_min}-{expected_max*1.5}"
        
        # Check justification
        justification = pricing_result.justification
        assert len(justification) > 50, "Justification should be detailed"
        
        # Check competitive position
        position = pricing_result.competitive_score
        assert position > 0, "Competitive position should be assessed"
        
        print(f"Generation time: {generation_time:.3f}s")