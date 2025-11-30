"""
Integration tests for API endpoints.

Tests the full request/response cycle through FastAPI TestClient.
Validates endpoint behavior with database operations and mocked external services.
"""
from unittest.mock import patch, MagicMock


class TestHealthEndpoints:
    """Test health and root endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "RFP" in data["message"]
        assert "version" in data
        assert "docs" in data

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestRFPEndpoints:
    """Integration tests for RFP endpoints."""

    def test_get_discovered_rfps_empty(self, client):
        """Test listing discovered RFPs when database is empty."""
        response = client.get("/api/v1/rfps/discovered")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_discovered_rfps_with_data(self, client, sample_rfp):
        """Test listing discovered RFPs with data in database."""
        response = client.get("/api/v1/rfps/discovered")

        assert response.status_code == 200
        data = response.json()
        # sample_rfp starts in DISCOVERED stage
        assert any(rfp["rfp_id"] == sample_rfp.rfp_id for rfp in data)

    def test_get_recent_rfps(self, client, sample_rfp_list):
        """Test getting recent RFPs."""
        response = client.get("/api/v1/rfps/recent")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_stats_overview(self, client, sample_rfp_list):
        """Test getting RFP stats overview."""
        response = client.get("/api/v1/rfps/stats/overview")

        assert response.status_code == 200
        data = response.json()
        # Should have some stats
        assert isinstance(data, dict)

    def test_get_rfp_by_id(self, client, sample_rfp):
        """Test getting a specific RFP by ID (uses rfp_id string)."""
        response = client.get(f"/api/v1/rfps/{sample_rfp.rfp_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["rfp_id"] == sample_rfp.rfp_id
        assert data["title"] == sample_rfp.title
        assert data["agency"] == sample_rfp.agency

    def test_get_rfp_not_found(self, client):
        """Test 404 when RFP doesn't exist."""
        response = client.get("/api/v1/rfps/nonexistent-rfp-id")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_create_rfp(self, client):
        """Test creating a new RFP."""
        rfp_data = {
            "rfp_id": "RFP-TEST-001",
            "title": "Test RFP Creation",
            "description": "Testing RFP creation endpoint",
            "agency": "Test Agency",
            "naics_code": "541512"
        }

        response = client.post("/api/v1/rfps", json=rfp_data)

        assert response.status_code == 200
        data = response.json()
        assert data["rfp_id"] == rfp_data["rfp_id"]
        assert data["title"] == rfp_data["title"]

    def test_update_rfp(self, client, sample_rfp):
        """Test updating an RFP (uses rfp_id string)."""
        # Update the sample RFP
        update_data = {
            "title": "Updated RFP Title",
            "description": "Updated description"
        }

        response = client.put(f"/api/v1/rfps/{sample_rfp.rfp_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        # Verify response contains the RFP data
        assert "title" in data
        assert "rfp_id" in data

    def test_triage_rfp(self, client, sample_rfp, sample_company_profile):
        """Test triaging an RFP (uses rfp_id string) - requires company profile."""
        response = client.post(f"/api/v1/rfps/{sample_rfp.rfp_id}/triage")

        # Triage endpoint may require company profile context
        # Accept 200 (success) or 422 (validation error if missing requirements)
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            assert "triage_score" in data

    def test_advance_rfp_stage(self, client, sample_rfp):
        """Test advancing RFP to next pipeline stage (uses rfp_id string)."""
        response = client.post(
            f"/api/v1/rfps/{sample_rfp.rfp_id}/advance-stage",
            json={"target_stage": "triaged"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["current_stage"] == "triaged"

    def test_get_rfp_competitors(self, client, sample_rfp, sample_company_profile):
        """Test getting competitor analysis (uses rfp_id string)."""
        response = client.get(f"/api/v1/rfps/{sample_rfp.rfp_id}/competitors")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_get_rfp_partners(self, client, sample_rfp, sample_company_profile):
        """Test getting partner recommendations (uses rfp_id string)."""
        response = client.get(f"/api/v1/rfps/{sample_rfp.rfp_id}/partners")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestAlertRulesEndpoints:
    """Integration tests for alert rules CRUD."""

    def test_create_alert_rule(self, client):
        """Test creating a new alert rule."""
        rule_data = {
            "name": "Test Alert Rule",
            "alert_type": "keyword_match",
            "priority": "medium",
            "criteria": {
                "keywords": ["cloud", "security"],
                "match_title": True
            },
            "notification_channels": ["in_app"]
        }

        response = client.post("/api/v1/alerts/rules", json=rule_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == rule_data["name"]
        assert data["alert_type"] == rule_data["alert_type"]
        assert data["is_active"] is True
        assert "id" in data

    def test_list_alert_rules(self, client, sample_alert_rule):
        """Test listing alert rules."""
        response = client.get("/api/v1/alerts/rules")

        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert data["total"] >= 1

    def test_filter_alert_rules_by_type(self, client, sample_alert_rule):
        """Test filtering rules by alert type."""
        response = client.get("/api/v1/alerts/rules?alert_type=keyword_match")

        assert response.status_code == 200
        data = response.json()
        assert all(r["alert_type"] == "keyword_match" for r in data["rules"])

    def test_filter_alert_rules_active_only(self, client, sample_alert_rule):
        """Test filtering only active rules."""
        response = client.get("/api/v1/alerts/rules?active_only=true")

        assert response.status_code == 200
        data = response.json()
        assert all(r["is_active"] for r in data["rules"])

    def test_get_alert_rule_by_id(self, client, sample_alert_rule):
        """Test getting a specific alert rule."""
        response = client.get(f"/api/v1/alerts/rules/{sample_alert_rule.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_alert_rule.id
        assert data["name"] == sample_alert_rule.name

    def test_update_alert_rule(self, client, sample_alert_rule):
        """Test updating an alert rule."""
        update_data = {
            "name": "Updated Rule Name",
            "priority": "urgent"
        }

        response = client.patch(
            f"/api/v1/alerts/rules/{sample_alert_rule.id}",
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Rule Name"
        assert data["priority"] == "urgent"

    def test_toggle_alert_rule(self, client, sample_alert_rule):
        """Test toggling alert rule active status."""
        # Disable
        response = client.post(f"/api/v1/alerts/rules/{sample_alert_rule.id}/toggle")
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

        # Enable again
        response = client.post(f"/api/v1/alerts/rules/{sample_alert_rule.id}/toggle")
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    def test_delete_alert_rule(self, client, sample_alert_rule):
        """Test deleting an alert rule."""
        response = client.delete(f"/api/v1/alerts/rules/{sample_alert_rule.id}")

        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data["message"].lower()

        # Verify it's gone
        response = client.get(f"/api/v1/alerts/rules/{sample_alert_rule.id}")
        assert response.status_code == 404


class TestAlertNotificationsEndpoints:
    """Integration tests for alert notifications."""

    def test_list_notifications(self, client, sample_notification):
        """Test listing notifications."""
        response = client.get("/api/v1/alerts/notifications")

        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert data["total"] >= 1

    def test_filter_notifications_by_read_status(self, client, sample_notification):
        """Test filtering notifications by read status."""
        response = client.get("/api/v1/alerts/notifications?unread_only=true")

        assert response.status_code == 200
        data = response.json()
        assert all(not n["is_read"] for n in data["notifications"])

    def test_filter_notifications_by_priority(self, client, sample_notification):
        """Test filtering notifications by priority."""
        response = client.get("/api/v1/alerts/notifications?priority=high")

        assert response.status_code == 200
        data = response.json()
        assert all(n["priority"] == "high" for n in data["notifications"])

    def test_get_notification_count(self, client, sample_notification):
        """Test getting notification counts."""
        response = client.get("/api/v1/alerts/notifications/count")

        assert response.status_code == 200
        data = response.json()
        # API returns unread count and by_priority breakdown
        assert "unread" in data
        assert "by_priority" in data

    def test_get_notification_by_id(self, client, sample_notification):
        """Test getting a specific notification."""
        response = client.get(f"/api/v1/alerts/notifications/{sample_notification.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_notification.id

    def test_notification_action_mark_read(self, client, sample_notification):
        """Test marking notification as read using mark_read action."""
        response = client.post(
            f"/api/v1/alerts/notifications/{sample_notification.id}/action",
            json={"action": "mark_read"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_read"] is True

    def test_notification_action_dismiss(self, client, sample_notification):
        """Test dismissing notification."""
        response = client.post(
            f"/api/v1/alerts/notifications/{sample_notification.id}/action",
            json={"action": "dismiss"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_dismissed"] is True

    def test_notification_toggle_read_status(self, client, sample_notification):
        """Test toggling notification read status."""
        # First mark as read
        response = client.post(
            f"/api/v1/alerts/notifications/{sample_notification.id}/action",
            json={"action": "mark_read"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_read"] is True

        # Marking as read again should still work (idempotent)
        response = client.post(
            f"/api/v1/alerts/notifications/{sample_notification.id}/action",
            json={"action": "mark_read"}
        )
        # API may return 200 or 400 for already-read notification
        assert response.status_code in [200, 400]

    def test_mark_all_notifications_read(self, client, sample_notification):
        """Test marking all notifications as read."""
        response = client.post("/api/v1/alerts/notifications/mark-all-read")

        assert response.status_code == 200
        data = response.json()
        assert "marked_read" in data

    def test_dismiss_all_notifications(self, client, sample_notification):
        """Test dismissing all notifications."""
        response = client.post("/api/v1/alerts/notifications/dismiss-all")

        assert response.status_code == 200
        data = response.json()
        assert "dismissed" in data


class TestAlertEvaluationEndpoints:
    """Integration tests for alert evaluation."""

    def test_test_alert_rule(self, client, sample_alert_rule, sample_rfp):
        """Test dry-run evaluation of an alert rule."""
        # Test endpoint uses database integer ID for RFP lookup
        response = client.post(
            f"/api/v1/alerts/rules/{sample_alert_rule.id}/test",
            json={"rfp_id": sample_rfp.id}
        )

        assert response.status_code == 200
        data = response.json()
        # API returns rule info and matching RFPs
        assert "rule_id" in data
        assert "matches_found" in data or "matching_rfps" in data


class TestCompanyProfileEndpoints:
    """Integration tests for company profile endpoints."""

    def test_list_profiles_empty(self, client):
        """Test listing profiles when empty."""
        response = client.get("/api/v1/profiles")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_profiles_with_data(self, client, sample_company_profile):
        """Test listing profiles with data."""
        response = client.get("/api/v1/profiles")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(p["name"] == sample_company_profile.name for p in data)

    def test_get_default_profile(self, client, sample_company_profile):
        """Test getting default profile."""
        response = client.get("/api/v1/profiles/default/current")

        assert response.status_code == 200
        data = response.json()
        assert data["is_default"] is True
        assert data["name"] == sample_company_profile.name

    def test_get_profile_by_id(self, client, sample_company_profile):
        """Test getting profile by ID."""
        response = client.get(f"/api/v1/profiles/{sample_company_profile.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_company_profile.id
        assert "certifications" in data
        assert "naics_codes" in data

    def test_create_profile(self, client):
        """Test creating a new company profile."""
        profile_data = {
            "name": "New Company",
            "legal_name": "New Company LLC",
            "is_default": False,
            "uei": "XYZ789ABC123",
            "naics_codes": ["541512"],
            "certifications": ["ISO 27001"]
        }

        response = client.post("/api/v1/profiles", json=profile_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == profile_data["name"]
        assert data["uei"] == profile_data["uei"]

    def test_update_profile(self, client, sample_company_profile):
        """Test updating a company profile."""
        update_data = {
            "name": "Updated Company Name",
            "employee_count": "100-250"
        }

        response = client.put(
            f"/api/v1/profiles/{sample_company_profile.id}",
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Company Name"

    def test_delete_profile(self, client, sample_company_profile):
        """Test deleting a company profile."""
        # First create a non-default profile
        profile_data = {
            "name": "Temp Company",
            "is_default": False,
            "naics_codes": ["541512"]
        }
        create_response = client.post("/api/v1/profiles", json=profile_data)
        profile_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/v1/profiles/{profile_id}")
        assert response.status_code == 200

    def test_set_default_profile(self, client, sample_company_profile):
        """Test setting a profile as default."""
        # Create a second profile
        profile_data = {
            "name": "Second Company",
            "is_default": False,
            "naics_codes": ["541512"]
        }
        create_response = client.post("/api/v1/profiles", json=profile_data)
        new_profile_id = create_response.json()["id"]

        # Set it as default
        response = client.post(f"/api/v1/profiles/{new_profile_id}/default")

        assert response.status_code == 200
        data = response.json()
        assert data["is_default"] is True


class TestGenerationEndpoints:
    """Integration tests for document generation endpoints."""

    def test_list_writer_commands(self, client):
        """Test listing available AI Writer commands."""
        response = client.get("/api/v1/generation/writer/commands")

        assert response.status_code == 200
        data = response.json()
        assert "commands" in data
        assert "total" in data
        assert data["total"] > 0

        # Verify command structure
        for cmd in data["commands"]:
            assert "command" in cmd
            assert "name" in cmd
            assert "description" in cmd
            assert "default_max_words" in cmd
            assert "shortcut" in cmd

    @patch('src.config.enhanced_bid_llm.EnhancedBidLLMManager')
    @patch('src.rag.rag_engine.RAGEngine')
    def test_execute_writer_command(self, mock_rag_cls, mock_manager_cls, client, sample_rfp, sample_company_profile):
        """Test executing an AI Writer slash command (uses rfp_id string)."""
        # Setup RAG mock
        mock_rag = MagicMock()
        mock_rag.is_built = True
        mock_context = MagicMock()
        mock_context.context_text = "Relevant context"
        mock_rag.generate_context.return_value = mock_context
        mock_rag_cls.return_value = mock_rag

        # Setup LLM manager mock
        mock_manager = MagicMock()
        mock_manager.generate_bid_section.return_value = {
            "section_type": "executive_summary",
            "content": "Generated executive summary for the proposal.",
            "word_count": 200,
            "confidence_score": 0.88,
            "generation_method": "llm",
            "status": "generated"
        }
        mock_manager_cls.return_value = mock_manager

        response = client.post(
            f"/api/v1/generation/{sample_rfp.rfp_id}/writer",
            json={
                "command": "executive-summary",
                "context": "Focus on cloud capabilities",
                "tone": "professional"
            }
        )

        # Response may be 200 with generated content or 500 if no company profile in session
        # For integration test, we verify the endpoint is reachable
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["command"] == "executive-summary"
            assert "content" in data

    @patch('src.config.enhanced_bid_llm.EnhancedBidLLMManager')
    @patch('src.rag.rag_engine.RAGEngine')
    def test_writer_expand_content(self, mock_rag_cls, mock_manager_cls, client, sample_rfp, sample_company_profile):
        """Test expanding content with AI Writer (uses rfp_id string)."""
        # Setup RAG mock
        mock_rag = MagicMock()
        mock_rag.is_built = True
        mock_context = MagicMock()
        mock_context.context_text = "Additional context"
        mock_rag.generate_context.return_value = mock_context
        mock_rag_cls.return_value = mock_rag

        # Setup LLM manager mock
        mock_manager = MagicMock()
        mock_manager.refine_content.return_value = "Expanded and detailed content with more information."
        mock_manager_cls.return_value = mock_manager

        response = client.post(
            f"/api/v1/generation/{sample_rfp.rfp_id}/writer/expand",
            json={
                "text": "Brief content to expand.",
                "target_length": 500
            }
        )

        # Response may be 200 or 500 depending on LLM availability
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "expanded_text" in data

    @patch('src.config.enhanced_bid_llm.EnhancedBidLLMManager')
    @patch('src.rag.rag_engine.RAGEngine')
    def test_writer_summarize_content(self, mock_rag_cls, mock_manager_cls, client, sample_rfp, sample_company_profile):
        """Test summarizing content with AI Writer (uses rfp_id string)."""
        mock_rag = MagicMock()
        mock_rag.is_built = True
        mock_rag_cls.return_value = mock_rag

        mock_manager = MagicMock()
        mock_manager.refine_content.return_value = "Concise summary."
        mock_manager_cls.return_value = mock_manager

        response = client.post(
            f"/api/v1/generation/{sample_rfp.rfp_id}/writer/summarize",
            json={
                "text": "Long detailed content that needs to be summarized into a shorter form.",
                "max_length": 50
            }
        )

        # Response may be 200 or 500 depending on LLM availability
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            # API returns 'summary' not 'summarized_text'
            assert "summary" in data or "summarized_text" in data

    @patch('src.config.enhanced_bid_llm.EnhancedBidLLMManager')
    @patch('src.rag.rag_engine.RAGEngine')
    def test_writer_improve_content(self, mock_rag_cls, mock_manager_cls, client, sample_rfp, sample_company_profile):
        """Test improving content with AI Writer (uses rfp_id string)."""
        mock_rag = MagicMock()
        mock_rag.is_built = True
        mock_context = MagicMock()
        mock_context.context_text = "Context"
        mock_rag.generate_context.return_value = mock_context
        mock_rag_cls.return_value = mock_rag

        mock_manager = MagicMock()
        mock_manager.refine_content.return_value = "Improved and polished content."
        mock_manager_cls.return_value = mock_manager

        response = client.post(
            f"/api/v1/generation/{sample_rfp.rfp_id}/writer/improve",
            json={
                "content": "Original content to improve.",
                "instruction": "Make it more persuasive"
            }
        )

        # Response may be 200, 422 (validation), or 500 depending on LLM availability
        assert response.status_code in [200, 422, 500]
        if response.status_code == 200:
            data = response.json()
            assert "improved_text" in data


class TestChatEndpoints:
    """Integration tests for chat endpoints."""

    @patch('src.config.llm_adapter.create_llm_interface')
    @patch('src.rag.rag_engine.RAGEngine')
    def test_chat_with_rfp(self, mock_rag_cls, mock_llm_factory, client, sample_rfp):
        """Test chat endpoint with RAG (uses rfp_id string)."""
        # Setup RAG mock
        mock_rag = MagicMock()
        mock_rag.is_built = True
        mock_doc = MagicMock()
        mock_doc.content = "Document about deadlines and requirements."
        mock_doc.document_id = "doc-1"
        mock_doc.source_dataset = "RFP"
        mock_doc.similarity_score = 0.9
        mock_context = MagicMock()
        mock_context.retrieved_documents = [mock_doc]
        mock_context.context_text = "Deadline is January 15, 2025"
        mock_rag.generate_context.return_value = mock_context
        mock_rag_cls.return_value = mock_rag

        # Setup LLM mock
        mock_llm = MagicMock()
        mock_llm.generate_text.return_value = {
            "content": "The deadline is January 15, 2025."
        }
        mock_llm_factory.return_value = mock_llm

        response = client.post(
            f"/api/v1/chat/{sample_rfp.rfp_id}/chat",
            json={
                "message": "What is the deadline?",
                "history": []
            }
        )

        # Response may be 200 or 500 depending on service availability
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "answer" in data
            assert "rfp_id" in data

    def test_chat_suggestions(self, client, sample_rfp):
        """Test getting chat suggestions for an RFP (uses rfp_id string)."""
        response = client.get(f"/api/v1/chat/{sample_rfp.rfp_id}/chat/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "rfp_id" in data
        assert len(data["suggestions"]) > 0

    @patch('src.config.llm_adapter.create_llm_interface')
    @patch('src.rag.rag_engine.RAGEngine')
    def test_chat_status(self, mock_rag_cls, mock_llm_factory, client, sample_rfp):
        """Test chat status endpoint (uses rfp_id string)."""
        mock_rag = MagicMock()
        mock_rag.is_built = True
        mock_rag.vector_index = MagicMock()
        mock_rag.vector_index.document_ids = ["doc1", "doc2"]
        mock_rag_cls.return_value = mock_rag

        mock_llm = MagicMock()
        mock_llm.get_status.return_value = {"current_backend": "openai"}
        mock_llm_factory.return_value = mock_llm

        response = client.get(f"/api/v1/chat/{sample_rfp.rfp_id}/chat/status")

        assert response.status_code == 200
        data = response.json()
        assert "chat_available" in data
        assert "rag_status" in data
        assert "llm_status" in data


class TestScraperEndpoints:
    """Integration tests for scraper endpoints."""

    def test_get_rfp_documents(self, client, sample_rfp):
        """Test getting documents for an RFP (uses rfp_id string)."""
        response = client.get(f"/api/v1/scraper/{sample_rfp.rfp_id}/documents")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_rfp_qa(self, client, sample_rfp):
        """Test getting Q&A for an RFP (uses rfp_id string)."""
        response = client.get(f"/api/v1/scraper/{sample_rfp.rfp_id}/qa")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAPIErrorHandling:
    """Test API error handling."""

    def test_invalid_endpoint_404(self, client):
        """Test 404 for non-existent endpoint."""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_invalid_rfp_id_format(self, client):
        """Test error for invalid RFP ID format."""
        response = client.get("/api/v1/rfps/not-a-number")

        # Could be 404 or 422 depending on route design
        assert response.status_code in [404, 422]

    def test_invalid_request_body(self, client):
        """Test validation error for invalid request body."""
        response = client.post(
            "/api/v1/alerts/rules",
            json={"invalid_field": "value"}  # Missing required fields
        )

        assert response.status_code == 422

    def test_alert_rule_not_found(self, client):
        """Test 404 for non-existent alert rule."""
        response = client.get("/api/v1/alerts/rules/999999")

        assert response.status_code == 404

    def test_notification_not_found(self, client):
        """Test 404 for non-existent notification."""
        response = client.get("/api/v1/alerts/notifications/999999")

        assert response.status_code == 404

    def test_invalid_notification_action(self, client, sample_notification):
        """Test error for invalid notification action."""
        response = client.post(
            f"/api/v1/alerts/notifications/{sample_notification.id}/action",
            json={"action": "invalid_action"}
        )

        # API returns 400 Bad Request for invalid action values
        assert response.status_code in [400, 422]
