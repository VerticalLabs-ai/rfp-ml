"""
Unit tests for Chat API routes.

Tests the conversational RFP chat functionality including:
- Chat endpoint with RAG integration
- Suggested questions generation
- Chat availability status
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

from app.routes.chat import (
    build_chat_prompt,
    extract_citations,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Citation,
    SUGGESTED_QUESTIONS,
)


class TestBuildChatPrompt:
    """Tests for the build_chat_prompt helper function."""

    def test_basic_prompt_generation(self):
        """Test prompt generation with minimal inputs."""
        prompt = build_chat_prompt(
            question="What is the deadline?",
            context="The deadline is January 15, 2025.",
            history=[],
            rfp_title="IT Services Contract",
            rfp_agency="DoD"
        )

        assert "IT Services Contract" in prompt
        assert "DoD" in prompt
        assert "What is the deadline?" in prompt
        assert "January 15, 2025" in prompt

    def test_prompt_with_history(self):
        """Test prompt includes conversation history."""
        history = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there!"),
        ]

        prompt = build_chat_prompt(
            question="Follow up question",
            context="Some context",
            history=history,
            rfp_title="Test RFP",
            rfp_agency="NASA"
        )

        assert "User: Hello" in prompt
        assert "Assistant: Hi there!" in prompt

    def test_prompt_limits_history(self):
        """Test that prompt only uses last 5 messages from history."""
        # Create 10 messages
        history = [
            ChatMessage(role="user" if i % 2 == 0 else "assistant", content=f"Message {i}")
            for i in range(10)
        ]

        prompt = build_chat_prompt(
            question="Latest question",
            context="Context",
            history=history,
            rfp_title="Test",
            rfp_agency=None
        )

        # Should only contain last 5 messages (5-9)
        assert "Message 5" in prompt
        assert "Message 9" in prompt
        assert "Message 0" not in prompt
        assert "Message 4" not in prompt

    def test_prompt_with_no_agency(self):
        """Test prompt handles None agency gracefully."""
        prompt = build_chat_prompt(
            question="Question",
            context="Context",
            history=[],
            rfp_title="Test RFP",
            rfp_agency=None
        )

        assert "the contracting agency" in prompt


class TestExtractCitations:
    """Tests for the extract_citations helper function."""

    def test_extract_citations_from_documents(self):
        """Test citation extraction from retrieved documents."""
        mock_docs = []
        for i in range(5):
            doc = MagicMock()
            doc.content = f"Document {i} content that is longer than two hundred characters " * 5
            doc.document_id = f"doc-{i}"
            doc.source_dataset = f"Source {i}"
            doc.similarity_score = 0.9 - (i * 0.1)
            mock_docs.append(doc)

        citations = extract_citations(mock_docs, max_citations=3)

        assert len(citations) == 3
        assert citations[0].document_id == "doc-0"
        assert citations[0].similarity_score == 0.9
        assert len(citations[0].content_snippet) <= 203  # 200 + "..."

    def test_extract_citations_handles_missing_attributes(self):
        """Test citation extraction handles documents with missing attributes."""
        mock_doc = MagicMock(spec=[])  # No attributes
        mock_doc.content = "Short content"

        # Manually set hasattr behavior
        del mock_doc.document_id
        del mock_doc.source_dataset
        del mock_doc.similarity_score

        citations = extract_citations([mock_doc])

        assert len(citations) == 1
        assert citations[0].document_id == "unknown"
        assert citations[0].source == "RFP Document"
        assert citations[0].similarity_score == 0.0

    def test_extract_citations_empty_list(self):
        """Test citation extraction with empty document list."""
        citations = extract_citations([])
        assert citations == []


class TestChatModels:
    """Tests for Pydantic chat models."""

    def test_chat_message_creation(self):
        """Test ChatMessage model validation."""
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is None

    def test_chat_request_validation(self):
        """Test ChatRequest model validation."""
        request = ChatRequest(
            message="What is the deadline?",
            history=[]
        )
        assert request.message == "What is the deadline?"
        assert request.history == []

    def test_chat_request_with_history(self):
        """Test ChatRequest with conversation history."""
        history = [
            ChatMessage(role="user", content="Previous question"),
            ChatMessage(role="assistant", content="Previous answer")
        ]
        request = ChatRequest(message="Follow up", history=history)
        assert len(request.history) == 2

    def test_chat_response_creation(self):
        """Test ChatResponse model creation."""
        response = ChatResponse(
            answer="The deadline is next week.",
            citations=[],
            confidence=0.85,
            rfp_id="RFP-001",
            processing_time_ms=150
        )
        assert response.confidence == 0.85
        assert response.processing_time_ms == 150

    def test_citation_model(self):
        """Test Citation model creation."""
        citation = Citation(
            document_id="doc-001",
            content_snippet="Relevant text...",
            source="RFP Documents",
            similarity_score=0.92
        )
        assert citation.similarity_score == 0.92


class TestSuggestedQuestions:
    """Tests for suggested questions functionality."""

    def test_suggested_questions_exist(self):
        """Test that default suggested questions are defined."""
        assert len(SUGGESTED_QUESTIONS) > 0
        assert any("deadline" in q.lower() for q in SUGGESTED_QUESTIONS)
        assert any("requirements" in q.lower() for q in SUGGESTED_QUESTIONS)


class TestChatEndpointUnit:
    """Unit tests for chat endpoint logic (mocked dependencies)."""

    @pytest.fixture
    def mock_rfp(self):
        """Create a mock RFP object."""
        rfp = MagicMock()
        rfp.rfp_id = "RFP-2024-001"
        rfp.title = "IT Services Contract"
        rfp.agency = "Department of Defense"
        rfp.description = "IT infrastructure support services"
        rfp.naics_code = "541512"
        rfp.category = "IT Services"
        rfp.response_deadline = datetime(2025, 1, 15)
        return rfp

    @patch('src.config.llm_adapter.create_llm_interface')
    @patch('src.rag.rag_engine.RAGEngine')
    @pytest.mark.asyncio
    async def test_chat_generates_response(self, mock_rag_cls, mock_llm_factory, mock_rfp):
        """Test that chat endpoint generates a response."""
        # Setup mocks
        mock_rag = MagicMock()
        mock_rag.is_built = True
        mock_context = MagicMock()
        mock_doc = MagicMock()
        mock_doc.content = "Document content"
        mock_doc.document_id = "doc-1"
        mock_doc.source_dataset = "RFP"
        mock_doc.similarity_score = 0.9
        mock_context.retrieved_documents = [mock_doc]
        mock_context.context_text = "Context text"
        mock_rag.generate_context.return_value = mock_context
        mock_rag_cls.return_value = mock_rag

        mock_llm = MagicMock()
        mock_llm.generate_text.return_value = {"content": "Generated answer"}
        mock_llm_factory.return_value = mock_llm

        # Import and call the endpoint function
        from app.routes.chat import chat_with_rfp

        request = ChatRequest(message="What is the deadline?", history=[])
        response = await chat_with_rfp(mock_rfp, request)

        assert response.answer == "Generated answer"
        assert response.rfp_id == "RFP-2024-001"
        assert len(response.citations) > 0

    @patch('src.rag.rag_engine.RAGEngine')
    @pytest.mark.asyncio
    async def test_chat_fallback_on_no_documents(self, mock_rag_cls, mock_rfp):
        """Test chat returns fallback when no documents found."""
        mock_rag = MagicMock()
        mock_rag.is_built = True
        mock_context = MagicMock()
        mock_context.retrieved_documents = []
        mock_rag.generate_context.return_value = mock_context
        mock_rag_cls.return_value = mock_rag

        from app.routes.chat import chat_with_rfp

        request = ChatRequest(message="Unknown question", history=[])
        response = await chat_with_rfp(mock_rfp, request)

        assert "couldn't find" in response.answer.lower() or "couldn't find" in response.answer
        assert response.confidence == 0.0
        assert response.citations == []


class TestChatSuggestionsEndpoint:
    """Tests for chat suggestions endpoint."""

    @pytest.fixture
    def mock_rfp(self):
        """Create a mock RFP for testing suggestions."""
        rfp = MagicMock()
        rfp.rfp_id = "RFP-2024-001"
        rfp.naics_code = "541512"
        rfp.agency = "NASA"
        rfp.response_deadline = datetime(2025, 1, 15)
        rfp.category = "IT Services"
        return rfp

    @pytest.mark.asyncio
    async def test_suggestions_include_generic_questions(self, mock_rfp):
        """Test that suggestions include generic questions."""
        from app.routes.chat import get_chat_suggestions

        result = await get_chat_suggestions(mock_rfp)

        assert "rfp_id" in result
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0
        assert len(result["suggestions"]) <= 10

    @pytest.mark.asyncio
    async def test_suggestions_include_naics_specific(self, mock_rfp):
        """Test that suggestions include NAICS-specific question."""
        from app.routes.chat import get_chat_suggestions

        result = await get_chat_suggestions(mock_rfp)

        # Should have a NAICS-specific suggestion
        naics_suggestions = [s for s in result["suggestions"] if "541512" in s]
        assert len(naics_suggestions) >= 1

    @pytest.mark.asyncio
    async def test_suggestions_include_agency_specific(self, mock_rfp):
        """Test that suggestions include agency-specific question."""
        from app.routes.chat import get_chat_suggestions

        result = await get_chat_suggestions(mock_rfp)

        # Should have an agency-specific suggestion
        agency_suggestions = [s for s in result["suggestions"] if "NASA" in s]
        assert len(agency_suggestions) >= 1


class TestChatStatusEndpoint:
    """Tests for chat status endpoint."""

    @pytest.fixture
    def mock_rfp(self):
        """Create a mock RFP."""
        rfp = MagicMock()
        rfp.rfp_id = "RFP-2024-001"
        return rfp

    @patch('src.config.llm_adapter.create_llm_interface')
    @patch('src.rag.rag_engine.RAGEngine')
    @pytest.mark.asyncio
    async def test_status_when_ready(self, mock_rag_cls, mock_llm_factory, mock_rfp):
        """Test status returns ready when all components available."""
        mock_rag = MagicMock()
        mock_rag.is_built = True
        mock_rag.vector_index.document_ids = ["doc1", "doc2"]
        mock_rag_cls.return_value = mock_rag

        mock_llm = MagicMock()
        mock_llm.get_status.return_value = {"current_backend": "openai"}
        mock_llm_factory.return_value = mock_llm

        from app.routes.chat import get_chat_status

        result = await get_chat_status(mock_rfp)

        assert result["chat_available"] is True
        assert result["rag_status"] == "ready"
        assert result["llm_status"] == "ready"

    @patch('src.rag.rag_engine.RAGEngine')
    @pytest.mark.asyncio
    async def test_status_when_rag_not_built(self, mock_rag_cls, mock_rfp):
        """Test status when RAG index not built."""
        mock_rag = MagicMock()
        mock_rag.is_built = False
        mock_rag_cls.return_value = mock_rag

        from app.routes.chat import get_chat_status

        result = await get_chat_status(mock_rfp)

        assert result["chat_available"] is False
        assert result["rag_status"] == "not_built"
        assert "RAG index not available" in result["message"]
