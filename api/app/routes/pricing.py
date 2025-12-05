"""
Pricing Workspace API Routes.

Enhanced pricing capabilities with market intelligence, AI recommendations,
and proposal integration.
"""

from datetime import datetime
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.database import PricingResult, RFPOpportunity

router = APIRouter()


# ============= Pydantic Models =============

class LaborLineItem(BaseModel):
    role: str
    hours: float
    ratePerHour: float


class MaterialLineItem(BaseModel):
    description: str
    quantity: float
    unitPrice: float
    unit: str = "each"


class SubcontractorQuote(BaseModel):
    vendor: str
    scope: str
    quoteAmount: float


class OverheadConfig(BaseModel):
    overheadRate: float = 15.0
    gaRate: float = 8.0
    profitMargin: float = 12.0


class CostBreakdownInput(BaseModel):
    labor: List[LaborLineItem]
    materials: List[MaterialLineItem]
    subcontractors: List[SubcontractorQuote]
    overhead: OverheadConfig


class AIRecommendationRequest(BaseModel):
    current_price: Optional[float] = None
    target_win_probability: float = 0.7


class OptimizePriceRequest(BaseModel):
    min_margin: float = 0.10
    max_margin: float = 0.35
    target_win_prob: float = 0.7


# ============= Helper Functions =============

def get_pricing_engine():
    """Get or create pricing engine instance."""
    from src.pricing.pricing_engine import PricingEngine
    return PricingEngine()


def get_rag_engine():
    """Get RAG engine if available."""
    try:
        from src.rag.chroma_rag_engine import get_rag_engine as get_rag
        return get_rag()
    except Exception:
        return None


# ============= Endpoints =============

@router.get("/{rfp_id}/result")
async def get_pricing_result(rfp_id: int, db: Session = Depends(get_db)):
    """Get existing pricing result for an RFP."""
    pricing = db.query(PricingResult).filter(PricingResult.rfp_id == rfp_id).first()
    if not pricing:
        raise HTTPException(status_code=404, detail="Pricing result not found")

    return {
        "id": pricing.id,
        "rfp_id": pricing.rfp_id,
        "total_price": pricing.total_price,
        "base_cost": pricing.base_cost,
        "margin_percentage": pricing.margin_percentage,
        "pricing_strategy": pricing.pricing_strategy,
        "competitive_score": pricing.competitive_score,
        "confidence_score": pricing.confidence_score,
        "price_breakdown": pricing.price_breakdown,
        "risk_factors": pricing.risk_factors,
        "justification": pricing.justification,
        "created_at": pricing.created_at.isoformat() if pricing.created_at else None,
        "updated_at": pricing.updated_at.isoformat() if pricing.updated_at else None,
    }


