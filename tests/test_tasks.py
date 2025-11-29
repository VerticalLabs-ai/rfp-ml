from unittest.mock import MagicMock, patch

import pytest

from src.tasks import calculate_pricing_task, generate_bid_task, ingest_documents_task


class TestCeleryTasks:

    @pytest.fixture(autouse=True)
    def setup_celery(self):
        """Configure Celery to run tasks synchronously (eagerly) for testing."""
        from src.celery_app import celery_app
        celery_app.conf.update(task_always_eager=True)
        yield
        celery_app.conf.update(task_always_eager=False)

    @patch('src.tasks.RAGEngine')
    def test_ingest_documents_task(self, mock_rag_cls):
        """Test document ingestion task."""
        mock_rag = MagicMock()
        mock_rag_cls.return_value = mock_rag

        result = ingest_documents_task.delay(["file1.pdf", "file2.pdf"])

        assert result.successful()
        assert result.result["status"] == "completed"
        assert result.result["files_processed"] == 2
        mock_rag.build_index.assert_called_once()

    def test_generate_bid_task(self):
        """Test bid generation task."""
        rfp_data = {"rfp_id": "123", "title": "Test RFP"}

        # We mock time.sleep to speed up test
        with patch('time.sleep'):
            result = generate_bid_task.delay(rfp_data)

        assert result.successful()
        assert result.result["status"] == "completed"
        assert result.result["rfp_id"] == "123"

    @patch('src.tasks.PricingEngine')
    def test_calculate_pricing_task(self, mock_pricing_cls):
        """Test pricing calculation task."""
        mock_pricing = MagicMock()
        mock_pricing_cls.return_value = mock_pricing
        mock_pricing.generate_pricing.return_value = MagicMock(
            total_price=10000,
            margin_percentage=20.0
        )

        rfp_data = {"rfp_id": "123", "title": "Test RFP"}
        result = calculate_pricing_task.delay(rfp_data)

        assert result.successful()
        assert result.result["status"] == "completed"
        assert result.result["total_price"] == 10000
