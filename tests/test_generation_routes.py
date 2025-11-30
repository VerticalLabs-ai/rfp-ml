"""
Unit tests for AI Writer / Generation API routes.

Tests the proposal generation functionality including:
- Writer slash commands
- Content expansion and summarization
- Content improvement
- Style upload
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.routes.generation import (
    WriterCommand,
    WRITER_COMMANDS,
    AIWriterRequest,
    AIWriterResponse,
    RefineRequest,
    ExpandRequest,
    SummarizeRequest,
    _generate_suggestions,
    _generate_fallback_content,
)


class TestWriterCommands:
    """Tests for WriterCommand enum and configuration."""

    def test_all_commands_have_config(self):
        """Test that all WriterCommand values have corresponding config."""
        for cmd in WriterCommand:
            assert cmd in WRITER_COMMANDS, f"Missing config for {cmd}"

    def test_command_config_structure(self):
        """Test that command configs have required fields."""
        required_fields = ["name", "description", "prompt_template", "default_max_words"]

        for cmd, config in WRITER_COMMANDS.items():
            for field in required_fields:
                assert field in config, f"Missing {field} in {cmd} config"

    def test_prompt_templates_have_placeholders(self):
        """Test that prompt templates include required placeholders."""
        required_placeholders = ["{rfp_title}", "{agency}", "{max_words}"]

        for cmd, config in WRITER_COMMANDS.items():
            template = config["prompt_template"]
            for placeholder in required_placeholders:
                assert placeholder in template, f"Missing {placeholder} in {cmd} template"

    def test_default_max_words_reasonable(self):
        """Test that default max words are within reasonable range."""
        for cmd, config in WRITER_COMMANDS.items():
            max_words = config["default_max_words"]
            assert 100 <= max_words <= 1000, f"Unreasonable max_words for {cmd}: {max_words}"


class TestAIWriterModels:
    """Tests for AI Writer Pydantic models."""

    def test_ai_writer_request_basic(self):
        """Test basic AIWriterRequest creation."""
        request = AIWriterRequest(command=WriterCommand.EXECUTIVE_SUMMARY)
        assert request.command == WriterCommand.EXECUTIVE_SUMMARY
        assert request.context == ""
        assert request.tone == "professional"
        assert request.include_citations is False

    def test_ai_writer_request_with_options(self):
        """Test AIWriterRequest with all options."""
        request = AIWriterRequest(
            command=WriterCommand.TECHNICAL_APPROACH,
            context="Focus on cloud migration",
            max_words=500,
            tone="formal",
            include_citations=True
        )
        assert request.max_words == 500
        assert request.tone == "formal"
        assert request.include_citations is True

    def test_ai_writer_response_model(self):
        """Test AIWriterResponse model."""
        response = AIWriterResponse(
            command="executive-summary",
            section_name="Executive Summary",
            content="Generated content here.",
            word_count=150,
            confidence_score=0.85,
            generation_method="llm",
            rfp_id="RFP-001",
            suggestions=["Try /technical-approach next"]
        )
        assert response.word_count == 150
        assert len(response.suggestions) == 1

    def test_refine_request_validation(self):
        """Test RefineRequest validation."""
        request = RefineRequest(
            text="Original text to refine",
            instruction="Make it more persuasive",
            context="Government proposal"
        )
        assert request.text == "Original text to refine"
        assert request.instruction == "Make it more persuasive"

    def test_expand_request_model(self):
        """Test ExpandRequest model."""
        request = ExpandRequest(
            text="Brief outline of approach",
            expansion_type="detailed",
            target_length=300
        )
        assert request.expansion_type == "detailed"
        assert request.target_length == 300

    def test_summarize_request_model(self):
        """Test SummarizeRequest model."""
        request = SummarizeRequest(
            text="Long content to summarize " * 20,
            summary_type="executive",
            max_length=150
        )
        assert request.summary_type == "executive"


class TestGenerateSuggestions:
    """Tests for suggestion generation helper."""

    @pytest.fixture
    def mock_rfp(self):
        """Create mock RFP."""
        rfp = MagicMock()
        rfp.title = "IT Services"
        rfp.agency = "DoD"
        return rfp

    def test_executive_summary_suggestions(self, mock_rfp):
        """Test suggestions after executive summary generation."""
        suggestions = _generate_suggestions(WriterCommand.EXECUTIVE_SUMMARY, mock_rfp)
        assert len(suggestions) > 0
        assert any("/technical-approach" in s for s in suggestions)

    def test_technical_approach_suggestions(self, mock_rfp):
        """Test suggestions after technical approach generation."""
        suggestions = _generate_suggestions(WriterCommand.TECHNICAL_APPROACH, mock_rfp)
        assert len(suggestions) > 0
        assert any("/quality-control" in s or "/risk-mitigation" in s for s in suggestions)

    def test_unknown_command_default_suggestion(self, mock_rfp):
        """Test default suggestion for unmapped commands."""
        suggestions = _generate_suggestions(WriterCommand.COVER_LETTER, mock_rfp)
        assert len(suggestions) > 0
        assert "Review" in suggestions[0]


class TestGenerateFallbackContent:
    """Tests for fallback content generation."""

    @pytest.fixture
    def mock_rfp(self):
        """Create mock RFP."""
        rfp = MagicMock()
        rfp.title = "Cloud Services Contract"
        rfp.agency = "NASA"
        return rfp

    def test_executive_summary_fallback(self, mock_rfp):
        """Test fallback content for executive summary."""
        content = _generate_fallback_content(
            WriterCommand.EXECUTIVE_SUMMARY,
            mock_rfp,
            max_words=200
        )
        assert "Cloud Services Contract" in content
        assert len(content) > 0

    def test_technical_approach_fallback(self, mock_rfp):
        """Test fallback content for technical approach."""
        content = _generate_fallback_content(
            WriterCommand.TECHNICAL_APPROACH,
            mock_rfp,
            max_words=300
        )
        assert "METHODOLOGY" in content or "approach" in content.lower()

    def test_fallback_respects_max_words(self, mock_rfp):
        """Test that fallback content respects max_words limit."""
        content = _generate_fallback_content(
            WriterCommand.EXECUTIVE_SUMMARY,
            mock_rfp,
            max_words=50
        )
        word_count = len(content.split())
        assert word_count <= 50

    def test_unknown_command_fallback(self, mock_rfp):
        """Test fallback for command without specific template."""
        content = _generate_fallback_content(
            WriterCommand.PRICING_NARRATIVE,
            mock_rfp,
            max_words=100
        )
        assert content is not None
        assert len(content) > 0


class TestWriterCommandsEndpoint:
    """Tests for list_writer_commands endpoint."""

    @pytest.mark.asyncio
    async def test_list_commands_returns_all(self):
        """Test that all commands are returned."""
        from app.routes.generation import list_writer_commands

        result = await list_writer_commands()

        assert "commands" in result
        assert "total" in result
        assert result["total"] == len(WriterCommand)

    @pytest.mark.asyncio
    async def test_list_commands_format(self):
        """Test command list format."""
        from app.routes.generation import list_writer_commands

        result = await list_writer_commands()

        for cmd in result["commands"]:
            assert "command" in cmd
            assert "name" in cmd
            assert "description" in cmd
            assert "default_max_words" in cmd
            assert "shortcut" in cmd
            assert cmd["shortcut"].startswith("/")


class TestExecuteWriterCommand:
    """Tests for execute_writer_command endpoint."""

    @pytest.fixture
    def mock_rfp(self):
        """Create mock RFP."""
        rfp = MagicMock()
        rfp.rfp_id = "RFP-2024-001"
        rfp.title = "IT Services Contract"
        rfp.agency = "Department of Defense"
        rfp.description = "Comprehensive IT support services"
        return rfp

    @patch('app.routes.generation.get_llm_manager')
    @pytest.mark.asyncio
    async def test_execute_command_success(self, mock_get_manager, mock_rfp):
        """Test successful command execution."""
        mock_manager = MagicMock()
        mock_manager.llm_manager.generate_text.return_value = (
            "This is a professionally written executive summary "
            "demonstrating our experience and qualifications. "
            "We are committed to delivering excellence."
        )
        mock_get_manager.return_value = mock_manager

        from app.routes.generation import execute_writer_command

        request = AIWriterRequest(command=WriterCommand.EXECUTIVE_SUMMARY)
        response = await execute_writer_command(mock_rfp, request)

        assert response.command == "executive-summary"
        assert response.section_name == "Executive Summary"
        assert response.word_count > 0
        assert response.rfp_id == "RFP-2024-001"

    @patch('app.routes.generation.get_llm_manager')
    @pytest.mark.asyncio
    async def test_execute_command_with_context(self, mock_get_manager, mock_rfp):
        """Test command execution with additional context."""
        mock_manager = MagicMock()
        mock_manager.llm_manager.generate_text.return_value = "Generated content"
        mock_get_manager.return_value = mock_manager

        from app.routes.generation import execute_writer_command

        request = AIWriterRequest(
            command=WriterCommand.TECHNICAL_APPROACH,
            context="Focus on cloud migration and DevOps"
        )
        response = await execute_writer_command(mock_rfp, request)

        # Verify context was included in prompt
        call_args = mock_manager.llm_manager.generate_text.call_args
        assert "cloud migration" in call_args[0][0] or "DevOps" in call_args[0][0]

    @patch('app.routes.generation.get_llm_manager')
    @pytest.mark.asyncio
    async def test_execute_command_fallback_on_error(self, mock_get_manager, mock_rfp):
        """Test fallback when LLM fails."""
        mock_manager = MagicMock()
        mock_manager.llm_manager.generate_text.side_effect = Exception("LLM error")
        mock_get_manager.return_value = mock_manager

        from app.routes.generation import execute_writer_command

        request = AIWriterRequest(command=WriterCommand.EXECUTIVE_SUMMARY)
        response = await execute_writer_command(mock_rfp, request)

        assert response.generation_method == "template"
        assert response.confidence_score == 0.5
        assert response.content is not None


class TestExpandContentEndpoint:
    """Tests for expand_content endpoint."""

    @pytest.fixture
    def mock_rfp(self):
        """Create mock RFP."""
        rfp = MagicMock()
        rfp.rfp_id = "RFP-2024-001"
        rfp.title = "IT Services"
        return rfp

    @patch('app.routes.generation.get_llm_manager')
    @pytest.mark.asyncio
    async def test_expand_detailed(self, mock_get_manager, mock_rfp):
        """Test detailed expansion."""
        mock_manager = MagicMock()
        mock_manager.llm_manager.generate_text.return_value = (
            "This is expanded detailed content with multiple paragraphs "
            "explaining the approach in depth."
        )
        mock_get_manager.return_value = mock_manager

        from app.routes.generation import expand_content

        request = ExpandRequest(
            text="Brief outline",
            expansion_type="detailed",
            target_length=300
        )
        result = await expand_content(mock_rfp, request)

        assert "expanded_text" in result
        assert "word_count" in result
        assert result["expansion_type"] == "detailed"

    @patch('app.routes.generation.get_llm_manager')
    @pytest.mark.asyncio
    async def test_expand_bullets(self, mock_get_manager, mock_rfp):
        """Test bullet point expansion."""
        mock_manager = MagicMock()
        mock_manager.llm_manager.generate_text.return_value = (
            "• First point\n• Second point\n• Third point"
        )
        mock_get_manager.return_value = mock_manager

        from app.routes.generation import expand_content

        request = ExpandRequest(
            text="Key points",
            expansion_type="bullets",
            target_length=200
        )
        result = await expand_content(mock_rfp, request)

        assert result["expansion_type"] == "bullets"


class TestSummarizeContentEndpoint:
    """Tests for summarize_content endpoint."""

    @pytest.fixture
    def mock_rfp(self):
        """Create mock RFP."""
        rfp = MagicMock()
        rfp.rfp_id = "RFP-2024-001"
        rfp.title = "IT Services"
        return rfp

    @patch('app.routes.generation.get_llm_manager')
    @pytest.mark.asyncio
    async def test_summarize_executive(self, mock_get_manager, mock_rfp):
        """Test executive summary type."""
        mock_manager = MagicMock()
        mock_manager.llm_manager.generate_text.return_value = "Concise executive summary."
        mock_get_manager.return_value = mock_manager

        from app.routes.generation import summarize_content

        long_text = "Long content to summarize. " * 50
        request = SummarizeRequest(
            text=long_text,
            summary_type="executive",
            max_length=150
        )
        result = await summarize_content(mock_rfp, request)

        assert "summary" in result
        assert "compression_ratio" in result
        assert result["summary_type"] == "executive"

    @patch('app.routes.generation.get_llm_manager')
    @pytest.mark.asyncio
    async def test_summarize_compression_ratio(self, mock_get_manager, mock_rfp):
        """Test compression ratio calculation."""
        mock_manager = MagicMock()
        mock_manager.llm_manager.generate_text.return_value = "Short summary of ten words here now."
        mock_get_manager.return_value = mock_manager

        from app.routes.generation import summarize_content

        long_text = "Word " * 100  # 100 words
        request = SummarizeRequest(
            text=long_text,
            summary_type="bullets",
            max_length=50
        )
        result = await summarize_content(mock_rfp, request)

        assert result["original_length"] == 100
        assert result["compression_ratio"] < 1.0


class TestImproveContentEndpoint:
    """Tests for improve_content endpoint."""

    @pytest.fixture
    def mock_rfp(self):
        """Create mock RFP."""
        rfp = MagicMock()
        rfp.rfp_id = "RFP-2024-001"
        rfp.title = "IT Services"
        rfp.agency = "DoD"
        return rfp

    @patch('app.routes.generation.get_llm_manager')
    @pytest.mark.asyncio
    async def test_improve_content_success(self, mock_get_manager, mock_rfp):
        """Test content improvement."""
        mock_manager = MagicMock()
        mock_manager.llm_manager.generate_text.return_value = (
            "Improved content that is more persuasive and compelling."
        )
        mock_get_manager.return_value = mock_manager

        from app.routes.generation import improve_content

        request = RefineRequest(
            text="Original weak content.",
            instruction="Make it more persuasive"
        )
        result = await improve_content(mock_rfp, request)

        assert "improved_text" in result
        assert "word_count_change" in result
        assert result["instruction"] == "Make it more persuasive"

    @patch('app.routes.generation.get_llm_manager')
    @pytest.mark.asyncio
    async def test_improve_content_fallback_on_error(self, mock_get_manager, mock_rfp):
        """Test fallback when improvement fails."""
        mock_manager = MagicMock()
        mock_manager.llm_manager.generate_text.side_effect = Exception("Error")
        mock_get_manager.return_value = mock_manager

        from app.routes.generation import improve_content

        request = RefineRequest(
            text="Original content.",
            instruction="Improve"
        )
        result = await improve_content(mock_rfp, request)

        # Should return original text on error
        assert result["improved_text"] == "Original content."
        assert "error" in result


class TestRefineEndpoint:
    """Tests for refine_text endpoint."""

    @patch('app.routes.generation.get_llm_manager')
    @pytest.mark.asyncio
    async def test_refine_text_success(self, mock_get_manager):
        """Test text refinement."""
        mock_manager = MagicMock()
        mock_manager.refine_content.return_value = "Refined and improved text."
        mock_get_manager.return_value = mock_manager

        from app.routes.generation import refine_text

        request = RefineRequest(
            text="Original text",
            instruction="Make formal"
        )
        result = await refine_text(request)

        assert "refined_text" in result
        assert result["refined_text"] == "Refined and improved text."

    @patch('app.routes.generation.get_llm_manager')
    @pytest.mark.asyncio
    async def test_refine_text_fallback(self, mock_get_manager):
        """Test refinement fallback on error."""
        mock_manager = MagicMock()
        mock_manager.refine_content.side_effect = Exception("LLM unavailable")
        mock_get_manager.return_value = mock_manager

        from app.routes.generation import refine_text

        request = RefineRequest(
            text="Original",
            instruction="Improve"
        )
        result = await refine_text(request)

        # Should return fallback with instruction note
        assert "[REFINED]" in result["refined_text"]
        assert "Improve" in result["refined_text"]