@router.post("/{rfp_id}/cost-breakdown")
async def save_cost_breakdown(
    rfp_id: int,
    breakdown: CostBreakdownInput,
    db: Session = Depends(get_db)
):
    """Save detailed cost breakdown for an RFP."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Calculate totals
    labor_total = sum(item.hours * item.ratePerHour for item in breakdown.labor)
    materials_total = sum(item.quantity * item.unitPrice for item in breakdown.materials)
    subcontractor_total = sum(item.quoteAmount for item in breakdown.subcontractors)

    direct_costs = labor_total + materials_total + subcontractor_total
    overhead_amount = direct_costs * (breakdown.overhead.overheadRate / 100)
    ga_amount = (direct_costs + overhead_amount) * (breakdown.overhead.gaRate / 100)
    subtotal = direct_costs + overhead_amount + ga_amount
    profit = subtotal * (breakdown.overhead.profitMargin / 100)
    total_price = subtotal + profit

    # Get or create pricing result
    pricing_result = db.query(PricingResult).filter(
        PricingResult.rfp_id == rfp_id
    ).first()

    if not pricing_result:
        pricing_result = PricingResult(rfp_id=rfp_id)
        db.add(pricing_result)

    pricing_result.total_price = total_price
    pricing_result.base_cost = direct_costs
    pricing_result.margin_percentage = breakdown.overhead.profitMargin
    pricing_result.pricing_strategy = "custom"
    pricing_result.confidence_score = 0.8  # Manual entry has moderate confidence
    pricing_result.competitive_score = 0.7
    pricing_result.price_breakdown = {
        "labor": {
            "items": [item.dict() for item in breakdown.labor],
            "total": labor_total
        },
        "materials": {
            "items": [item.dict() for item in breakdown.materials],
            "total": materials_total
        },
        "subcontractors": {
            "items": [item.dict() for item in breakdown.subcontractors],
            "total": subcontractor_total
        },
        "overhead": overhead_amount,
        "ga": ga_amount,
        "profit": profit,
    }
    pricing_result.risk_factors = []
    pricing_result.justification = "Manual cost breakdown entry"

    db.commit()
    db.refresh(pricing_result)

    return {
        "id": pricing_result.id,
        "total_price": total_price,
        "base_cost": direct_costs,
        "margin_percentage": breakdown.overhead.profitMargin,
    }


@router.get("/{rfp_id}/market-intelligence")
async def get_market_intelligence(rfp_id: int, db: Session = Depends(get_db)):
    """Get historical pricing intelligence for an RFP."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    engine = get_pricing_engine()
    rag_engine = get_rag_engine()

    # Get NAICS-based statistics
    naics_stats = None
    if rfp.naics_code:
        naics_stats = engine._get_naics_statistics(rfp.naics_code)

    # Get category statistics
    category = engine._determine_category(rfp.title or "", rfp.description or "")
    category_stats = engine._get_category_statistics(category)

    # Get similar contracts from RAG
    similar_contracts = []
    if rag_engine and rfp.description:
        try:
            results = rag_engine.retrieve(
                f"{rfp.title or ''} {(rfp.description or '')[:500]}",
                top_k=15
            )
            for doc in results:
                award_amount = doc.get('award_amount', 0)
                if award_amount and award_amount > 0:
                    similar_contracts.append({
                        "title": doc.get('title', 'Unknown'),
                        "agency": doc.get('agency', 'Unknown'),
                        "award_amount": award_amount,
                        "date": doc.get('posted_date', 'Unknown'),
                        "similarity": doc.get('similarity', 0),
                        "naics_code": doc.get('naics_code'),
                    })
        except Exception as e:
            print(f"Error retrieving similar contracts: {e}")

    # Calculate award range
    award_range = None
    awards = [c['award_amount'] for c in similar_contracts if c.get('award_amount')]
    if awards:
        award_range = {
            "min": min(awards),
            "p25": float(np.percentile(awards, 25)),
            "median": float(np.median(awards)),
            "p75": float(np.percentile(awards, 75)),
            "max": max(awards),
            "count": len(awards),
        }

    # Get agency-specific insights
    agency_insights = None
    if rfp.agency and engine.historical_data is not None:
        try:
            agency_data = engine.historical_data[
                engine.historical_data['agency'].str.contains(rfp.agency[:20], case=False, na=False)
            ]
            if len(agency_data) > 0:
                agency_insights = {
                    "average_award": float(agency_data['award_amount'].mean()),
                    "contract_count": len(agency_data),
                    "typical_duration": "2-3 years",
                    "budget_peak": "Q4 (September)",
                }
        except Exception:
            pass

    return {
        "naics_stats": naics_stats,
        "category_stats": category_stats,
        "award_range": award_range,
        "similar_contracts": similar_contracts[:10],
        "agency_insights": agency_insights,
        "analysis_date": datetime.now().isoformat(),
    }


