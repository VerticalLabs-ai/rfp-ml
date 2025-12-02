"""
Discovery API endpoints with Natural Language Search.

Provides endpoints for:
- Semantic search across RFPs using RAG
- Natural language query parsing
- Advanced filtering with extracted parameters
"""
import logging
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.dependencies import DBDep

logger = logging.getLogger(__name__)

# Lazy singleton instances for RAG engine and NL parser
_rag_engine_instance = None
_nl_parser_instance = None

router = APIRouter()


class SearchRequest(BaseModel):
    """Request for semantic search."""

    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    search_type: Literal["hybrid", "semantic", "keyword"] = Field(
        default="hybrid",
        description="Search type: semantic (RAG), keyword (TF-IDF), or hybrid"
    )
    top_k: int = Field(default=20, ge=1, le=100, description="Number of results to return")
    skip: int = Field(default=0, ge=0, description="Number of results to skip")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum relevance score")
    filters: dict[str, Any] = Field(default_factory=dict, description="Additional filters")


class SearchResultItem(BaseModel):
    """Individual search result."""

    rfp_id: str
    title: str
    agency: str | None
    description: str | None
    naics_code: str | None
    category: str | None
    award_amount: float | None
    response_deadline: str | None
    triage_score: float | None
    relevance_score: float
    match_highlights: list[str] = Field(default_factory=list)


class ParsedQueryInfo(BaseModel):
    """Information about how the query was parsed."""

    original_query: str
    semantic_query: str
    extracted_filters: dict[str, Any]
    keywords: list[str]
    intent: str
    confidence: float


class SearchResponse(BaseModel):
    """Response for search endpoint."""

    results: list[SearchResultItem]
    total: int
    query_info: ParsedQueryInfo
    search_type: str


class SearchSuggestionsResponse(BaseModel):
    """Response for search suggestions."""

    suggestions: list[str]
    recent_searches: list[str]
    popular_categories: list[str]


def get_rag_engine():
    """Get ChromaDB RAG engine singleton instance."""
    global _rag_engine_instance
    if _rag_engine_instance is not None:
        return _rag_engine_instance
    try:
        from src.rag.chroma_rag_engine import get_rag_engine as get_chroma_engine
        _rag_engine_instance = get_chroma_engine()
        return _rag_engine_instance
    except Exception:
        logger.exception("Failed to initialize RAG engine")
        return None


def get_nl_parser():
    """Get NL query parser lazy singleton instance."""
    global _nl_parser_instance
    if _nl_parser_instance is not None:
        return _nl_parser_instance
    try:
        from src.discovery.nl_parser import get_nl_parser as get_parser
        _nl_parser_instance = get_parser()
        return _nl_parser_instance
    except Exception:
        logger.exception("Failed to initialize NL parser")
        return None


@dataclass
class ParsedQueryFallback:
    """Fallback parsed query when parser is unavailable."""
    original_query: str
    semantic_query: str
    extracted_filters: dict
    keywords: list
    intent: str
    confidence: float


