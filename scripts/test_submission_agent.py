#!/usr/bin/env python3
"""
Test the Submission Agent with mock data.
"""
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.submission_agent import SubmissionAgent
from agents.notification_service import NotificationService

def main():
    """Test submission agent."""
    print("=" * 80)
    print("SUBMISSION AGENT TEST")
    print("=" * 80)

    # Initialize services
    notification_service = NotificationService(enabled_channels=["email"])
    agent = SubmissionAgent(
        notification_service=notification_service,
        max_concurrent_submissions=3,
        data_dir="./data"
    )

    print(f"\n✅ Submission Agent initialized")
    print(f"   Available portals: {list(agent.portal_adapters.keys())}")

    # Create test RFP and bid document
    test_rfp = {
        "rfp_id": "TEST-RFP-001",
        "title": "Test Water Delivery Services",
        "agency": "Test Agency",
        "response_deadline": datetime.utcnow() + timedelta(days=7),
        "cage_code": "12345",
        "duns_number": "987654321",
        "solicitation_number": "TEST-SOL-2025-001"
    }

    test_bid = {
        "document_id": "BID-DOC-001",
        "rfp_id": "TEST-RFP-001",
        "format": "PDF",
        "content": "Mock bid document content",
        "cage_code": "12345",
        "duns_number": "987654321",
        "solicitation_number": "TEST-SOL-2025-001",
        "vendor_name": "Test Vendor Inc.",
        "vendor_address": "123 Test St, Test City, TS 12345"
    }

    # Submit to mock portal
    print("\n📤 Submitting bid to mock portal...")
    job = agent.submit_bid(
        rfp_data=test_rfp,
        bid_document=test_bid,
        portal="mock",
        priority=1
    )

    print(f"   ✅ Job created: {job.job_id}")
    print(f"   Status: {job.status.value}")

    # Process queue
    print("\n⚙️ Processing submission queue...")
    agent.process_queue()

    # Check job status
    print("\n📊 Checking job status...")
    status = agent.get_job_status(job.job_id)
    if status:
        print(f"   Status: {status['status']}")
        print(f"   Confirmation: {status.get('confirmation_number', 'N/A')}")
        print(f"   Attempts: {status['attempts']}")

    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    main()