@router.get("/trends/{naics_code}")
async def get_pricing_trends(naics_code: str):
    """Get pricing trend data for a NAICS code."""
    engine = get_pricing_engine()

    trends = []
    yoy_change = None

    if engine.historical_data is not None:
        try:
            import pandas as pd

            naics_data = engine.historical_data[
                engine.historical_data['naics_code'].astype(str).str.startswith(naics_code[:4])
            ]

            if 'posted_date' in naics_data.columns and len(naics_data) > 0:
                naics_data = naics_data.copy()
                naics_data['year'] = pd.to_datetime(naics_data['posted_date'], errors='coerce').dt.year
                naics_data = naics_data.dropna(subset=['year'])

                yearly = naics_data.groupby('year').agg({
                    'award_amount': ['mean', 'median', 'count']
                }).reset_index()
                yearly.columns = ['year', 'mean', 'median', 'count']

                trends = [
                    {
                        "year": int(row['year']),
                        "award_amount": {
                            "mean": float(row['mean']),
                            "median": float(row['median']),
                            "count": int(row['count']),
                        }
                    }
                    for _, row in yearly.iterrows()
                ]

                # Calculate YoY change
                if len(yearly) >= 2:
                    sorted_years = yearly.sort_values('year')
                    latest = sorted_years.iloc[-1]['median']
                    previous = sorted_years.iloc[-2]['median']
                    if previous > 0:
                        yoy_change = ((latest - previous) / previous) * 100
        except Exception as e:
            print(f"Error calculating trends: {e}")

    return {
        "naics_code": naics_code,
        "trends": trends,
        "yoy_change": yoy_change,
    }


