"""Tests for background task functions."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.app.services.background_tasks import (
    calculate_pricing_task,
    generate_bid_task,
    get_task_status,
    ingest_documents_task,
    task_status,
)


class TestBackgroundTasks:
    """Test suite for background task functions."""

    def setup_method(self):
        """Clear task status before each test."""
        task_status.clear()

    @pytest.mark.asyncio
    @patch('src.rag.rag_engine.RAGEngine')
    async def test_ingest_documents_task(self, mock_rag_cls):
        """Test document ingestion task."""
        mock_rag = MagicMock()
        mock_rag_cls.return_value = mock_rag

        task_id = "test-task-1"
        await ingest_documents_task(task_id, ["file1.pdf", "file2.pdf"])

        status = get_task_status(task_id)
        assert status is not None
        assert status["status"] == "completed"
        assert status["result"]["files_processed"] == 2
        mock_rag.build_index.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.rfp_processor.processor')
    async def test_generate_bid_task(self, mock_processor):
        """Test bid generation task."""
        mock_processor.generate_bid_document = AsyncMock(return_value={
            "bid_id": "BID-123",
            "rfp_id": "123"
        })

        task_id = "test-task-2"
        rfp_data = {"rfp_id": "123", "title": "Test RFP"}
        await generate_bid_task(task_id, rfp_data)

        status = get_task_status(task_id)
        assert status is not None
        assert status["status"] == "completed"
        assert status["result"]["bid_id"] == "BID-123"

    @pytest.mark.asyncio
    @patch('src.pricing.pricing_engine.PricingEngine')
    async def test_calculate_pricing_task(self, mock_pricing_cls):
        """Test pricing calculation task."""
        mock_pricing = MagicMock()
        mock_pricing_cls.return_value = mock_pricing
        mock_pricing.generate_pricing.return_value = MagicMock(
            total_price=10000,
            margin_percentage=20.0
        )

        task_id = "test-task-3"
        rfp_data = {"rfp_id": "123", "title": "Test RFP"}
        await calculate_pricing_task(task_id, rfp_data)

        status = get_task_status(task_id)
        assert status is not None
        assert status["status"] == "completed"
        assert status["result"]["total_price"] == 10000

    @pytest.mark.asyncio
    @patch('src.rag.rag_engine.RAGEngine', side_effect=Exception("Test error"))
    async def test_task_failure_handling(self, mock_rag_cls):
        """Test that task failures are properly recorded."""
        task_id = "test-task-fail"

        await ingest_documents_task(task_id, ["file.pdf"])

        status = get_task_status(task_id)
        assert status is not None
        assert status["status"] == "failed"
        assert "Test error" in status["error"]

    def test_get_nonexistent_task(self):
        """Test getting status of non-existent task."""
        status = get_task_status("nonexistent-task")
        assert status is None
