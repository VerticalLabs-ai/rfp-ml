"""
AI Pricing Engine for RFP bid generation system.
Generates competitive pricing while maintaining target margins using historical data and cost baselines.
"""
import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import statistics

# Import path configuration
from config.paths import PathConfig
@dataclass
class PricingStrategy:
    """Pricing strategy configuration."""
    strategy_name: str
    base_margin: float
    competitive_factor: float
    risk_adjustment: float
    minimum_margin: float
    maximum_margin: float
@dataclass
class CostBaseline:
    """Cost baseline for a category or service type."""
    category: str
    unit_type: str
    base_cost: float
    labor_rate: float
    material_multiplier: float
    overhead_rate: float
    profit_margin: float
@dataclass
class PricingResult:
    """Result of pricing calculation."""
    total_price: float
    base_cost: float
    margin_percentage: float
    pricing_strategy: str
    competitive_score: float
    risk_factors: List[str]
    price_breakdown: Dict[str, float]
    justification: str
    confidence_score: float
class PricingEngine:
    """
    AI-powered pricing engine for government RFP bids.
    Analyzes historical data and generates competitive pricing with margin compliance.
    """
    def __init__(
        self,
        rag_engine=None,
        compliance_generator=None,
        data_dir: str | None = None,
        pricing_dir: str | None = None,
        target_margin: float = 0.40,
        minimum_margin: float = 0.15
    ):
        """
        Initialize pricing engine.
        Args:
            rag_engine: RAG engine for historical context
            compliance_generator: Compliance matrix generator for requirement analysis
            data_dir: Directory with processed RFP data
            pricing_dir: Directory for pricing configurations and outputs
            target_margin: Target profit margin (default 40%)
            minimum_margin: Minimum acceptable margin (default 15%)
        """
        # Ensure PathConfig directories are initialized
        PathConfig.ensure_directories()

        self.rag_engine = rag_engine
        self.compliance_generator = compliance_generator
        self.data_dir = data_dir or str(PathConfig.PROCESSED_DATA_DIR)
        self.pricing_dir = pricing_dir or str(PathConfig.PRICING_DIR)
        self.target_margin = target_margin
        self.minimum_margin = minimum_margin
        # Create directories
        os.makedirs(self.pricing_dir, exist_ok=True)
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        # Load historical pricing data
        self.historical_data = self._load_historical_data()
        # Load cost baselines
        self.cost_baselines = self._load_cost_baselines()
        # Initialize pricing strategies
        self.pricing_strategies = self._initialize_pricing_strategies()
        # Load NAICS pricing patterns
        self.naics_patterns = self._analyze_naics_pricing()
    def _load_historical_data(self) -> pd.DataFrame:
        """Load and combine historical RFP award data."""
        historical_data = []
        datasets = [
            'rfp_master_dataset.parquet',
            'bottled_water_rfps.parquet',
            'construction_rfps.parquet', 
            'delivery_rfps.parquet'
        ]
        for dataset in datasets:
            file_path = os.path.join(self.data_dir, dataset)
            if os.path.exists(file_path):
                try:
                    df = pd.read_parquet(file_path)
                    df['source_dataset'] = dataset
                    historical_data.append(df)
                    self.logger.info(f"Loaded {len(df)} records from {dataset}")
                except Exception as e:
                    self.logger.warning(f"Failed to load {dataset}: {e}")
        if historical_data:
            combined_df = pd.concat(historical_data, ignore_index=True)
            # Clean and process award amounts
            if 'award_amount_clean' in combined_df.columns:
                combined_df['award_amount'] = pd.to_numeric(combined_df['award_amount_clean'], errors='coerce')
            elif 'award_amount' in combined_df.columns:
                combined_df['award_amount'] = pd.to_numeric(combined_df['award_amount'], errors='coerce')
            else:
                combined_df['award_amount'] = np.nan
            # Filter valid records
            valid_df = combined_df[
                (combined_df['award_amount'].notna()) & 
                (combined_df['award_amount'] > 0)
            ].copy()
            self.logger.info(f"Loaded {len(valid_df)} records with valid award amounts")
            return valid_df
        self.logger.warning("No historical data loaded")
        return pd.DataFrame()
    def _load_cost_baselines(self) -> Dict[str, CostBaseline]:
        """Load or create cost baseline data for different categories."""
        baselines_path = os.path.join(self.pricing_dir, "cost_baselines.json")
        # Default cost baselines based on industry standards
        default_baselines = {
            "bottled_water": {
                "category": "bottled_water",
                "unit_type": "case",
                "base_cost": 3.50,  # per case
                "labor_rate": 25.00,  # per hour
                "material_multiplier": 1.15,
                "overhead_rate": 0.20,
                "profit_margin": 0.35
            },
            "construction": {
                "category": "construction",
                "unit_type": "square_foot",
                "base_cost": 120.00,  # per sq ft
                "labor_rate": 65.00,  # per hour
                "material_multiplier": 1.25,
                "overhead_rate": 0.25,
                "profit_margin": 0.20
            },
            "delivery": {
                "category": "delivery",
                "unit_type": "mile",
                "base_cost": 2.50,  # per mile
                "labor_rate": 35.00,  # per hour
                "material_multiplier": 1.10,
                "overhead_rate": 0.18,
                "profit_margin": 0.30
            },
            "professional_services": {
                "category": "professional_services",
                "unit_type": "hour",
                "base_cost": 150.00,  # per hour
                "labor_rate": 85.00,  # per hour
                "material_multiplier": 1.05,
                "overhead_rate": 0.30,
                "profit_margin": 0.40
            },
            "maintenance": {
                "category": "maintenance",
                "unit_type": "service_call",
                "base_cost": 250.00,  # per call
                "labor_rate": 75.00,  # per hour
                "material_multiplier": 1.20,
                "overhead_rate": 0.22,
                "profit_margin": 0.35
            },
            "it_services": {
                "category": "it_services",
                "unit_type": "hour",
                "base_cost": 125.00,  # per hour
                "labor_rate": 95.00,  # per hour
                "material_multiplier": 1.08,
                "overhead_rate": 0.28,
                "profit_margin": 0.45
            }
        }
        if os.path.exists(baselines_path):
            try:
                with open(baselines_path, 'r') as f:
                    loaded_baselines = json.load(f)
                self.logger.info(f"Loaded cost baselines from {baselines_path}")
                # Convert to CostBaseline objects
                baselines = {}
                for key, data in loaded_baselines.items():
                    baselines[key] = CostBaseline(**data)
                return baselines
            except Exception as e:
                self.logger.warning(f"Failed to load cost baselines: {e}")
        # Save default baselines
        with open(baselines_path, 'w') as f:
            json.dump(default_baselines, f, indent=2)
        # Convert to CostBaseline objects
        baselines = {}
        for key, data in default_baselines.items():
            baselines[key] = CostBaseline(**data)
        self.logger.info(f"Created default cost baselines at {baselines_path}")
        return baselines
    def _initialize_pricing_strategies(self) -> Dict[str, PricingStrategy]:
        """Initialize different pricing strategies."""
        strategies = {
            "competitive": PricingStrategy(
                strategy_name="competitive",
                base_margin=0.25,
                competitive_factor=0.90,  # Bid 10% below median
                risk_adjustment=0.05,
                minimum_margin=0.15,
                maximum_margin=0.35
            ),
            "value_based": PricingStrategy(
                strategy_name="value_based", 
                base_margin=0.40,
                competitive_factor=1.05,  # Bid 5% above median (premium positioning)
                risk_adjustment=0.10,
                minimum_margin=0.20,
                maximum_margin=0.50
            ),
            "cost_plus": PricingStrategy(
                strategy_name="cost_plus",
                base_margin=0.30,
                competitive_factor=1.00,  # Bid at median
                risk_adjustment=0.08,
                minimum_margin=0.18,
                maximum_margin=0.45
            ),
            "aggressive": PricingStrategy(
                strategy_name="aggressive",
                base_margin=0.20,
                competitive_factor=0.85,  # Bid 15% below median
                risk_adjustment=0.03,
                minimum_margin=0.12,
                maximum_margin=0.30
            )
        }
        return strategies
    def _analyze_naics_pricing(self) -> Dict[str, Dict[str, float]]:
        """Analyze pricing patterns by NAICS code."""
        if self.historical_data.empty:
            return {}
        naics_patterns = {}
        if 'naics_code' in self.historical_data.columns:
            grouped = self.historical_data.groupby('naics_code')['award_amount'].agg([
                'count', 'mean', 'median', 'std', 
                lambda x: x.quantile(0.25),
                lambda x: x.quantile(0.75)
            ])
            grouped.columns = ['count', 'mean', 'median', 'std', 'q25', 'q75']
            # Only include NAICS codes with sufficient data
            valid_naics = grouped[grouped['count'] >= 5]
            for naics_code, row in valid_naics.iterrows():
                naics_patterns[str(naics_code)] = {
                    'count': int(row['count']),
                    'mean': float(row['mean']),
                    'median': float(row['median']),
                    'std': float(row['std']),
                    'q25': float(row['q25']),
                    'q75': float(row['q75']),
                    'confidence': min(1.0, row['count'] / 20.0)  # Confidence based on sample size
                }
        self.logger.info(f"Analyzed pricing patterns for {len(naics_patterns)} NAICS codes")
        return naics_patterns
    def _determine_category(self, rfp_data: Dict[str, Any]) -> str:
        """Determine the category of an RFP for cost baseline selection."""
        title = str(rfp_data.get('title', '')).lower()
        description = str(rfp_data.get('description', '')).lower()
        naics_code = str(rfp_data.get('naics_code', ''))
        # Category mapping based on keywords and NAICS codes
        if any(keyword in title + description for keyword in ['water', 'beverage', 'bottle']):
            return 'bottled_water'
        elif any(keyword in title + description for keyword in ['construction', 'building', 'infrastructure', 'renovation']):
            return 'construction'
        elif any(keyword in title + description for keyword in ['delivery', 'transport', 'logistics', 'shipping']):
            return 'delivery'
        elif any(keyword in title + description for keyword in ['maintenance', 'repair', 'service']):
            return 'maintenance'
        elif any(keyword in title + description for keyword in ['software', 'technology', 'system', 'network']):
            return 'it_services'
        elif naics_code.startswith('54'):  # Professional services
            return 'professional_services'
        elif naics_code.startswith('23'):  # Construction
            return 'construction'
        elif naics_code.startswith('48') or naics_code.startswith('49'):  # Transportation
            return 'delivery'
        else:
            return 'professional_services'  # Default category
    def _get_historical_pricing_context(self, rfp_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get historical pricing context for similar RFPs."""
        context = {
            'similar_awards': [],
            'naics_statistics': {},
            'category_statistics': {},
            'competitive_landscape': {}
        }
        if self.historical_data.empty:
            return context
        # Get NAICS-specific statistics
        naics_code = str(rfp_data.get('naics_code', ''))
        if naics_code and naics_code in self.naics_patterns:
            context['naics_statistics'] = self.naics_patterns[naics_code]
        # Get category-specific statistics
        category = self._determine_category(rfp_data)
        category_data = self.historical_data[
            self.historical_data['description'].str.contains(category, case=False, na=False) |
            self.historical_data['title'].str.contains(category, case=False, na=False)
        ]
        if not category_data.empty:
            awards = category_data['award_amount']
            context['category_statistics'] = {
                'count': len(awards),
                'mean': float(awards.mean()),
                'median': float(awards.median()),
                'std': float(awards.std()),
                'min': float(awards.min()),
                'max': float(awards.max())
            }
        # Use RAG to find similar RFPs if available
        if self.rag_engine:
            try:
                query = f"{rfp_data.get('title', '')} {rfp_data.get('description', '')}"[:500]
                similar_rfps = self.rag_engine.retrieve(query, k=5)
                context['similar_awards'] = []
                for rfp in similar_rfps:
                    # Extract award amount from metadata if available
                    award_amount = rfp.get('metadata', {}).get('total_contract_value', 0)
                    if award_amount and award_amount > 0:
                        context['similar_awards'].append({
                            'title': rfp.get('metadata', {}).get('title', ''),
                            'award_amount': float(award_amount),
                            'similarity_score': float(rfp.get('score', 0))
                        })
            except Exception as e:
                self.logger.warning(f"RAG retrieval failed: {e}")
        return context
    def _estimate_base_cost(self, rfp_data: Dict[str, Any], 
                          extracted_requirements: Optional[List[Dict]] = None) -> float:
        """Estimate base cost for the RFP based on requirements and category."""
        category = self._determine_category(rfp_data)
        baseline = self.cost_baselines.get(category, self.cost_baselines['professional_services'])
        # Base cost estimation factors
        base_cost = baseline.base_cost
        # Adjust based on requirements complexity
        complexity_multiplier = 1.0
        if extracted_requirements:
            # Analyze requirements for cost drivers
            total_requirements = len(extracted_requirements)
            mandatory_requirements = len([r for r in extracted_requirements if r.get('mandatory', False)])
            technical_requirements = len([r for r in extracted_requirements if r.get('category') == 'technical'])
            # Complexity factors
            if total_requirements > 15:
                complexity_multiplier *= 1.3
            elif total_requirements > 10:
                complexity_multiplier *= 1.2
            elif total_requirements > 5:
                complexity_multiplier *= 1.1
            if mandatory_requirements > total_requirements * 0.7:
                complexity_multiplier *= 1.15
            if technical_requirements > total_requirements * 0.4:
                complexity_multiplier *= 1.25
        # Adjust based on description keywords
        description = str(rfp_data.get('description', '')).lower()
        title = str(rfp_data.get('title', '')).lower()
        cost_drivers = {
            'emergency': 1.5,
            'urgent': 1.3,
            'complex': 1.4,
            'specialized': 1.3,
            'certified': 1.2,
            'security': 1.25,
            'compliance': 1.15,
            'custom': 1.35,
            '24/7': 1.4,
            'maintenance': 1.1,
            'installation': 1.2
        }
        for keyword, multiplier in cost_drivers.items():
            if keyword in description or keyword in title:
                complexity_multiplier *= multiplier
        # Contract duration adjustment
        if 'description' in rfp_data:
            desc = description
            if any(term in desc for term in ['annual', 'yearly', 'year']):
                complexity_multiplier *= 1.2  # Annual contracts require more resources
            elif any(term in desc for term in ['month', 'months']):
                complexity_multiplier *= 0.9  # Short-term contracts
        estimated_cost = base_cost * complexity_multiplier
        # Apply material and overhead multipliers
        estimated_cost *= baseline.material_multiplier
        estimated_cost *= (1 + baseline.overhead_rate)
        return estimated_cost
    def _calculate_competitive_pricing(self, base_cost: float, historical_context: Dict[str, Any],
                                     strategy: PricingStrategy) -> Tuple[float, float, str]:
        """Calculate competitive pricing based on historical data and strategy."""
        # Start with cost-plus pricing
        cost_plus_price = base_cost * (1 + strategy.base_margin)
        # Adjust based on historical data
        competitive_price = cost_plus_price
        competitive_score = 0.5  # Default score
        pricing_rationale = f"Cost-plus pricing with {strategy.base_margin:.1%} margin"
        # Use NAICS statistics if available
        if historical_context.get('naics_statistics'):
            naics_stats = historical_context['naics_statistics']
            market_median = naics_stats['median']
            # Adjust price relative to market median
            market_adjusted_price = market_median * strategy.competitive_factor
            # Weighted average of cost-plus and market-adjusted pricing
            competitive_price = (cost_plus_price * 0.6) + (market_adjusted_price * 0.4)
            competitive_score = naics_stats.get('confidence', 0.5)
            pricing_rationale = f"Market-adjusted pricing based on {naics_stats['count']} similar contracts"
        # Use category statistics as fallback
        elif historical_context.get('category_statistics'):
            cat_stats = historical_context['category_statistics']
            market_median = cat_stats['median']
            # Adjust price relative to category median
            market_adjusted_price = market_median * strategy.competitive_factor
            # Weighted average
            competitive_price = (cost_plus_price * 0.7) + (market_adjusted_price * 0.3)
            competitive_score = min(0.7, cat_stats['count'] / 50.0)
            pricing_rationale = f"Category-adjusted pricing based on {cat_stats['count']} similar contracts"
        # Use similar awards from RAG if available
        elif historical_context.get('similar_awards'):
            similar_awards = historical_context['similar_awards']
            if similar_awards:
                award_amounts = [award['award_amount'] for award in similar_awards]
                similar_median = statistics.median(award_amounts)
                # Weight by similarity scores
                weighted_amounts = []
                for award in similar_awards:
                    weight = award.get('similarity_score', 0.5)
                    weighted_amounts.extend([award['award_amount']] * int(weight * 10))
                if weighted_amounts:
                    weighted_median = statistics.median(weighted_amounts)
                    market_adjusted_price = weighted_median * strategy.competitive_factor
                    # Weighted average
                    competitive_price = (cost_plus_price * 0.8) + (market_adjusted_price * 0.2)
                    competitive_score = min(0.6, len(similar_awards) / 10.0)
                    pricing_rationale = f"RAG-based pricing using {len(similar_awards)} similar RFPs"
        # Apply risk adjustments
        risk_adjusted_price = competitive_price * (1 + strategy.risk_adjustment)
        # Ensure margin compliance
        minimum_price = base_cost * (1 + strategy.minimum_margin)
        maximum_price = base_cost * (1 + strategy.maximum_margin)
        final_price = max(minimum_price, min(maximum_price, risk_adjusted_price))
        return final_price, competitive_score, pricing_rationale
    def _generate_price_breakdown(self, base_cost: float, final_price: float,
                                category: str) -> Dict[str, float]:
        """Generate detailed price breakdown."""
        baseline = self.cost_baselines.get(category, self.cost_baselines['professional_services'])
        # Calculate component costs
        material_cost = base_cost * 0.4  # 40% materials
        labor_cost = base_cost * 0.45    # 45% labor
        overhead_cost = base_cost * baseline.overhead_rate
        profit = final_price - base_cost - overhead_cost
        breakdown = {
            'base_cost': base_cost,
            'material_cost': material_cost,
            'labor_cost': labor_cost,
            'overhead_cost': overhead_cost,
            'profit': profit,
            'total_price': final_price
        }
        return breakdown
    def _generate_pricing_justification(self, rfp_data: Dict[str, Any], 
                                      pricing_result: PricingResult,
                                      historical_context: Dict[str, Any]) -> str:
        """Generate detailed pricing justification."""
        category = self._determine_category(rfp_data)
        justification_parts = []
        # Project overview
        justification_parts.append(
            f"Pricing Analysis for {rfp_data.get('title', 'RFP')} "
            f"(Category: {category.replace('_', ' ').title()})"
        )
        # Cost basis
        justification_parts.append(
            f"Base cost estimation: ${pricing_result.base_cost:,.2f} based on "
            f"industry standards for {category.replace('_', ' ')} services."
        )
        # Market context
        if historical_context.get('naics_statistics'):
            stats = historical_context['naics_statistics']
            justification_parts.append(
                f"Market analysis: Based on {stats['count']} similar contracts "
                f"(NAICS {rfp_data.get('naics_code', 'N/A')}), typical awards range "
                f"${stats['q25']:,.0f} - ${stats['q75']:,.0f} with median ${stats['median']:,.0f}."
            )
        elif historical_context.get('category_statistics'):
            stats = historical_context['category_statistics']
            justification_parts.append(
                f"Category analysis: Based on {stats['count']} similar {category} contracts, "
                f"typical awards range ${stats['min']:,.0f} - ${stats['max']:,.0f} "
                f"with median ${stats['median']:,.0f}."
            )
        # Pricing strategy
        justification_parts.append(
            f"Strategy: {pricing_result.pricing_strategy.replace('_', ' ').title()} approach "
            f"targeting {pricing_result.margin_percentage:.1f}% margin."
        )
        # Risk factors
        if pricing_result.risk_factors:
            justification_parts.append(
                f"Risk considerations: {', '.join(pricing_result.risk_factors)}."
            )
        # Competitive positioning
        if pricing_result.competitive_score > 0.5:
            justification_parts.append(
                f"Competitive position: High confidence pricing based on extensive market data "
                f"(confidence: {pricing_result.competitive_score:.1%})."
            )
        else:
            justification_parts.append(
                f"Competitive position: Conservative pricing due to limited comparable data "
                f"(confidence: {pricing_result.competitive_score:.1%})."
            )
        # Value proposition
        justification_parts.append(
            f"Our pricing reflects proven expertise, quality delivery, and compliance "
            f"with all requirements while maintaining competitive market positioning."
        )
        return " ".join(justification_parts)
    def generate_pricing(self, rfp_data: Dict[str, Any], 
                        extracted_requirements: Optional[List[Dict]] = None,
                        strategy_name: str = "competitive") -> PricingResult:
        """
        Generate comprehensive pricing for an RFP.
        Args:
            rfp_data: RFP information dictionary
            extracted_requirements: List of extracted requirements from compliance matrix
            strategy_name: Pricing strategy to use
        Returns:
            PricingResult with detailed pricing information
        """
        self.logger.info(f"Generating pricing for RFP: {rfp_data.get('title', 'Unknown')}")
        # Get pricing strategy
        strategy = self.pricing_strategies.get(strategy_name, self.pricing_strategies['competitive'])
        # Determine category and get cost baseline
        category = self._determine_category(rfp_data)
        # Get historical context
        historical_context = self._get_historical_pricing_context(rfp_data)
        # Estimate base cost
        base_cost = self._estimate_base_cost(rfp_data, extracted_requirements)
        # Calculate competitive pricing
        final_price, competitive_score, pricing_rationale = self._calculate_competitive_pricing(
            base_cost, historical_context, strategy
        )
        # Calculate actual margin
        margin_percentage = ((final_price - base_cost) / base_cost) * 100
        # Generate price breakdown
        price_breakdown = self._generate_price_breakdown(base_cost, final_price, category)
        # Identify risk factors
        risk_factors = []
        if margin_percentage < self.minimum_margin * 100:
            risk_factors.append("Below minimum margin threshold")
        if competitive_score < 0.3:
            risk_factors.append("Limited historical data")
        if extracted_requirements and len(extracted_requirements) > 15:
            risk_factors.append("High complexity requirements")
        if any(keyword in str(rfp_data.get('description', '')).lower() 
               for keyword in ['emergency', 'urgent', 'immediate']):
            risk_factors.append("Expedited timeline")
        # Calculate confidence score
        confidence_factors = [
            competitive_score,
            1.0 if margin_percentage >= self.minimum_margin * 100 else 0.5,
            0.8 if extracted_requirements else 0.6,
            0.9 if len(risk_factors) <= 2 else 0.6
        ]
        confidence_score = sum(confidence_factors) / len(confidence_factors)
        # Create pricing result
        result = PricingResult(
            total_price=final_price,
            base_cost=base_cost,
            margin_percentage=margin_percentage,
            pricing_strategy=strategy_name,
            competitive_score=competitive_score,
            risk_factors=risk_factors,
            price_breakdown=price_breakdown,
            justification="",  # Will be filled below
            confidence_score=confidence_score
        )
        # Generate justification
        result.justification = self._generate_pricing_justification(
            rfp_data, result, historical_context
        )
        self.logger.info(f"Generated pricing: ${final_price:,.2f} with {margin_percentage:.1f}% margin")
        return result
    def compare_strategies(self, rfp_data: Dict[str, Any], 
                          extracted_requirements: Optional[List[Dict]] = None) -> Dict[str, PricingResult]:
        """Compare pricing across all available strategies."""
        results = {}
        for strategy_name in self.pricing_strategies.keys():
            try:
                result = self.generate_pricing(rfp_data, extracted_requirements, strategy_name)
                results[strategy_name] = result
            except Exception as e:
                self.logger.error(f"Failed to generate pricing for strategy {strategy_name}: {e}")
        return results
    def export_pricing_analysis(self, rfp_data: Dict[str, Any], 
                               pricing_results: Dict[str, PricingResult],
                               output_format: str = "json") -> str:
        """Export pricing analysis to various formats."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rfp_id = rfp_data.get('rfp_id', 'unknown')
        if output_format.lower() == "json":
            filename = f"pricing_analysis_{rfp_id}_{timestamp}.json"
            filepath = os.path.join(self.pricing_dir, filename)
            # Convert results to serializable format
            export_data = {
                "rfp_info": {
                    "title": rfp_data.get('title', 'Unknown'),
                    "agency": rfp_data.get('agency', 'Unknown'),
                    "rfp_id": rfp_id,
                    "naics_code": rfp_data.get('naics_code', ''),
                    "category": self._determine_category(rfp_data)
                },
                "pricing_strategies": {},
                "recommended_strategy": "",
                "analysis_timestamp": datetime.now().isoformat()
            }
            # Add pricing results
            best_score = 0
            recommended_strategy = ""
            for strategy_name, result in pricing_results.items():
                export_data["pricing_strategies"][strategy_name] = asdict(result)
                # Determine recommended strategy based on confidence score and margin
                score = result.confidence_score * 0.7 + (result.margin_percentage / 100) * 0.3
                if score > best_score:
                    best_score = score
                    recommended_strategy = strategy_name
            export_data["recommended_strategy"] = recommended_strategy
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        self.logger.info(f"Pricing analysis exported to: {filepath}")
        return filepath
def main():
    """Main function for testing pricing engine."""
    import pandas as pd
    print("Testing AI Pricing Engine")
    print("=" * 50)
    try:
        # Initialize pricing engine
        pricing_engine = PricingEngine()
        # Load a sample RFP
        df = pd.read_parquet(os.path.join(pricing_engine.data_dir, 'rfp_master_dataset.parquet'))
        sample_rfp = df[df['description'].notna()].iloc[0].to_dict()
        print(f"Sample RFP: {sample_rfp['title']}")
        print(f"Agency: {sample_rfp['agency']}")
        print(f"NAICS: {sample_rfp.get('naics_code', 'N/A')}")
        # Generate pricing with different strategies
        strategies_results = pricing_engine.compare_strategies(sample_rfp)
        print(f"\nPricing Strategy Comparison:")
        print("-" * 60)
        for strategy_name, result in strategies_results.items():
            print(f"\n{strategy_name.upper()} Strategy:")
            print(f"  Total Price: ${result.total_price:,.2f}")
            print(f"  Base Cost: ${result.base_cost:,.2f}")
            print(f"  Margin: {result.margin_percentage:.1f}%")
            print(f"  Confidence: {result.confidence_score:.1%}")
            print(f"  Risk Factors: {len(result.risk_factors)}")
            if result.risk_factors:
                for risk in result.risk_factors:
                    print(f"    - {risk}")
        # Export analysis
        export_path = pricing_engine.export_pricing_analysis(sample_rfp, strategies_results)
        print(f"\nPricing analysis exported to: {export_path}")
        # Show recommended strategy
        best_strategy = max(strategies_results.items(), 
                          key=lambda x: x[1].confidence_score * 0.7 + (x[1].margin_percentage / 100) * 0.3)
        print(f"\nRecommended Strategy: {best_strategy[0].upper()}")
        print(f"Justification: {best_strategy[1].justification}")
        return True
    except Exception as e:
        print(f"Error testing pricing engine: {e}")
        import traceback
        traceback.print_exc()
        return False
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)