@router.post("/{rfp_id}/ai-recommendation")
async def get_ai_pricing_recommendation(
    rfp_id: int,
    request: AIRecommendationRequest,
    db: Session = Depends(get_db)
):
    """Get AI-powered pricing recommendation."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    engine = get_pricing_engine()
    rag_engine = get_rag_engine()

    # Generate pricing for all strategies
    strategies = engine.compare_strategies(
        rfp_title=rfp.title or "",
        rfp_description=rfp.description or "",
        naics_code=rfp.naics_code,
        requirements=None,
        compliance_analysis=None,
        rag_engine=rag_engine
    )

    # Get market data
    naics_stats = engine._get_naics_statistics(rfp.naics_code) if rfp.naics_code else None
    market_median = naics_stats['median'] if naics_stats else 200000

    # Determine optimal strategy
    optimal = None
    for name, result in strategies.items():
        if optimal is None or (
            result.confidence_score > optimal[1].confidence_score and
            result.margin_percentage >= 10
        ):
            optimal = (name, result)

    # Generate recommendation reasoning
    reasoning = []
    if optimal:
        if naics_stats:
            reasoning.append(f"Market median for similar contracts: ${naics_stats['median']:,.0f}")

        win_prob = engine.win_probability_model.predict(
            optimal[1].total_price,
            market_median,
            sensitivity=2.5
        )
        reasoning.append(f"Estimated win probability at this price: {win_prob*100:.0f}%")

        competition_level = "Moderate" if win_prob > 0.5 else "High"
        reasoning.append(f"Competition level: {competition_level}")

    # Generate win/price curve
    curve_data = []
    for prob in [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]:
        price = engine.win_probability_model.solve_for_price(prob, market_median)
        curve_data.append({"probability": prob, "price": price})

    # Build strategy response
    strategy_response = {}
    for name, result in strategies.items():
        win_prob = engine.win_probability_model.predict(result.total_price, market_median)
        strategy_response[name] = {
            "price": result.total_price,
            "margin": result.margin_percentage,
            "confidence": result.confidence_score,
            "win_probability": win_prob,
            "risk_level": "Low" if result.confidence_score > 0.7 else "Medium" if result.confidence_score > 0.5 else "High",
        }

    # Calculate PTW
    ptw_result = engine.calculate_price_to_win(
        rfp_title=rfp.title or "",
        rfp_description=rfp.description or "",
        naics_code=rfp.naics_code,
        target_win_probability=request.target_win_probability,
        rag_engine=rag_engine
    )

    return {
        "optimal": {
            "strategy": optimal[0] if optimal else "competitive",
            "price": optimal[1].total_price if optimal else None,
            "confidence": optimal[1].confidence_score if optimal else 0,
            "margin": optimal[1].margin_percentage if optimal else 0,
            "reasoning": reasoning,
        } if optimal else None,
        "strategies": strategy_response,
        "price_to_win": {
            "target_probability": request.target_win_probability,
            "maximum_price": ptw_result.get('maximum_price'),
            "expected_margin": ptw_result.get('margin_at_target'),
        },
        "win_price_curve": curve_data,
        "risk_factors": optimal[1].risk_factors if optimal else [],
    }


@router.get("/{rfp_id}/ptw-analysis")
async def get_ptw_analysis(
    rfp_id: int,
    current_price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Get comprehensive Price-to-Win analysis."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    engine = get_pricing_engine()
    rag_engine = get_rag_engine()

    # Get market data
    naics_stats = engine._get_naics_statistics(rfp.naics_code) if rfp.naics_code else None
    market_median = naics_stats['median'] if naics_stats else 200000

    # Estimate competitor prices
    competitor_low = market_median * 0.82
    competitor_avg = market_median * 1.0
    competitor_high = market_median * 1.30

    # Generate base pricing
    pricing_result = engine.generate_pricing(
        rfp_title=rfp.title or "",
        rfp_description=rfp.description or "",
        naics_code=rfp.naics_code,
        rag_engine=rag_engine
    )
    base_cost = pricing_result.base_cost

    # Minimum viable prices
    minimum_viable = {
        "absolute_floor": base_cost,
        "minimum_margin": base_cost * 1.10,
        "recommended_floor": base_cost * 1.15,
    }

    # Generate margin impact table
    margin_impact = []
    for multiplier in [1.10, 1.15, 1.20, 1.25, 1.30]:
        price_point = base_cost * multiplier
        margin = ((price_point - base_cost) / price_point) * 100
        profit = price_point - base_cost
        win_prob = engine.win_probability_model.predict(price_point, market_median)

        if margin < 12:
            risk = "Thin margin"
        elif win_prob < 0.5:
            risk = "Low win probability"
        elif win_prob > 0.7:
            risk = "Good"
        else:
            risk = "Acceptable"

        margin_impact.append({
            "price": price_point,
            "margin_percent": margin,
            "profit": profit,
            "win_probability": win_prob,
            "risk_assessment": risk,
        })

    # Calculate risk score
    risk_score = 0
    risk_factors = []

    if current_price:
        win_prob = engine.win_probability_model.predict(current_price, market_median)
        margin = ((current_price - base_cost) / current_price) * 100 if current_price > 0 else 0

        if win_prob < 0.5:
            risk_score += 30
            risk_factors.append("Low win probability at current price")

        if margin < 15:
            risk_score += 20
            risk_factors.append("Margin below recommended threshold")

        if current_price > competitor_high:
            risk_score += 25
            risk_factors.append("Price above expected competitor range")

    return {
        "competitor_estimates": {
            "expected_bidders": "4-6",
            "low_bidder": competitor_low,
            "average": competitor_avg,
            "high_bidder": competitor_high,
        },
        "minimum_viable": minimum_viable,
        "margin_impact_table": margin_impact,
        "risk_assessment": {
            "score": risk_score,
            "level": "Low" if risk_score < 30 else "Medium" if risk_score < 60 else "High",
            "factors": risk_factors,
        },
        "current_position": {
            "price": current_price,
            "vs_market": ((current_price - market_median) / market_median * 100) if current_price else None,
        }
    }


@router.post("/{rfp_id}/narrative")
async def generate_pricing_narrative(rfp_id: int, db: Session = Depends(get_db)):
    """Generate pricing narrative for proposal inclusion."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    pricing = db.query(PricingResult).filter(PricingResult.rfp_id == rfp_id).first()

    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    if not pricing:
        raise HTTPException(status_code=404, detail="Pricing result not found. Please save pricing first.")

    breakdown = pricing.price_breakdown or {}

    narrative = f"""## Pricing Summary

**{rfp.title}**

### Total Proposed Price: ${pricing.total_price:,.2f}

Our pricing reflects a comprehensive understanding of the project requirements and represents best value to the Government while ensuring successful project delivery.

### Cost Breakdown

**Direct Labor**: ${breakdown.get('labor', {}).get('total', 0):,.2f}
Our labor estimate is based on detailed analysis of each task requirement, utilizing appropriate labor categories with rates that reflect current market conditions.

**Materials & Equipment**: ${breakdown.get('materials', {}).get('total', 0):,.2f}
Material costs are based on current vendor quotes and include appropriate contingency for market fluctuations.

**Subcontractor Costs**: ${breakdown.get('subcontractors', {}).get('total', 0):,.2f}
Subcontractor pricing reflects competitive quotes from qualified vendors with proven track records in their respective specialties.

**Overhead & G&A**: ${(breakdown.get('overhead', 0) + breakdown.get('ga', 0)):,.2f}
Indirect rates are current, audited rates applied consistently across all contracts.

**Profit**: ${breakdown.get('profit', 0):,.2f}
Our profit margin of {pricing.margin_percentage:.1f}% is reasonable and reflects the risk profile of this requirement.

### Value Proposition

This pricing represents competitive value based on analysis of {pricing.confidence_score*100:.0f}% confidence market data. We are committed to delivering exceptional results within this budget framework.
"""

    return {"narrative": narrative, "generated_at": datetime.now().isoformat()}


