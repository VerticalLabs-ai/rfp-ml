from typing import Dict, List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings

class DecisionSettings(BaseSettings):
    """Settings for Go/No-Go Decision Engine."""
    margin_weight: float = 0.30
    complexity_weight: float = 0.25
    duration_weight: float = 0.20
    historical_weight: float = 0.15
    resource_weight: float = 0.10
    
    margin_threshold_go: float = 70.0
    margin_threshold_review: float = 50.0
    complexity_threshold_review: float = 70.0
    confidence_threshold_go: float = 70.0

    # Win Rate Assumptions
    win_rate_small_contract: float = 0.75
    win_rate_medium_contract: float = 0.60
    win_rate_large_contract: float = 0.45

    # Margin Scoring Thresholds
    margin_score_excellent: float = 40.0
    margin_score_good: float = 30.0
    margin_score_fair: float = 20.0
    margin_score_poor: float = 15.0

    # Complexity Scoring
    complexity_req_low: int = 5
    complexity_req_medium: int = 10
    complexity_req_high: int = 20
    complexity_req_very_high: int = 30

    # Duration Scoring
    duration_optimal_min: int = 6
    duration_optimal_max: int = 24
    duration_acceptable_min: int = 3
    duration_acceptable_max: int = 36
    
    lead_time_short: int = 15
    lead_time_long: int = 60

class RAGSettings(BaseSettings):
    """Settings for RAG Engine."""
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 50
    max_text_length: int = 2000
    top_k: int = 5
    similarity_threshold: float = 0.3
    use_gpu: bool = False
    index_type: str = "flat"
    use_tfidf_fallback: bool = True

class Settings(BaseSettings):
    """Global Application Settings."""
    decision: DecisionSettings = Field(default_factory=DecisionSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        extra = "ignore"

settings = Settings()