@router.post("/search", response_model=SearchResponse)
async def search_rfps(
    request: SearchRequest,
    db: DBDep,
) -> SearchResponse:
    """
    Search RFPs using natural language.

    Supports:
    - Semantic search using RAG embeddings
    - Natural language query parsing
    - Automatic filter extraction (location, agency, NAICS, amount)
    - Hybrid search combining semantic + keyword matching

    Example queries:
    - "Construction contracts in California"
    - "IT services for DOD over $1M"
    - "Small business set-aside cybersecurity"
    """
    from app.models.database import RFPOpportunity

    # Parse the natural language query
    parser = get_nl_parser()
    if parser:
        parsed = parser.parse(request.query)
    else:
        # Fallback if parser unavailable
        parsed = ParsedQueryFallback(
            original_query=request.query,
            semantic_query=request.query,
            extracted_filters={},
            keywords=request.query.split(),
            intent='search',
            confidence=0.5
        )

    # Combine parsed filters with explicit filters
    combined_filters = {**parsed.extracted_filters, **request.filters}

    results: list[SearchResultItem] = []
    total = 0

    # Try RAG-based semantic search first
    rag_engine = get_rag_engine()
    rfp_id_scores: dict[str, float] = {}

    if rag_engine and rag_engine.is_built and request.search_type in ("semantic", "hybrid"):
        try:
            # Retrieve relevant documents from RAG
            rag_results = rag_engine.retrieve(
                query=parsed.semantic_query,
                k=request.top_k * 2  # Get more for filtering
            )

            # Extract RFP IDs and scores from RAG results
            for result in rag_results:
                metadata = result.get('metadata', {})
                rfp_id = metadata.get('rfp_id') or metadata.get('solicitation_number')
                score = result.get('similarity_score', result.get('score', 0.5))

                if rfp_id and score >= request.min_score:
                    if rfp_id not in rfp_id_scores or score > rfp_id_scores[rfp_id]:
                        rfp_id_scores[rfp_id] = score

        except Exception:
            logger.exception("RAG search failed, falling back to keyword")

    # If no RAG results or keyword search requested, do database search
    if not rfp_id_scores or request.search_type in ("keyword", "hybrid"):
        try:
            # Build database query with filters
            query = db.query(RFPOpportunity)

            # Apply text search on title and description
            if parsed.semantic_query:
                search_term = f"%{parsed.semantic_query}%"
                query = query.filter(
                    (RFPOpportunity.title.ilike(search_term)) |
                    (RFPOpportunity.description.ilike(search_term))
                )

            # Apply extracted filters
            if combined_filters.get("location"):
                location = combined_filters["location"]
                query = query.filter(
                    (RFPOpportunity.rfp_metadata["pop_state"].astext == location) |
                    (RFPOpportunity.rfp_metadata["location"].astext.ilike(f"%{location}%"))
                )

            if combined_filters.get("agency"):
                agency = combined_filters["agency"]
                query = query.filter(RFPOpportunity.agency.ilike(f"%{agency}%"))

            if combined_filters.get("naics_code"):
                naics = combined_filters["naics_code"]
                query = query.filter(RFPOpportunity.naics_code.startswith(naics))

            if combined_filters.get("amount_range"):
                amount_range = combined_filters["amount_range"]
                if "min" in amount_range:
                    query = query.filter(RFPOpportunity.award_amount >= amount_range["min"])
                if "max" in amount_range:
                    query = query.filter(RFPOpportunity.award_amount <= amount_range["max"])

            if combined_filters.get("category"):
                query = query.filter(RFPOpportunity.category == combined_filters["category"])

            if combined_filters.get("min_triage_score"):
                query = query.filter(RFPOpportunity.triage_score >= combined_filters["min_triage_score"])

            # Get keyword results
            keyword_results = query.order_by(RFPOpportunity.triage_score.desc().nullslast()).limit(request.top_k * 2).all()

            for rfp in keyword_results:
                # Assign keyword match score (lower than semantic)
                keyword_score = 0.4  # Base keyword match score
                if rfp.triage_score:
                    keyword_score += 0.1 * (rfp.triage_score / 100)

                if rfp.rfp_id not in rfp_id_scores:
                    rfp_id_scores[rfp.rfp_id] = keyword_score
                elif request.search_type == "hybrid":
                    # Boost score for hybrid matches
                    rfp_id_scores[rfp.rfp_id] = min(1.0, rfp_id_scores[rfp.rfp_id] + 0.2)

        except Exception:
            logger.exception("Database search failed")

    # Fetch full RFP data for matched IDs
    if rfp_id_scores:
        matched_rfps = db.query(RFPOpportunity).filter(
            RFPOpportunity.rfp_id.in_(rfp_id_scores.keys())
        ).all()

        # Build results with scores
        for rfp in matched_rfps:
            score = rfp_id_scores.get(rfp.rfp_id, 0.0)
            if score >= request.min_score:
                # Generate match highlights
                highlights = _generate_highlights(
                    rfp.title,
                    rfp.description,
                    parsed.keywords
                )

                results.append(SearchResultItem(
                    rfp_id=rfp.rfp_id,
                    title=rfp.title or "Untitled",
                    agency=rfp.agency,
                    description=rfp.description[:500] if rfp.description else None,
                    naics_code=rfp.naics_code,
                    category=rfp.category,
                    award_amount=rfp.award_amount,
                    response_deadline=rfp.response_deadline.isoformat() if rfp.response_deadline else None,
                    triage_score=rfp.triage_score,
                    relevance_score=round(score, 3),
                    match_highlights=highlights,
                ))

        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)

    # Apply pagination
    total = len(results)
    results = results[request.skip:request.skip + request.top_k]

    return SearchResponse(
        results=results,
        total=total,
        query_info=ParsedQueryInfo(
            original_query=parsed.original_query,
            semantic_query=parsed.semantic_query,
            extracted_filters=parsed.extracted_filters,
            keywords=parsed.keywords,
            intent=parsed.intent,
            confidence=parsed.confidence,
        ),
        search_type=request.search_type,
    )