@router.post("/{rfp_id}/basis-of-estimate")
async def generate_basis_of_estimate(rfp_id: int, db: Session = Depends(get_db)):
    """Generate Basis of Estimate (BOE) document."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    pricing = db.query(PricingResult).filter(PricingResult.rfp_id == rfp_id).first()

    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    if not pricing:
        raise HTTPException(status_code=404, detail="Pricing result not found. Please save pricing first.")

    breakdown = pricing.price_breakdown or {}
    labor_items = breakdown.get('labor', {}).get('items', [])

    boe = {
        "document_title": f"Basis of Estimate - {rfp.title}",
        "rfp_number": rfp.rfp_number,
        "date_prepared": datetime.now().isoformat(),
        "sections": [
            {
                "title": "1. Introduction",
                "content": f"This Basis of Estimate (BOE) documents the methodology and assumptions used to develop the cost estimate for {rfp.title}."
            },
            {
                "title": "2. Labor Estimate Methodology",
                "content": "Labor hours were estimated using analogous estimation based on similar historical projects, supplemented by bottom-up estimates for unique requirements.",
                "details": [
                    {
                        "role": item.get('role'),
                        "hours": item.get('hours'),
                        "rate": item.get('ratePerHour'),
                        "basis": f"Based on historical data from similar {rfp.naics_code or 'IT'} projects"
                    }
                    for item in labor_items
                ]
            },
            {
                "title": "3. Material/ODC Methodology",
                "content": "Material and Other Direct Costs are based on current vendor quotes and catalog pricing."
            },
            {
                "title": "4. Indirect Rates",
                "content": f"Overhead: {(breakdown.get('overhead', 0) / pricing.base_cost * 100) if pricing.base_cost else 0:.1f}%\nG&A: {(breakdown.get('ga', 0) / pricing.base_cost * 100) if pricing.base_cost else 0:.1f}%"
            },
            {
                "title": "5. Assumptions and Exclusions",
                "content": "Key assumptions: Government-furnished equipment as specified, standard work hours, no travel beyond PWS requirements."
            },
            {
                "title": "6. Risk Assessment",
                "content": f"Risk factors identified: {', '.join(pricing.risk_factors) if pricing.risk_factors else 'None significant'}"
            }
        ],
        "total_price": pricing.total_price,
        "confidence_level": f"{pricing.confidence_score*100:.0f}%"
    }

    return boe


@router.post("/train-model")
async def train_pricing_model():
    """Train/retrain the ML pricing model on historical data."""
    try:
        from src.pricing.pricing_ml import PricingMLModel

        engine = get_pricing_engine()
        if engine.historical_data is None:
            raise HTTPException(status_code=500, detail="No historical data available")

        model = PricingMLModel()
        results = model.train(engine.historical_data)

        return {"status": "trained", "metrics": results}
    except ImportError:
        raise HTTPException(status_code=501, detail="ML model not yet implemented")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{rfp_id}/ml-prediction")
async def get_ml_price_prediction(rfp_id: int, db: Session = Depends(get_db)):
    """Get ML-based price prediction for an RFP."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    try:
        from src.pricing.pricing_ml import PricingMLModel

        model = PricingMLModel()
        prediction = model.predict(
            naics_code=rfp.naics_code or "541511",
            agency=rfp.agency or "Unknown",
            description_length=len(rfp.description or ""),
            requirement_count=10,
        )

        return {
            "predicted_price": prediction.predicted_price,
            "confidence_interval": {
                "lower": prediction.confidence_interval[0],
                "upper": prediction.confidence_interval[1],
            },
            "model_confidence": prediction.model_confidence,
            "feature_importance": prediction.feature_importance,
        }
    except ImportError:
        # Fallback to simple prediction if ML model not available
        engine = get_pricing_engine()
        result = engine.generate_pricing(
            rfp_title=rfp.title or "",
            rfp_description=rfp.description or "",
            naics_code=rfp.naics_code,
        )
        return {
            "predicted_price": result.total_price,
            "confidence_interval": {
                "lower": result.total_price * 0.85,
                "upper": result.total_price * 1.15,
            },
            "model_confidence": result.confidence_score,
            "feature_importance": {},
        }


