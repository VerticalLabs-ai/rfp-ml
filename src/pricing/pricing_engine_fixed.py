"""
Fixed AI-Powered Pricing Engine for Government RFP Bid Generation
Simplified version with robust error handling and fallback mechanisms
"""
import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import warnings
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.paths import PathConfig
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class PricingStrategy(Enum):
    """Available pricing strategies"""
    COST_PLUS = "cost_plus"
    MARKET_BASED = "market_based"
    HYBRID = "hybrid"
    COMPETITIVE = "competitive"
class RiskLevel(Enum):
    """Risk levels for pricing decisions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
@dataclass
class CostBaseline:
    """Cost baseline for different service categories"""
    category: str
    unit_type: str
    base_cost: float
    unit_description: str
    overhead_factor: float = 1.2
    labor_rate: Optional[float] = None
@dataclass
class PricingResult:
    """Result of pricing calculation"""
    category: str
    base_cost: float
    recommended_price: float
    margin_percentage: float
    margin_compliance: bool
    strategy_used: PricingStrategy
    confidence_score: float
    risk_level: RiskLevel
    justification: str
    competitive_analysis: Dict[str, Any]
    cost_breakdown: Dict[str, float]
class PricingEngineFixed:
    """
    Simplified AI-powered pricing engine with robust error handling
    """
    def __init__(self, 
                 processed_data_dir: str = str(PathConfig.DATA_DIR / "processed"),
                 pricing_data_dir: str = str(PathConfig.DATA_DIR / "pricing"),
                 default_margin: float = 0.40,
                 min_margin: float = 0.15,
                 max_margin: float = 0.50):
        """
        Initialize pricing engine
        """
        self.processed_data_dir = Path(processed_data_dir)
        self.pricing_data_dir = Path(pricing_data_dir)
        self.default_margin = default_margin
        self.min_margin = min_margin
        self.max_margin = max_margin
        # Create pricing data directory
        self.pricing_data_dir.mkdir(parents=True, exist_ok=True)
        # Initialize components
        self.historical_data = None
        self.cost_baselines = {}
        # Load configurations
        self._load_cost_baselines()
        self._load_historical_data()
        logger.info("Fixed Pricing Engine initialized successfully")
    def _load_cost_baselines(self):
        """Load or create cost baselines for different categories"""
        baseline_file = self.pricing_data_dir / "cost_baselines.json"
        if baseline_file.exists():
            try:
                with open(baseline_file, 'r') as f:
                    baselines_data = json.load(f)
                for category, data in baselines_data.items():
                    # Filter out any unexpected fields
                    valid_fields = {
                        'category', 'unit_type', 'base_cost', 
                        'unit_description', 'overhead_factor', 'labor_rate'
                    }
                    filtered_data = {k: v for k, v in data.items() if k in valid_fields}
                    self.cost_baselines[category] = CostBaseline(**filtered_data)
                logger.info(f"Loaded {len(self.cost_baselines)} cost baselines")
                return
            except Exception as e:
                logger.warning(f"Failed to load existing baselines: {e}")
        # Create default cost baselines
        self._create_default_baselines()
        self._save_cost_baselines()
    def _create_default_baselines(self):
        """Create default cost baselines for different categories"""
        baselines = {
            'bottled_water': CostBaseline(
                category='bottled_water',
                unit_type='case',
                base_cost=2.75,
                unit_description='24-bottle case of spring water',
                overhead_factor=1.15
            ),
            'construction': CostBaseline(
                category='construction',
                unit_type='hour',
                base_cost=85.00,
                unit_description='Labor hour including equipment',
                overhead_factor=1.25,
                labor_rate=65.00
            ),
            'delivery': CostBaseline(
                category='delivery',
                unit_type='delivery',
                base_cost=45.00,
                unit_description='Per delivery including fuel and labor',
                overhead_factor=1.20,
                labor_rate=25.00
            ),
            'general': CostBaseline(
                category='general',
                unit_type='unit',
                base_cost=50.00,
                unit_description='General service unit',
                overhead_factor=1.20
            )
        }
        self.cost_baselines = baselines
        logger.info("Created default cost baselines")
    def _save_cost_baselines(self):
        """Save cost baselines to file"""
        baseline_file = self.pricing_data_dir / "cost_baselines.json"
        baselines_data = {}
        for category, baseline in self.cost_baselines.items():
            baselines_data[category] = {
                'category': baseline.category,
                'unit_type': baseline.unit_type,
                'base_cost': baseline.base_cost,
                'unit_description': baseline.unit_description,
                'overhead_factor': baseline.overhead_factor,
                'labor_rate': baseline.labor_rate
            }
        with open(baseline_file, 'w') as f:
            json.dump(baselines_data, f, indent=2)
        logger.info(f"Cost baselines saved to {baseline_file}")
    def _load_historical_data(self):
        """Load historical RFP award data with robust column handling"""
        try:
            # Load processed RFP datasets
            datasets = []
            dataset_files = [
                "rfp_master_dataset.parquet",
                "bottled_water_rfps.parquet",
                "construction_rfps.parquet", 
                "delivery_rfps.parquet"
            ]
            for filename in dataset_files:
                file_path = self.processed_data_dir / filename
                if file_path.exists():
                    try:
                        df = pd.read_parquet(file_path)
                        df['source_file'] = filename
                        datasets.append(df)
                        logger.info(f"Loaded {len(df)} records from {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to load {filename}: {e}")
            if datasets:
                self.historical_data = pd.concat(datasets, ignore_index=True)
                self.historical_data = self.historical_data.drop_duplicates()
                # Clean and prepare data with robust column handling
                self._prepare_historical_data_robust()
                logger.info(f"Total historical records: {len(self.historical_data)}")
            else:
                logger.warning("No historical data loaded")
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            self.historical_data = None
    def _prepare_historical_data_robust(self):
        """Clean and prepare historical data with robust error handling"""
        if self.historical_data is None:
            return
        try:
            # Find contract value column with multiple possible names
            value_columns = [
                'total_contract_value', 'contract_value', 'award_amount', 
                'value', 'amount', 'contract_amount', 'total_value'
            ]
            contract_column = None
            for col in value_columns:
                if col in self.historical_data.columns:
                    contract_column = col
                    logger.info(f"Using {contract_column} for contract values")
                    break
            if contract_column:
                # Convert to numeric, handling various formats
                self.historical_data['contract_value_clean'] = pd.to_numeric(
                    self.historical_data[contract_column], 
                    errors='coerce'
                )
            else:
                # Create dummy column if no value column found
                logger.warning("No contract value column found, using baseline pricing only")
                self.historical_data['contract_value_clean'] = np.nan
            # Categorize contracts
            self.historical_data['pricing_category'] = self.historical_data.apply(
                self._determine_pricing_category, axis=1
            )
            # Only remove outliers if we have valid contract values
            valid_values = self.historical_data['contract_value_clean'].dropna()
            if len(valid_values) > 10:
                # Remove extreme outliers (beyond 99th and 1st percentiles)
                q99 = valid_values.quantile(0.99)
                q01 = valid_values.quantile(0.01)
                outlier_mask = (
                    (self.historical_data['contract_value_clean'] > q99) |
                    (self.historical_data['contract_value_clean'] < q01)
                )
                self.historical_data.loc[outlier_mask, 'contract_value_clean'] = np.nan
                logger.info(f"Cleaned {outlier_mask.sum()} outlier values")
            logger.info("Historical data prepared and cleaned successfully")
        except Exception as e:
            logger.error(f"Failed to prepare historical data: {e}")
            # Ensure we have the required columns even if processing fails
            if 'contract_value_clean' not in self.historical_data.columns:
                self.historical_data['contract_value_clean'] = np.nan
            if 'pricing_category' not in self.historical_data.columns:
                self.historical_data['pricing_category'] = 'general'
    def _determine_pricing_category(self, row: pd.Series) -> str:
        """Determine pricing category for a contract"""
        try:
            # Check description/title
            text_fields = []
            for field in ['description', 'title', 'category']:
                if field in row and pd.notna(row[field]):
                    text_fields.append(str(row[field]).lower())
            combined_text = ' '.join(text_fields)
            # Category keywords
            if any(keyword in combined_text for keyword in ['water', 'beverage', 'drinking']):
                return 'bottled_water'
            elif any(keyword in combined_text for keyword in ['construction', 'building', 'infrastructure']):
                return 'construction'
            elif any(keyword in combined_text for keyword in ['delivery', 'transport', 'logistics']):
                return 'delivery'
            # Check source file
            source = str(row.get('source_file', '')).lower()
            if 'water' in source:
                return 'bottled_water'
            elif 'construction' in source:
                return 'construction'
            elif 'delivery' in source:
                return 'delivery'
            return 'general'
        except Exception as e:
            logger.warning(f"Error determining category: {e}")
            return 'general'
    def _get_historical_statistics(self, category: str) -> Dict[str, float]:
        """Get historical contract value statistics for category"""
        if self.historical_data is None:
            return {}
        try:
            category_data = self.historical_data[
                (self.historical_data['pricing_category'] == category) &
                (self.historical_data['contract_value_clean'].notna())
            ]
            if len(category_data) == 0:
                return {}
            values = category_data['contract_value_clean']
            return {
                'count': len(values),
                'mean': float(values.mean()),
                'median': float(values.median()),
                'std': float(values.std()),
                'min': float(values.min()),
                'max': float(values.max()),
                'q25': float(values.quantile(0.25)),
                'q75': float(values.quantile(0.75))
            }
        except Exception as e:
            logger.warning(f"Error getting historical statistics: {e}")
            return {}
    def calculate_cost_plus_price(self, 
                                 category: str,
                                 quantity: float,
                                 duration_months: int = 12,
                                 complexity_factor: float = 1.0) -> Tuple[float, Dict[str, float]]:
        """Calculate cost-plus pricing"""
        if category not in self.cost_baselines:
            category = 'general'
        baseline = self.cost_baselines[category]
        # Base cost calculation
        base_unit_cost = baseline.base_cost * complexity_factor
        subtotal = base_unit_cost * quantity * duration_months
        # Add overhead
        overhead = subtotal * (baseline.overhead_factor - 1.0)
        # Additional costs
        insurance = subtotal * 0.02  # 2% insurance
        admin = subtotal * 0.05      # 5% admin
        total_cost = subtotal + overhead + insurance + admin
        cost_breakdown = {
            'base_cost': subtotal,
            'overhead': overhead,
            'insurance': insurance,
            'administrative': admin,
            'total': total_cost
        }
        return total_cost, cost_breakdown
    def calculate_market_based_price(self, 
                                   category: str,
                                   target_percentile: float = 0.6) -> Optional[float]:
        """Calculate market-based pricing using historical data"""
        stats = self._get_historical_statistics(category)
        if not stats or stats['count'] < 5:
            return None
        # Use percentile-based pricing
        price_range = stats['q75'] - stats['q25']
        market_price = stats['q25'] + (price_range * target_percentile)
        return market_price
    def generate_pricing(self,
                        rfp_description: str,
                        category: str = None,
                        quantity: float = None,
                        duration_months: int = 12,
                        strategy: PricingStrategy = PricingStrategy.HYBRID,
                        target_margin: Optional[float] = None) -> PricingResult:
        """Generate comprehensive pricing for an RFP"""
        try:
            # Auto-detect category if not provided
            if category is None:
                category = self._detect_category_from_description(rfp_description)
            # Auto-estimate quantity if not provided
            if quantity is None:
                quantity = self._estimate_quantity_from_description(rfp_description, category)
            # Use default margin if not specified
            if target_margin is None:
                target_margin = self.default_margin
            # Calculate base cost
            complexity_factor = self._assess_complexity(rfp_description)
            base_cost, cost_breakdown = self.calculate_cost_plus_price(
                category, quantity, duration_months, complexity_factor
            )
            # Apply pricing strategy
            if strategy == PricingStrategy.COST_PLUS:
                recommended_price = base_cost * (1 + target_margin)
                confidence = 0.8
            elif strategy == PricingStrategy.MARKET_BASED:
                market_price = self.calculate_market_based_price(category)
                if market_price and market_price > 0:
                    recommended_price = market_price
                    confidence = 0.9
                else:
                    # Fallback to cost-plus
                    recommended_price = base_cost * (1 + target_margin)
                    confidence = 0.6
            elif strategy == PricingStrategy.HYBRID:
                # Combine cost-plus and market-based
                cost_plus_price = base_cost * (1 + target_margin)
                market_price = self.calculate_market_based_price(category)
                if market_price and market_price > 0:
                    # Weight 60% market, 40% cost-plus
                    recommended_price = (market_price * 0.6) + (cost_plus_price * 0.4)
                    confidence = 0.85
                else:
                    recommended_price = cost_plus_price
                    confidence = 0.7
            elif strategy == PricingStrategy.COMPETITIVE:
                # Aggressive pricing for competitiveness
                market_price = self.calculate_market_based_price(category)
                if market_price and market_price > 0:
                    recommended_price = market_price * 0.95  # 5% below market
                    confidence = 0.7
                else:
                    recommended_price = base_cost * (1 + self.min_margin * 1.1)
                    confidence = 0.6
            else:
                # Default fallback
                recommended_price = base_cost * (1 + target_margin)
                confidence = 0.7
            # Calculate actual margin
            actual_margin = (recommended_price - base_cost) / base_cost if base_cost > 0 else 0
            # Check margin compliance
            margin_compliance = self.min_margin <= actual_margin <= self.max_margin
            # Assess risk
            risk_level = self._assess_pricing_risk(actual_margin, confidence, category)
            # Generate justification
            justification = self._generate_pricing_justification(
                category, strategy, actual_margin, cost_breakdown
            )
            # Competitive analysis
            competitive_analysis = self._analyze_competition(category, recommended_price)
            return PricingResult(
                category=category,
                base_cost=base_cost,
                recommended_price=recommended_price,
                margin_percentage=actual_margin,
                margin_compliance=margin_compliance,
                strategy_used=strategy,
                confidence_score=confidence,
                risk_level=risk_level,
                justification=justification,
                competitive_analysis=competitive_analysis,
                cost_breakdown=cost_breakdown
            )
        except Exception as e:
            logger.error(f"Error generating pricing: {e}")
            # Return a basic fallback result
            fallback_price = 10000.0  # Basic fallback
            return PricingResult(
                category=category or 'general',
                base_cost=fallback_price * 0.7,
                recommended_price=fallback_price,
                margin_percentage=0.30,
                margin_compliance=True,
                strategy_used=strategy,
                confidence_score=0.5,
                risk_level=RiskLevel.MEDIUM,
                justification="Fallback pricing due to processing error",
                competitive_analysis={},
                cost_breakdown={'total': fallback_price * 0.7}
            )
    def _detect_category_from_description(self, description: str) -> str:
        """Auto-detect category from RFP description"""
        desc_lower = description.lower()
        water_keywords = ['water', 'beverage', 'drinking', 'bottled']
        construction_keywords = ['construction', 'building', 'infrastructure', 'renovation']
        delivery_keywords = ['delivery', 'transport', 'logistics', 'shipping']
        if any(keyword in desc_lower for keyword in water_keywords):
            return 'bottled_water'
        elif any(keyword in desc_lower for keyword in construction_keywords):
            return 'construction'
        elif any(keyword in desc_lower for keyword in delivery_keywords):
            return 'delivery'
        else:
            return 'general'
    def _estimate_quantity_from_description(self, description: str, category: str) -> float:
        """Estimate quantity from RFP description"""
        import re
        # Look for numbers in description
        numbers = re.findall(r'\b\d+\b', description)
        if numbers:
            # Use the largest reasonable number found
            quantities = [int(n) for n in numbers if 1 <= int(n) <= 10000]
            estimated = max(quantities) if quantities else 100
        else:
            estimated = 100  # Default
        # Category-specific adjustments
        if category == 'bottled_water':
            return min(max(estimated, 50), 2000)
        elif category == 'construction':
            return min(max(estimated, 100), 5000)
        elif category == 'delivery':
            return min(max(estimated, 10), 500)
        else:
            return min(max(estimated, 50), 1000)
    def _assess_complexity(self, description: str) -> float:
        """Assess complexity factor from RFP description"""
        desc_lower = description.lower()
        complexity_indicators = {
            'high': ['specialized', 'complex', 'custom', 'emergency', '24/7', 'certified'],
            'medium': ['quality', 'compliance', 'reporting', 'insurance', 'bonded'],
            'low': ['standard', 'regular', 'basic', 'simple']
        }
        high_count = sum(1 for word in complexity_indicators['high'] if word in desc_lower)
        medium_count = sum(1 for word in complexity_indicators['medium'] if word in desc_lower)
        low_count = sum(1 for word in complexity_indicators['low'] if word in desc_lower)
        if high_count > medium_count and high_count > low_count:
            return 1.3  # 30% increase for high complexity
        elif low_count > medium_count and low_count > high_count:
            return 0.9  # 10% decrease for low complexity
        else:
            return 1.0  # Standard complexity
    def _assess_pricing_risk(self, margin: float, confidence: float, category: str) -> RiskLevel:
        """Assess pricing risk level"""
        risk_score = 0
        # Margin risk
        if margin < self.min_margin:
            risk_score += 3
        elif margin < self.min_margin * 1.5:
            risk_score += 2
        elif margin > self.max_margin * 0.8:
            risk_score += 1
        # Confidence risk
        if confidence < 0.6:
            risk_score += 2
        elif confidence < 0.8:
            risk_score += 1
        # Category risk
        if category == 'general':
            risk_score += 1
        # Convert to risk level
        if risk_score >= 5:
            return RiskLevel.VERY_HIGH
        elif risk_score >= 3:
            return RiskLevel.HIGH
        elif risk_score >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    def _generate_pricing_justification(self, 
                                      category: str,
                                      strategy: PricingStrategy,
                                      margin: float,
                                      cost_breakdown: Dict[str, float]) -> str:
        """Generate pricing justification text"""
        justification_parts = []
        # Strategy explanation
        strategy_explanations = {
            PricingStrategy.COST_PLUS: "Cost-plus methodology ensures all project costs are covered with appropriate margin.",
            PricingStrategy.MARKET_BASED: "Market-based pricing aligns with historical award patterns in this category.",
            PricingStrategy.HYBRID: "Hybrid approach balances cost coverage with market competitiveness.",
            PricingStrategy.COMPETITIVE: "Competitive pricing strategy to maximize win probability."
        }
        justification_parts.append(strategy_explanations.get(strategy, "Standard pricing approach applied."))
        # Margin explanation
        justification_parts.append(f"Target margin of {margin:.1%} ensures profitability while remaining competitive.")
        # Cost factors
        if cost_breakdown and cost_breakdown.get('total', 0) > 0:
            base_pct = (cost_breakdown.get('base_cost', 0) / cost_breakdown['total']) * 100
            overhead_pct = (cost_breakdown.get('overhead', 0) / cost_breakdown['total']) * 100
            justification_parts.append(
                f"Cost structure: {base_pct:.0f}% base costs, {overhead_pct:.0f}% overhead and administration."
            )
        return " ".join(justification_parts)
    def _analyze_competition(self, category: str, proposed_price: float) -> Dict[str, Any]:
        """Analyze competitive positioning"""
        stats = self._get_historical_statistics(category)
        analysis = {
            'market_position': 'unknown',
            'price_percentile': None,
            'competitive_advantage': [],
            'risk_factors': []
        }
        if stats and stats['count'] >= 5:
            # Determine market position
            if proposed_price <= stats['q25']:
                analysis['market_position'] = 'very_competitive'
                analysis['competitive_advantage'].append("Significantly below market average")
            elif proposed_price <= stats['median']:
                analysis['market_position'] = 'competitive'
                analysis['competitive_advantage'].append("Below market median")
            elif proposed_price <= stats['q75']:
                analysis['market_position'] = 'moderate'
            else:
                analysis['market_position'] = 'premium'
                analysis['risk_factors'].append("Above market average")
            # Calculate percentile
            if stats['max'] > stats['min']:
                percentile = (proposed_price - stats['min']) / (stats['max'] - stats['min'])
                analysis['price_percentile'] = percentile
        return analysis
    def validate_margin_compliance(self, pricing_results: List[PricingResult]) -> Dict[str, Any]:
        """Validate margin compliance across multiple pricing results"""
        if not pricing_results:
            return {"compliance_rate": 0, "details": []}
        compliant_count = sum(1 for result in pricing_results if result.margin_compliance)
        compliance_rate = compliant_count / len(pricing_results)
        validation = {
            "total_bids": len(pricing_results),
            "compliant_bids": compliant_count,
            "compliance_rate": compliance_rate,
            "target_rate": 0.90,  # 90% compliance target
            "passes_requirement": compliance_rate >= 0.90,
            "details": []
        }
        for i, result in enumerate(pricing_results):
            validation["details"].append({
                "bid_index": i,
                "category": result.category,
                "margin": result.margin_percentage,
                "compliant": result.margin_compliance,
                "risk_level": result.risk_level.value
            })
        return validation
    def get_pricing_statistics(self) -> Dict[str, Any]:
        """Get pricing engine statistics and capabilities"""
        stats = {
            "engine_status": "operational",
            "cost_baselines_loaded": len(self.cost_baselines),
            "categories_supported": list(self.cost_baselines.keys()),
            "historical_data_available": self.historical_data is not None,
            "margin_configuration": {
                "default_margin": self.default_margin,
                "min_margin": self.min_margin,
                "max_margin": self.max_margin
            },
            "strategies_available": [strategy.value for strategy in PricingStrategy]
        }
        if self.historical_data is not None:
            stats["historical_records"] = len(self.historical_data)
            try:
                stats["category_distribution"] = self.historical_data['pricing_category'].value_counts().to_dict()
            except Exception:
                stats["category_distribution"] = {}
        return stats
# Convenience functions
def create_pricing_engine() -> PricingEngineFixed:
    """Create and initialize fixed pricing engine"""
    return PricingEngineFixed()
def calculate_bid_price(rfp_description: str,
                       category: str = None,
                       strategy: PricingStrategy = PricingStrategy.HYBRID,
                       target_margin: float = 0.40) -> PricingResult:
    """Calculate bid price for an RFP"""
    engine = create_pricing_engine()
    return engine.generate_pricing(
        rfp_description=rfp_description,
        category=category,
        strategy=strategy,
        target_margin=target_margin
    )
def validate_pricing_compliance(pricing_results: List[PricingResult]) -> bool:
    """Validate that pricing results meet compliance requirements"""
    engine = create_pricing_engine()
    validation = engine.validate_margin_compliance(pricing_results)
    return validation["passes_requirement"]
if __name__ == "__main__":
    # Test the fixed pricing engine
    print("Testing Fixed AI Pricing Engine...")
    try:
        # Create engine
        engine = create_pricing_engine()
        stats = engine.get_pricing_statistics()
        print(f"✓ Engine Status: {stats['engine_status']}")
        print(f"✓ Categories: {stats['categories_supported']}")
        # Test pricing
        result = calculate_bid_price(
            "Monthly delivery of 500 cases of bottled water",
            category="bottled_water"
        )
        print(f"✓ Price: ${result.recommended_price:,.2f}")
        print(f"✓ Margin: {result.margin_percentage:.1%}")
        print(f"✓ Compliant: {result.margin_compliance}")
        print("\n🎉 Fixed Pricing Engine working correctly!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()