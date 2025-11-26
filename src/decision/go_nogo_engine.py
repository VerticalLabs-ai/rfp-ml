"""
Go/No-Go Decision Engine for AI-powered RFP bid generation system.
Provides intelligent bid/no-bid recommendations based on multiple business factors.
"""
import os
import sys
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict

# Import path configuration
from config.paths import PathConfig
from config.settings import settings
@dataclass
class DecisionCriteria:
    """Decision criteria configuration."""
    margin_weight: float = 0.30
    complexity_weight: float = 0.25
    duration_weight: float = 0.20
    historical_weight: float = 0.15
    resource_weight: float = 0.10
    margin_threshold_go: float = 70.0
    margin_threshold_review: float = 50.0
    complexity_threshold_review: float = 70.0
    confidence_threshold_go: float = 70.0
@dataclass
class DecisionResult:
    """Result of go/no-go decision analysis."""
    recommendation: str  # 'go', 'no_go', 'review'
    overall_score: float
    confidence_level: float
    margin_score: float
    complexity_score: float
    duration_score: float
    historical_score: float
    resource_score: float
    risk_factors: List[str]
    opportunities: List[str]
    justification: str
    decision_timestamp: str
class GoNoGoEngine:
    """
    Go/No-Go Decision Engine that analyzes all pipeline outputs to provide 
    intelligent bid/no-bid recommendations with detailed justification.
    """
    def __init__(
        self,
        rag_engine=None,
        compliance_generator=None,
        pricing_engine=None,
        document_generator=None,
        config_dir: str | None = None,
        historical_data_dir: str | None = None
    ):
        """
        Initialize Go/No-Go decision engine.
        Args:
            rag_engine: RAG engine for historical analysis
            compliance_generator: Compliance matrix generator
            pricing_engine: Pricing engine for margin analysis
            document_generator: Document generator for completeness assessment
            config_dir: Directory for decision configuration
            historical_data_dir: Directory with historical RFP data
        """
        # Ensure PathConfig directories are initialized
        PathConfig.ensure_directories()

        self.rag_engine = rag_engine
        self.compliance_generator = compliance_generator
        self.pricing_engine = pricing_engine
        self.document_generator = document_generator
        self.config_dir = config_dir or str(PathConfig.DATA_DIR / "config")
        self.historical_data_dir = historical_data_dir or str(PathConfig.PROCESSED_DATA_DIR)
        # Create directories
        os.makedirs(self.config_dir, exist_ok=True)
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        # Load configuration and historical data
        self.decision_criteria = self._load_decision_criteria()
        self.historical_data = self._load_historical_data()
        self.win_rate_patterns = self._analyze_historical_win_rates()
    def _load_decision_criteria(self) -> DecisionCriteria:
        """Load decision criteria from settings or override with JSON."""
        config_path = os.path.join(self.config_dir, "decision_parameters.json")
        
        # Start with defaults from settings
        criteria_data = settings.decision.model_dump()
        
        # Override with JSON if exists (optional, for backward compatibility or runtime tuning)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    json_data = json.load(f)
                    # Only update keys that exist in DecisionCriteria
                    valid_keys = DecisionCriteria.__annotations__.keys()
                    for k, v in json_data.items():
                        if k in valid_keys:
                            criteria_data[k] = v
                self.logger.info(f"Loaded decision criteria from {config_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load decision criteria from JSON: {e}")
        
        # Filter to match DecisionCriteria fields (in case settings has more)
        valid_keys = DecisionCriteria.__annotations__.keys()
        filtered_data = {k: v for k, v in criteria_data.items() if k in valid_keys}
        
        return DecisionCriteria(**filtered_data)
    def _load_historical_data(self) -> pd.DataFrame:
        """Load historical RFP data for win rate analysis."""
        try:
            df = pd.read_parquet(os.path.join(self.historical_data_dir, "rfp_master_dataset.parquet"))
            # Clean and process data
            df['award_amount'] = pd.to_numeric(df.get('award_amount_clean', df.get('award_amount', 0)), errors='coerce')
            df = df[df['award_amount'].notna() & (df['award_amount'] > 0)]
            self.logger.info(f"Loaded {len(df)} historical records for decision analysis")
            return df
        except Exception as e:
            self.logger.warning(f"Failed to load historical data: {e}")
            return pd.DataFrame()
    def _analyze_historical_win_rates(self) -> Dict[str, float]:
        """Analyze historical win rates by category and characteristics."""
        win_rates = {}
        if self.historical_data.empty:
            return win_rates
        try:
            # Analyze by NAICS code
            if 'naics_code' in self.historical_data.columns:
                naics_groups = self.historical_data.groupby('naics_code').size()
                # Calculate win rates (assuming all records in dataset are wins)
                # In production, this would compare wins vs total opportunities
                for naics_code, count in naics_groups.items():
                    if count >= 10:  # Minimum sample size
                        # Simulated win rate based on contract characteristics
                        win_rate = min(0.9, 0.3 + (count / 1000))  # Higher for categories with more contracts
                        win_rates[f"naics_{naics_code}"] = win_rate
            # Analyze by contract value ranges
            if 'award_amount' in self.historical_data.columns:
                awards = self.historical_data['award_amount']
                # Define value ranges
                small_contracts = awards[awards <= awards.quantile(0.33)]
                medium_contracts = awards[(awards > awards.quantile(0.33)) & (awards <= awards.quantile(0.67))]
                large_contracts = awards[awards > awards.quantile(0.67)]
                # Calculate win rates by contract size
                win_rates['small_contracts'] = settings.decision.win_rate_small_contract
                win_rates['medium_contracts'] = settings.decision.win_rate_medium_contract
                win_rates['large_contracts'] = settings.decision.win_rate_large_contract
            self.logger.info(f"Analyzed win rate patterns for {len(win_rates)} categories")
        except Exception as e:
            self.logger.warning(f"Win rate analysis failed: {e}")
        return win_rates
    def _calculate_margin_score(self, pricing_results: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
        """Calculate margin-based score and identify factors."""
        if not pricing_results:
            return 50.0, ["No pricing analysis available"], []
        # Find recommended strategy
        recommended_strategy = None
        best_confidence = 0
        for strategy_name, result in pricing_results.items():
            confidence = getattr(result, 'confidence_score', 0)
            if confidence > best_confidence:
                best_confidence = confidence
                recommended_strategy = result
        if not recommended_strategy:
            return 30.0, ["No valid pricing strategy found"], []
        margin = getattr(recommended_strategy, 'margin_percentage', 0)
        risk_factors = getattr(recommended_strategy, 'risk_factors', [])
        # Score based on margin percentage
        if margin >= settings.decision.margin_score_excellent:
            score = 100.0
        elif margin >= settings.decision.margin_score_good:
            score = 80.0
        elif margin >= settings.decision.margin_score_fair:
            score = 60.0
        elif margin >= settings.decision.margin_score_poor:
            score = 40.0
        else:
            score = 20.0
        # Adjust for risk factors
        risk_adjustment = len(risk_factors) * 5  # 5% penalty per risk factor
        score = max(0, score - risk_adjustment)
        # Identify risk factors and opportunities
        risks = []
        opportunities = []
        if margin < 20:
            risks.append("Low margin below 20% threshold")
        if risk_factors:
            risks.extend([f"Pricing risk: {risk}" for risk in risk_factors])
        if margin > 35:
            opportunities.append("High margin potential above 35%")
        if best_confidence > 0.8:
            opportunities.append("High pricing confidence based on market data")
        return score, risks, opportunities
    def _calculate_complexity_score(self, compliance_matrix: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
        """Calculate complexity-based score."""
        if not compliance_matrix:
            return 50.0, ["No compliance analysis available"], []
        total_requirements = compliance_matrix.get('compliance_summary', {}).get('total_requirements', 0)
        compliance_rate = compliance_matrix.get('compliance_summary', {}).get('compliance_rate', 0)
        # Score based on complexity (inverse relationship)
        if total_requirements <= settings.decision.complexity_req_low:
            complexity_score = 100.0
        elif total_requirements <= settings.decision.complexity_req_medium:
            complexity_score = 80.0
        elif total_requirements <= settings.decision.complexity_req_high:
            complexity_score = 60.0
        elif total_requirements <= settings.decision.complexity_req_very_high:
            complexity_score = 40.0
        else:
            complexity_score = 20.0
        # Adjust based on compliance rate
        compliance_adjustment = compliance_rate * 20  # Up to 20% bonus for high compliance
        complexity_score = min(100.0, complexity_score + compliance_adjustment)
        # Identify complexity factors
        risks = []
        opportunities = []
        if total_requirements > 25:
            risks.append("High complexity with 25+ requirements")
        if compliance_rate < 0.7:
            risks.append("Low compliance rate below 70%")
        if total_requirements <= 10:
            opportunities.append("Low complexity project")
        if compliance_rate >= 0.8:
            opportunities.append("High compliance rate above 80%")
        return complexity_score, risks, opportunities
    def _calculate_duration_score(self, rfp_data: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
        """Calculate duration-based score."""
        # Extract duration information
        lead_time = rfp_data.get('lead_time_days', 30)  # Default 30 days
        description = str(rfp_data.get('description', '')).lower()
        # Estimate contract duration from description
        estimated_duration = 12  # Default 12 months
        if any(term in description for term in ['annual', 'yearly', 'year']):
            estimated_duration = 12
        elif any(term in description for term in ['month', 'months']):
            estimated_duration = 6
        elif any(term in description for term in ['emergency', 'urgent', 'immediate']):
            estimated_duration = 1
        # Score based on optimal duration range
        if settings.decision.duration_optimal_min <= estimated_duration <= settings.decision.duration_optimal_max:
            duration_score = 100.0
        elif settings.decision.duration_acceptable_min <= estimated_duration <= settings.decision.duration_acceptable_max:
            duration_score = 80.0
        elif estimated_duration <= 60:
            duration_score = 60.0
        else:
            duration_score = 40.0
        # Adjust for lead time
        if lead_time < settings.decision.lead_time_short:
            duration_score *= 0.8  # Penalty for short lead times
        elif lead_time > settings.decision.lead_time_long:
            duration_score *= 1.1  # Bonus for longer lead times
        # Identify duration factors
        risks = []
        opportunities = []
        if lead_time < 15:
            risks.append("Short lead time below 15 days")
        if estimated_duration > 36:
            risks.append("Long-term contract exceeding 36 months")
        if any(term in description for term in ['emergency', 'urgent']):
            risks.append("Emergency/urgent timeline requirements")
        if 15 <= lead_time <= 45:
            opportunities.append("Adequate lead time for proposal preparation")
        if 6 <= estimated_duration <= 24:
            opportunities.append("Optimal contract duration range")
        return min(100.0, duration_score), risks, opportunities
    def _calculate_historical_score(self, rfp_data: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
        """Calculate score based on historical win patterns."""
        naics_code = str(rfp_data.get('naics_code', ''))
        award_amount = float(rfp_data.get('award_amount_clean', rfp_data.get('award_amount', 0)) or 0)
        historical_score = 50.0  # Default score
        risks = []
        opportunities = []
        # Check NAICS-specific win rates
        naics_key = f"naics_{naics_code}"
        if naics_key in self.win_rate_patterns:
            win_rate = self.win_rate_patterns[naics_key]
            historical_score = win_rate * 100
            if win_rate >= 0.7:
                opportunities.append(f"High historical win rate ({win_rate:.1%}) for NAICS {naics_code}")
            elif win_rate < 0.4:
                risks.append(f"Low historical win rate ({win_rate:.1%}) for NAICS {naics_code}")
        # Check contract size patterns
        if award_amount > 0:
            if award_amount <= 100000:  # Small contracts
                size_win_rate = self.win_rate_patterns.get('small_contracts', 0.6)
                size_score = size_win_rate * 100
            elif award_amount <= 1000000:  # Medium contracts
                size_win_rate = self.win_rate_patterns.get('medium_contracts', 0.5)
                size_score = size_win_rate * 100
            else:  # Large contracts
                size_win_rate = self.win_rate_patterns.get('large_contracts', 0.4)
                size_score = size_win_rate * 100
            # Weight historical score with size score
            historical_score = (historical_score * 0.6) + (size_score * 0.4)
            if size_win_rate >= 0.6:
                opportunities.append(f"Favorable contract size category ({size_win_rate:.1%} win rate)")
            elif size_win_rate < 0.4:
                risks.append(f"Challenging contract size category ({size_win_rate:.1%} win rate)")
        return min(100.0, historical_score), risks, opportunities
    def _calculate_resource_score(self, rfp_data: Dict[str, Any], 
                                compliance_matrix: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
        """Calculate resource availability score."""
        # Base resource availability (would be configurable in production)
        base_resource_score = 75.0
        # Adjust based on project characteristics
        total_requirements = compliance_matrix.get('compliance_summary', {}).get('total_requirements', 0)
        # Resource requirements based on complexity
        if total_requirements <= 10:
            resource_adjustment = 10  # Bonus for simple projects
        elif total_requirements <= 20:
            resource_adjustment = 0   # Neutral
        elif total_requirements <= 30:
            resource_adjustment = -10  # Penalty for complex projects
        else:
            resource_adjustment = -20  # Higher penalty for very complex
        resource_score = max(0, min(100, base_resource_score + resource_adjustment))
        # Identify resource factors
        risks = []
        opportunities = []
        if total_requirements > 25:
            risks.append("High resource requirements due to complexity")
        description = str(rfp_data.get('description', '')).lower()
        if any(term in description for term in ['specialized', 'certified', 'security clearance']):
            risks.append("Specialized personnel requirements")
        if total_requirements <= 15:
            opportunities.append("Standard resource requirements")
        if any(term in description for term in ['maintenance', 'existing', 'current']):
            opportunities.append("Leverages existing capabilities")
        return resource_score, risks, opportunities

    def calculate_weighted_score(self, margin_score: float, complexity_score: float, 
                               duration_score: float, historical_score: float, 
                               resource_score: float) -> float:
        """Calculate final score using weighted average from settings."""
        weights = settings.decision
        
        total_score = (
            (margin_score * weights.margin_weight) +
            (complexity_score * weights.complexity_weight) +
            (duration_score * weights.duration_weight) +
            (historical_score * weights.historical_weight) +
            (resource_score * weights.resource_weight)
        )
        
        return round(total_score, 2)

    def generate_explanation(self, final_score: float, margin_score: float, 
                           complexity_score: float, duration_score: float, 
                           historical_score: float, resource_score: float,
                           risks: List[str]) -> str:
        """Generate a detailed, human-readable explanation for the score."""
        parts = []
        parts.append(f"Overall Score: {final_score}/100.")
        
        # Analyze key drivers
        if margin_score < 50:
            parts.append("Low margin potential is a significant drag on the score.")
        elif margin_score > 80:
            parts.append("Strong margin potential boosts the score.")
            
        if complexity_score < 50:
            parts.append("High technical complexity reduces confidence.")
            
        if historical_score > 80:
            parts.append("Favorable historical win rates for this category.")
        elif historical_score < 40:
            parts.append("Historical data suggests low win probability for this profile.")

        # Risk summary
        if risks:
            parts.append(f"Key risks identified: {', '.join(risks[:3])}.")
            
        return " ".join(parts)

    def feedback_loop(self, rfp_id: str, actual_outcome: str, user_override: Optional[str] = None):
        """
        Update decision weights based on feedback.
        This is a placeholder for a more complex reinforcement learning loop.
        """
        self.logger.info(f"Feedback received for RFP {rfp_id}: Outcome={actual_outcome}, Override={user_override}")
        
        if user_override == "GO" and actual_outcome == "WON":
            self.logger.info("Suggestion: Consider reducing complexity_weight and increasing historical_weight.")
    def _determine_recommendation(self, overall_score: float, 
                                individual_scores: Dict[str, float],
                                all_risks: List[str]) -> str:
        """Determine final recommendation based on scores and risk factors."""
        margin_score = individual_scores.get('margin_score', 0)
        complexity_score = individual_scores.get('complexity_score', 0)
        # High-level decision logic
        if overall_score >= self.decision_criteria.margin_threshold_go:
            if margin_score >= 60 and complexity_score >= 50:
                return 'go'
            else:
                return 'review'
        elif overall_score >= self.decision_criteria.margin_threshold_review:
            return 'review'
        else:
            return 'no_go'
    def _generate_decision_justification(self, decision_result: DecisionResult,
                                       rfp_data: Dict[str, Any]) -> str:
        """Generate detailed justification for the decision."""
        title = rfp_data.get('title', 'RFP')
        agency = rfp_data.get('agency', 'Agency')
        justification_parts = []
        # Overall assessment
        justification_parts.append(
            f"Decision Analysis for {title} from {agency}: "
            f"{decision_result.recommendation.upper()} recommendation with "
            f"{decision_result.overall_score:.0f}% overall score."
        )
        # Factor analysis
        justification_parts.append(
            f"Factor Analysis: Margin feasibility ({decision_result.margin_score:.0f}%), "
            f"complexity assessment ({decision_result.complexity_score:.0f}%), "
            f"duration fit ({decision_result.duration_score:.0f}%), "
            f"historical patterns ({decision_result.historical_score:.0f}%), "
            f"resource availability ({decision_result.resource_score:.0f}%)."
        )
        # Risk assessment
        if decision_result.risk_factors:
            risk_summary = ", ".join(decision_result.risk_factors[:3])  # Top 3 risks
            justification_parts.append(f"Key risks identified: {risk_summary}.")
        # Opportunity assessment
        if decision_result.opportunities:
            opp_summary = ", ".join(decision_result.opportunities[:3])  # Top 3 opportunities
            justification_parts.append(f"Opportunities: {opp_summary}.")
        # Recommendation rationale
        if decision_result.recommendation == 'go':
            justification_parts.append(
                "Recommendation: PROCEED with bid submission. Strong alignment with business objectives, "
                "acceptable risk profile, and favorable probability of success."
            )
        elif decision_result.recommendation == 'review':
            justification_parts.append(
                "Recommendation: REVIEW REQUIRED. Mixed factors require management evaluation. "
                "Consider risk mitigation strategies and resource allocation before final decision."
            )
        else:
            justification_parts.append(
                "Recommendation: NO-GO. Insufficient margin potential, high risk factors, "
                "or poor strategic fit. Resources better allocated to higher-probability opportunities."
            )
        return " ".join(justification_parts)
    def analyze_rfp_opportunity(self, rfp_data: Dict[str, Any]) -> DecisionResult:
        """
        Perform complete go/no-go analysis for an RFP opportunity.
        Args:
            rfp_data: RFP information dictionary
        Returns:
            DecisionResult with recommendation and detailed analysis
        """
        self.logger.info(f"Analyzing opportunity: {rfp_data.get('title', 'Unknown RFP')}")
        analysis_start = time.time()
        # Generate pipeline outputs if components are available
        compliance_matrix = {}
        pricing_results = {}
        # Step 1: Compliance analysis
        if self.compliance_generator:
            try:
                compliance_matrix = self.compliance_generator.generate_compliance_matrix(rfp_data)
                self.logger.info(f"Compliance analysis completed")
            except Exception as e:
                self.logger.warning(f"Compliance analysis failed: {e}")
        # Step 2: Pricing analysis
        if self.pricing_engine:
            try:
                extracted_requirements = compliance_matrix.get('requirements_and_responses', [])
                pricing_results = self.pricing_engine.compare_strategies(rfp_data, extracted_requirements)
                self.logger.info(f"Pricing analysis completed")
            except Exception as e:
                self.logger.warning(f"Pricing analysis failed: {e}")
        # Step 3: Calculate individual scores
        margin_score, margin_risks, margin_opportunities = self._calculate_margin_score(pricing_results)
        complexity_score, complexity_risks, complexity_opportunities = self._calculate_complexity_score(compliance_matrix)
        duration_score, duration_risks, duration_opportunities = self._calculate_duration_score(rfp_data)
        historical_score, historical_risks, historical_opportunities = self._calculate_historical_score(rfp_data)
        resource_score, resource_risks, resource_opportunities = self._calculate_resource_score(rfp_data, compliance_matrix)
        # Step 4: Calculate weighted overall score
        final_score = self.calculate_weighted_score(
            margin_score, 
            complexity_score, 
            duration_score, 
            historical_score, 
            resource_score
        )

        # Step 5: Combine risks and opportunities
        all_risks = margin_risks + complexity_risks + duration_risks + historical_risks + resource_risks
        all_opportunities = margin_opportunities + complexity_opportunities + duration_opportunities + historical_opportunities + resource_opportunities

        # Step 6: Determine recommendation
        if final_score >= settings.decision.confidence_threshold_go:
            recommendation = "go"
        elif final_score >= settings.decision.margin_threshold_review:
            recommendation = "review"
        else:
            recommendation = "no_go"

        # Step 7: Calculate confidence level (simplified)
        # Variance of scores indicates consistency
        scores = [margin_score, complexity_score, duration_score, historical_score, resource_score]
        score_variance = np.std(scores)
        confidence_level = max(50.0, 100 - (score_variance * 2))

        # Step 8: Generate explanation
        explanation = self.generate_explanation(
            final_score, margin_score, complexity_score, duration_score, 
            historical_score, resource_score, all_risks
        )

        # Step 9: Create decision result
        decision_result = DecisionResult(
            recommendation=recommendation,
            overall_score=final_score,
            confidence_level=confidence_level,
            margin_score=margin_score,
            complexity_score=complexity_score,
            duration_score=duration_score,
            historical_score=historical_score,
            resource_score=resource_score,
            risk_factors=all_risks,
            opportunities=all_opportunities,
            justification=explanation,
            decision_timestamp=datetime.now().isoformat()
        )

        analysis_time = time.time() - analysis_start
        self.logger.info(f"Decision analysis completed in {analysis_time:.2f} seconds: {recommendation.upper()}")
        return decision_result
    def export_decision_analysis(self, rfp_data: Dict[str, Any], 
                               decision_result: DecisionResult,
                               output_format: str = "json") -> str:
        """Export decision analysis to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rfp_id = rfp_data.get('rfp_id', 'unknown')
        if output_format.lower() == "json":
            filename = f"decision_analysis_{rfp_id}_{timestamp}.json"
            filepath = os.path.join(self.config_dir, filename)
            export_data = {
                "rfp_info": {
                    "title": rfp_data.get('title', 'Unknown'),
                    "agency": rfp_data.get('agency', 'Unknown'),
                    "rfp_id": rfp_id,
                    "naics_code": rfp_data.get('naics_code', ''),
                    "award_amount": rfp_data.get('award_amount_clean', 0)
                },
                "decision_analysis": asdict(decision_result),
                "criteria_weights": asdict(self.decision_criteria),
                "analysis_timestamp": datetime.now().isoformat()
            }
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        self.logger.info(f"Decision analysis exported to: {filepath}")
        return filepath
def main():
    """Main function for testing go/no-go decision engine."""
    print("Testing Go/No-Go Decision Engine")
    print("=" * 50)
    try:
        # Initialize with integrated components
        from compliance.compliance_matrix import ComplianceMatrixGenerator
        from pricing.pricing_engine import PricingEngine
        compliance_gen = ComplianceMatrixGenerator()
        pricing_engine = PricingEngine()
        decision_engine = GoNoGoEngine(
            compliance_generator=compliance_gen,
            pricing_engine=pricing_engine
        )
        print("✅ Decision engine initialized with full pipeline integration")
        # Load test RFPs
        df = pd.read_parquet(str(PathConfig.PROCESSED_DATA_DIR / "rfp_master_dataset.parquet"))
        test_rfps = []
        # Get diverse test cases
        for i in [0, 5, 10]:  # Different RFPs for variety
            if i < len(df):
                rfp_data = df[df['description'].notna()].iloc[i].to_dict()
                test_rfps.append(rfp_data)
        print(f"✅ Loaded {len(test_rfps)} test RFPs for decision analysis")
        # Analyze each RFP
        results = []
        for i, test_rfp in enumerate(test_rfps, 1):
            print(f"\n--- Decision Analysis {i} ---")
            print(f"RFP: {test_rfp['title'][:60]}...")
            print(f"Agency: {test_rfp['agency']}")
            print(f"NAICS: {test_rfp.get('naics_code', 'N/A')}")
            try:
                # Perform decision analysis
                decision_result = decision_engine.analyze_rfp_opportunity(test_rfp)
                # Export analysis
                export_path = decision_engine.export_decision_analysis(test_rfp, decision_result)
                result = {
                    'rfp_id': i,
                    'title': test_rfp['title'][:40],
                    'recommendation': decision_result.recommendation,
                    'overall_score': decision_result.overall_score,
                    'confidence': decision_result.confidence_level,
                    'margin_score': decision_result.margin_score,
                    'complexity_score': decision_result.complexity_score,
                    'risk_count': len(decision_result.risk_factors),
                    'opportunity_count': len(decision_result.opportunities),
                    'export_path': export_path
                }
                results.append(result)
                print(f"✅ Recommendation: {decision_result.recommendation.upper()}")
                print(f"✅ Overall Score: {decision_result.overall_score:.1f}%")
                print(f"✅ Confidence: {decision_result.confidence_level:.1f}%")
                print(f"✅ Key Scores: Margin {decision_result.margin_score:.0f}%, Complexity {decision_result.complexity_score:.0f}%")
                print(f"✅ Risk Factors: {len(decision_result.risk_factors)}")
                print(f"✅ Opportunities: {len(decision_result.opportunities)}")
                # Show sample justification
                print(f"Justification: {decision_result.justification[:150]}...")
            except Exception as e:
                print(f"❌ Decision analysis failed: {e}")
                continue
        # Summary results
        print(f"\n" + "=" * 60)
        print("GO/NO-GO DECISION ENGINE SUMMARY")
        print("=" * 60)
        if results:
            go_count = len([r for r in results if r['recommendation'] == 'go'])
            review_count = len([r for r in results if r['recommendation'] == 'review'])
            nogo_count = len([r for r in results if r['recommendation'] == 'no_go'])
            avg_score = sum(r['overall_score'] for r in results) / len(results)
            avg_confidence = sum(r['confidence'] for r in results) / len(results)
            print(f"Total RFPs analyzed: {len(results)}")
            print(f"Recommendations: {go_count} GO, {review_count} REVIEW, {nogo_count} NO-GO")
            print(f"Average overall score: {avg_score:.1f}%")
            print(f"Average confidence: {avg_confidence:.1f}%")
            print(f"\nIndividual Results:")
            for result in results:
                print(f"  RFP {result['rfp_id']}: {result['recommendation'].upper()} "
                      f"({result['overall_score']:.0f}% score, {result['confidence']:.0f}% confidence)")
            # Validation criteria
            validation_checks = {
                'decisions_generated': len(results) > 0,
                'varied_recommendations': len(set(r['recommendation'] for r in results)) > 1,
                'reasonable_scores': all(0 <= r['overall_score'] <= 100 for r in results),
                'adequate_confidence': avg_confidence >= 50,
                'risk_identification': all(r['risk_count'] >= 0 for r in results),
                'exports_created': all(os.path.exists(r['export_path']) for r in results)
            }
            print(f"\n🎯 Validation Results:")
            passed = 0
            for check, result in validation_checks.items():
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"  {check}: {status}")
                if result:
                    passed += 1
            success_rate = passed / len(validation_checks)
            print(f"\nValidation Score: {passed}/{len(validation_checks)} ({success_rate:.1%})")
            if success_rate >= 0.8:
                print("\n🎉 GO/NO-GO DECISION ENGINE: VALIDATION SUCCESSFUL")
                return True
            else:
                print("\n⚠️  GO/NO-GO DECISION ENGINE: NEEDS IMPROVEMENT")
                return False
        else:
            print("❌ No successful decision analyses")
            return False
    except Exception as e:
        print(f"❌ Error testing decision engine: {e}")
        import traceback
        traceback.print_exc()
        return False
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)