@router.post("/{rfp_id}/optimize")
async def optimize_price(
    rfp_id: int,
    request: OptimizePriceRequest,
    db: Session = Depends(get_db)
):
    """Find optimal price balancing margin and win probability."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    pricing = db.query(PricingResult).filter(PricingResult.rfp_id == rfp_id).first()

    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    engine = get_pricing_engine()

    # Get base cost
    if pricing:
        base_cost = pricing.base_cost
    else:
        result = engine.generate_pricing(
            rfp_title=rfp.title or "",
            rfp_description=rfp.description or "",
            naics_code=rfp.naics_code,
        )
        base_cost = result.base_cost

    # Get market median
    naics_stats = engine._get_naics_statistics(rfp.naics_code) if rfp.naics_code else None
    market_median = naics_stats['median'] if naics_stats else base_cost * 1.2

    # Find optimal price
    best_score = -1
    best_price = base_cost * (1 + request.min_margin)
    best_margin = request.min_margin
    best_win_prob = 0.5

    for margin in [x / 100 for x in range(int(request.min_margin * 100), int(request.max_margin * 100) + 1)]:
        price = base_cost * (1 + margin)
        win_prob = engine.win_probability_model.predict(price, market_median)

        if win_prob >= request.target_win_prob:
            score = margin * 0.6 + win_prob * 0.4
        else:
            score = win_prob

        if score > best_score:
            best_score = score
            best_price = price
            best_margin = margin
            best_win_prob = win_prob

    return {
        "optimal_price": best_price,
        "margin": best_margin,
        "win_probability": best_win_prob,
        "expected_profit": best_price - base_cost,
        "optimization_score": best_score,
    }


# ============= Default Labor Rates =============

@router.get("/labor-rates")
async def get_default_labor_rates():
    """Get default labor rates by role."""
    return {
        "Project Manager": 150,
        "Senior Developer": 175,
        "Developer": 125,
        "Junior Developer": 85,
        "Designer": 135,
        "QA Engineer": 110,
        "DevOps Engineer": 160,
        "Technical Writer": 95,
        "Subject Matter Expert": 200,
        "Security Specialist": 185,
        "Data Analyst": 130,
        "Business Analyst": 140,
    }