@router.get("/search/suggestions")
async def get_search_suggestions(
    q: Annotated[str, Query(min_length=1, max_length=100)] = "",
) -> SearchSuggestionsResponse:
    """
    Get search suggestions based on partial query.

    Returns:
    - Auto-complete suggestions
    - Recent searches (if user tracking enabled)
    - Popular categories
    """
    suggestions: list[str] = []

    if q and len(q) >= 2:
        # Generate suggestions based on query prefix
        base_suggestions = [
            f"{q} contracts",
            f"{q} services",
            f"{q} in California",
            f"{q} for DOD",
            f"{q} small business",
        ]
        suggestions = base_suggestions[:5]

    # Popular categories (static for now)
    popular_categories = [
        "IT Services",
        "Construction",
        "Professional Services",
        "Healthcare",
        "Cybersecurity",
        "Logistics",
        "Engineering",
        "Research & Development",
    ]

    return SearchSuggestionsResponse(
        suggestions=suggestions,
        recent_searches=[],  # Would require user session tracking
        popular_categories=popular_categories,
    )


@router.get("/search/parse")
async def parse_query(
    q: Annotated[str, Query(min_length=1, max_length=500)],
) -> ParsedQueryInfo:
    """
    Parse a natural language query without searching.

    Useful for:
    - Previewing filter extraction
    - Understanding query interpretation
    - Debugging search behavior
    """
    parser = get_nl_parser()
    if not parser:
        raise HTTPException(
            status_code=503,
            detail="Query parser not available"
        )

    try:
        parsed = parser.parse(q)
    except Exception as e:
        logger.exception("Failed to parse query")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse query: {e}"
        ) from e

    return ParsedQueryInfo(
        original_query=parsed.original_query,
        semantic_query=parsed.semantic_query,
        extracted_filters=parsed.extracted_filters,
        keywords=parsed.keywords,
        intent=parsed.intent,
        confidence=parsed.confidence,
    )


def _generate_highlights(
    title: str | None,
    description: str | None,
    keywords: list[str],
    max_highlights: int = 3
) -> list[str]:
    """Generate highlighted snippets showing keyword matches."""
    highlights = []

    if not keywords:
        return highlights

    text = f"{title or ''} {description or ''}"
    if not text.strip():
        return highlights

    # Find sentences containing keywords
    sentences = text.replace('\n', ' ').split('.')

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 20:
            continue

        sentence_lower = sentence.lower()
        for keyword in keywords:
            if keyword.lower() in sentence_lower:
                # Truncate long sentences
                if len(sentence) > 200:
                    # Find keyword position and extract context
                    pos = sentence_lower.find(keyword.lower())
                    start = max(0, pos - 80)
                    end = min(len(sentence), pos + len(keyword) + 80)
                    snippet = sentence[start:end]
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(sentence):
                        snippet = snippet + "..."
                    highlights.append(snippet)
                else:
                    highlights.append(sentence)
                break

        if len(highlights) >= max_highlights:
            break

    return highlights
