import pytest
from unittest.mock import MagicMock, patch
from src.decision.go_nogo_engine import GoNoGoEngine, DecisionResult
from src.config.settings import settings

class TestDynamicGoNoGo:
    
    @pytest.fixture
    def engine(self):
        return GoNoGoEngine()

    def test_weighted_score_calculation(self, engine):
        """Test that weighted score is calculated correctly based on settings."""
        # Mock settings
        settings.decision.margin_weight = 0.3
        settings.decision.complexity_weight = 0.3
        settings.decision.duration_weight = 0.2
        settings.decision.historical_weight = 0.1
        settings.decision.resource_weight = 0.1
        
        score = engine.calculate_weighted_score(
            margin_score=100,    # 30
            complexity_score=50, # 15
            duration_score=100,  # 20
            historical_score=50, # 5
            resource_score=50    # 5
        )
        
        expected = 30 + 15 + 20 + 5 + 5
        assert score == expected
        assert score == 75.0

    def test_explainability(self, engine):
        """Test that explanation contains key drivers."""
        explanation = engine.generate_explanation(
            final_score=40.0,
            margin_score=20.0,
            complexity_score=40.0,
            duration_score=60.0,
            historical_score=50.0,
            resource_score=50.0,
            risks=["Risk A"]
        )
        
        assert "Overall Score: 40.0/100" in explanation
        assert "Low margin potential" in explanation
        assert "High technical complexity" in explanation
        assert "Risk A" in explanation

    def test_feedback_loop(self, engine):
        """Test feedback loop logging."""
        with patch.object(engine.logger, 'info') as mock_log:
            engine.feedback_loop("RFP-123", "WON", "GO")
            mock_log.assert_any_call("Feedback received for RFP RFP-123: Outcome=WON, Override=GO")
            mock_log.assert_any_call("Suggestion: Consider reducing complexity_weight and increasing historical_weight.")
