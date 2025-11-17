# Implementation Plan: Phase 2 - Dashboard & Submission Agent

**Date**: November 14, 2025
**Status**: Planning
**Previous Phase**: Discovery Agent ✅ Completed

## Executive Summary

This document outlines the implementation plan for the next two critical phases of the RFP Bid Generation System:
1. **Dashboard and Workflow UI Development** - User interface for monitoring and managing the bid pipeline
2. **Submission Agent Implementation** - Automated submission of completed bids to government portals

## Current System State

### Completed Components ✅
- ✅ Discovery Agent (`src/agents/discovery_agent.py`)
- ✅ RAG Engine with FAISS indexing
- ✅ Compliance Matrix Generator
- ✅ Pricing Engine
- ✅ Go/No-Go Decision Engine
- ✅ Bid Document Generator
- ✅ End-to-end pipeline validation

### System Capabilities
- Autonomous RFP discovery and triage
- Semantic search across historical data
- Automated compliance matrix generation
- AI-powered pricing with margin compliance
- Data-driven go/no-go decisions
- Multi-format bid document generation

## Phase 2A: Dashboard and Workflow UI Development

### Overview
Build a web-based dashboard for monitoring RFP discovery, reviewing pipeline progress, approving decisions, and managing bid submissions.

### Objectives
1. Provide real-time visibility into the RFP pipeline
2. Enable human-in-the-loop decision review and approval
3. Monitor system performance and health metrics
4. Manage bid document review and editing
5. Track submission status and outcomes

### Technology Stack Recommendations

#### Option 1: Modern React Stack (Recommended)
```
Frontend:
- React 18+ with TypeScript
- Tailwind CSS v4.1 for styling
- Tanstack Query (React Query) for data fetching
- Zustand or Redux for state management
- React Router for navigation
- Recharts or Chart.js for visualizations

Backend API:
- FastAPI (Python) for REST API
- WebSocket support for real-time updates
- SQLite or PostgreSQL for dashboard data
- Redis for caching and pub/sub

Deployment:
- Docker containers
- Nginx reverse proxy
- PM2 for process management
```

#### Option 2: Lightweight Flask + HTMX
```
Frontend:
- HTMX for dynamic updates
- Tailwind CSS for styling
- Alpine.js for interactive components

Backend:
- Flask with Flask-SocketIO
- SQLAlchemy ORM
- Celery for background tasks
```

### Dashboard Features & Modules

#### 1. RFP Discovery Dashboard
**Features:**
- Live feed of discovered RFPs
- Triage score visualization
- Filtering by category, agency, value, deadline
- Quick actions: approve, reject, flag for review

**API Endpoints:**
```python
GET  /api/rfps/discovered       # List discovered RFPs
GET  /api/rfps/{id}             # Get RFP details
POST /api/rfps/{id}/triage      # Update triage decision
GET  /api/rfps/stats            # Discovery statistics
```

#### 2. Pipeline Monitoring Dashboard
**Features:**
- Pipeline stage visualization (Kanban or flowchart)
- Real-time progress tracking
- Performance metrics (processing time, success rate)
- Error monitoring and alerts

**API Endpoints:**
```python
GET  /api/pipeline/status       # Overall pipeline status
GET  /api/pipeline/{rfp_id}     # RFP pipeline progress
GET  /api/pipeline/metrics      # Performance metrics
WS   /ws/pipeline               # WebSocket for live updates
```

#### 3. Decision Review Dashboard
**Features:**
- Go/No-Go recommendations with scoring details
- Side-by-side comparison of RFP requirements vs capabilities
- Margin analysis and risk factors
- Approval workflow (approve, modify, reject)
- Comments and notes system

**API Endpoints:**
```python
GET  /api/decisions/pending     # Pending decisions
GET  /api/decisions/{id}        # Decision details
POST /api/decisions/{id}/approve # Approve decision
POST /api/decisions/{id}/modify  # Modify and reprocess
```

#### 4. Bid Document Management
**Features:**
- Document preview (HTML, Markdown, PDF)
- Inline editing capability
- Version history
- Compliance matrix review
- Pricing breakdown visualization
- Export in multiple formats

**API Endpoints:**
```python
GET  /api/bids/{id}             # Get bid document
PUT  /api/bids/{id}             # Update bid content
GET  /api/bids/{id}/versions    # Version history
POST /api/bids/{id}/export      # Export in format
```

#### 5. Submission Queue Dashboard
**Features:**
- Submission queue with status tracking
- Scheduled submissions calendar
- Submission history and audit log
- Retry management for failed submissions
- Confirmation tracking

**API Endpoints:**
```python
GET  /api/submissions/queue     # Submission queue
POST /api/submissions           # Create submission
GET  /api/submissions/{id}      # Submission status
POST /api/submissions/{id}/retry # Retry failed submission
```

#### 6. Analytics & Reporting
**Features:**
- Win/loss analysis
- Category performance trends
- Pricing competitiveness analysis
- Response time metrics
- Custom report generation

**API Endpoints:**
```python
GET  /api/analytics/overview    # Dashboard overview
GET  /api/analytics/trends      # Historical trends
GET  /api/analytics/reports     # Generate reports
```

### UI/UX Design Principles

1. **Information Hierarchy**: Critical actions and high-priority RFPs prominently displayed
2. **Progressive Disclosure**: Show summary first, details on demand
3. **Real-time Updates**: WebSocket integration for live pipeline updates
4. **Responsive Design**: Works on desktop, tablet, mobile
5. **Accessibility**: WCAG 2.1 AA compliance
6. **Dark Mode**: Support for light/dark themes

### Data Models for Dashboard

```python
# models/dashboard.py

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum

class PipelineStage(Enum):
    DISCOVERED = "discovered"
    TRIAGED = "triaged"
    ANALYZING = "analyzing"
    PRICING = "pricing"
    DECISION_PENDING = "decision_pending"
    APPROVED = "approved"
    DOCUMENT_GENERATION = "document_generation"
    REVIEW = "review"
    SUBMISSION_READY = "submission_ready"
    SUBMITTED = "submitted"
    REJECTED = "rejected"

@dataclass
class RFPPipelineStatus:
    rfp_id: str
    title: str
    agency: str
    current_stage: PipelineStage
    triage_score: float
    decision_recommendation: Optional[str]
    overall_score: Optional[float]
    started_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime]
    assigned_to: Optional[str]

@dataclass
class DashboardMetrics:
    total_discovered: int
    in_pipeline: int
    approved_count: int
    rejected_count: int
    submitted_count: int
    avg_processing_time: float
    success_rate: float
    pending_reviews: int
```

### Implementation Timeline

**Week 1: Backend API Development**
- Day 1-2: FastAPI setup and database models
- Day 3-4: Implement core API endpoints
- Day 5: WebSocket integration for real-time updates

**Week 2: Frontend Foundation**
- Day 1-2: React project setup, routing, state management
- Day 3-4: Reusable component library (cards, tables, forms)
- Day 5: API integration layer

**Week 3: Core Dashboard Features**
- Day 1-2: RFP Discovery Dashboard
- Day 3-4: Pipeline Monitoring Dashboard
- Day 5: Decision Review Dashboard

**Week 4: Document & Submission Features**
- Day 1-2: Bid Document Management
- Day 3-4: Submission Queue Dashboard
- Day 5: Analytics & Reporting

**Week 5: Polish & Testing**
- Day 1-2: UI/UX refinements, responsiveness
- Day 3-4: Integration testing
- Day 5: User acceptance testing

## Phase 2B: Submission Agent Implementation

### Overview
Automate the submission of approved bid documents to government procurement portals (SAM.gov, agency-specific portals).

### Objectives
1. Automate bid submission to government portals
2. Handle portal-specific formatting and requirements
3. Track submission status and confirmations
4. Manage resubmissions and corrections
5. Maintain audit trail for compliance

### Submission Agent Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Submission Agent Orchestrator               │
│  • Queue Management  • Scheduling  • Error Handling      │
└─────────────────────────────────────────────────────────┘
                         ↓
        ┌────────────────┴────────────────┐
        ↓                                  ↓
┌──────────────────┐            ┌──────────────────────┐
│  Portal Adapters │            │  Document Processor   │
│  • SAM.gov       │            │  • Format Conversion  │
│  • GSA eBuy      │            │  • Validation         │
│  • Agency Sites  │            │  • Package Assembly   │
└──────────────────┘            └──────────────────────┘
        ↓                                  ↓
┌─────────────────────────────────────────────────────────┐
│                  Submission Queue                        │
│    Pending | In Progress | Completed | Failed            │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Confirmation & Tracking                     │
│  • Receipt Verification  • Audit Logs  • Notifications   │
└─────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Submission Orchestrator
**Responsibilities:**
- Queue management (FIFO, priority-based)
- Submission scheduling (respect deadlines, business hours)
- Retry logic with exponential backoff
- Parallel submission handling (rate limiting)
- Error handling and notification

```python
# src/agents/submission_agent.py

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum

class SubmissionStatus(Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    FORMATTING = "formatting"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REJECTED = "rejected"

@dataclass
class SubmissionJob:
    job_id: str
    rfp_id: str
    bid_document_id: str
    portal: str
    deadline: datetime
    priority: int
    status: SubmissionStatus
    attempts: int
    max_retries: int
    created_at: datetime
    submitted_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    error_message: Optional[str]
    confirmation_number: Optional[str]

class SubmissionAgent:
    """Autonomous agent for bid submission to government portals."""

    def __init__(
        self,
        document_generator,
        notification_service=None,
        max_concurrent_submissions: int = 5
    ):
        self.document_generator = document_generator
        self.notification_service = notification_service
        self.max_concurrent = max_concurrent_submissions
        self.queue = []
        self.portal_adapters = {}
        self._initialize_adapters()

    def submit_bid(
        self,
        rfp_data: Dict,
        bid_document: Dict,
        portal: str,
        scheduled_time: Optional[datetime] = None
    ) -> SubmissionJob:
        """Submit a bid to the specified portal."""

    def validate_submission(self, job: SubmissionJob) -> bool:
        """Validate bid meets portal requirements."""

    def process_queue(self):
        """Process pending submissions from the queue."""

    def retry_failed_submission(self, job_id: str):
        """Retry a failed submission with updated parameters."""
```

#### 2. Portal Adapters
**Supported Portals:**
- SAM.gov (System for Award Management)
- GSA eBuy
- Agency-specific portals (extensible)

**Adapter Interface:**
```python
class PortalAdapter:
    """Base class for portal-specific submission logic."""

    def validate_requirements(self, bid_data: Dict) -> List[str]:
        """Check if bid meets portal requirements."""

    def format_submission(self, bid_document: Dict) -> Dict:
        """Format bid for portal-specific requirements."""

    def submit(self, formatted_data: Dict) -> Dict:
        """Submit bid to portal (API or web automation)."""

    def verify_submission(self, confirmation_data: Dict) -> bool:
        """Verify submission was received."""

    def get_submission_status(self, submission_id: str) -> str:
        """Check status of submitted bid."""
```

**SAM.gov Adapter Example:**
```python
class SAMGovAdapter(PortalAdapter):
    """Adapter for SAM.gov submissions."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.sam.gov"

    def validate_requirements(self, bid_data: Dict) -> List[str]:
        errors = []
        # Check required fields
        required = ['cage_code', 'duns_number', 'solicitation_number']
        for field in required:
            if field not in bid_data:
                errors.append(f"Missing required field: {field}")

        # Validate file formats
        if bid_data.get('format') not in ['PDF', 'DOCX']:
            errors.append("SAM.gov requires PDF or DOCX format")

        return errors

    def submit(self, formatted_data: Dict) -> Dict:
        # API submission logic or browser automation
        pass
```

#### 3. Document Processor
**Responsibilities:**
- Convert bid documents to portal-required formats
- Assemble submission packages (forms, attachments, certifications)
- Validate file sizes and naming conventions
- Digital signature application (if required)

```python
class DocumentProcessor:
    """Process bid documents for submission."""

    def convert_format(
        self,
        bid_document: Dict,
        target_format: str
    ) -> bytes:
        """Convert bid document to target format."""

    def assemble_package(
        self,
        bid_document: Dict,
        portal_requirements: Dict
    ) -> Dict:
        """Assemble complete submission package."""

    def validate_package(
        self,
        package: Dict,
        requirements: Dict
    ) -> List[str]:
        """Validate submission package."""
```

#### 4. Notification Service
**Notifications:**
- Submission queued
- Submission in progress
- Submission successful (with confirmation number)
- Submission failed (with error details)
- Deadline approaching warnings

**Channels:**
- Email
- Slack/Teams integration
- SMS (for critical alerts)
- Dashboard notifications

### Implementation Strategy

#### Phase 2B.1: Core Infrastructure (Week 6-7)
```python
# Tasks:
1. Implement SubmissionAgent base class
2. Create submission queue with database persistence
3. Build retry logic with exponential backoff
4. Set up notification service
5. Create audit logging system
```

#### Phase 2B.2: Portal Adapters (Week 8-9)
```python
# Tasks:
1. Research SAM.gov API and submission requirements
2. Implement SAMGovAdapter
3. Build document format conversion (PDF, DOCX)
4. Create validation rules for each portal
5. Test with sandbox/test environments
```

#### Phase 2B.3: Browser Automation (Week 10)
For portals without APIs, use browser automation:
```python
# Technologies:
- Selenium or Playwright for web automation
- Handle login, form filling, file uploads
- Screenshot capture for verification
- CAPTCHA handling (manual intervention or service)

# Example with Playwright:
from playwright.sync_api import sync_playwright

class BrowserSubmissionAdapter:
    def submit_via_browser(self, portal_url: str, bid_data: Dict):
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(portal_url)
            # Login, fill forms, upload documents
            page.screenshot(path="submission_proof.png")
            browser.close()
```

#### Phase 2B.4: Integration & Testing (Week 11)
```python
# Tasks:
1. Integrate SubmissionAgent with dashboard
2. End-to-end testing with test portals
3. Load testing for concurrent submissions
4. Error scenario testing
5. Documentation and runbooks
```

### Data Models

```python
# models/submission.py

@dataclass
class SubmissionPackage:
    """Complete submission package for a portal."""
    rfp_id: str
    bid_document_id: str
    portal: str
    primary_document: bytes
    primary_format: str
    attachments: List[Dict[str, bytes]]
    forms: Dict[str, Any]
    certifications: List[str]
    metadata: Dict[str, Any]

@dataclass
class SubmissionConfirmation:
    """Confirmation of bid submission."""
    submission_id: str
    confirmation_number: str
    portal: str
    submitted_at: datetime
    receipt_data: Dict
    verification_screenshot: Optional[bytes]

@dataclass
class SubmissionAuditLog:
    """Audit log entry for submission."""
    log_id: str
    submission_id: str
    timestamp: datetime
    event_type: str  # queued, validating, submitting, etc.
    user: Optional[str]
    details: Dict
    success: bool
    error_message: Optional[str]
```

### Security & Compliance

1. **Credential Management**
   - Use environment variables or secrets manager
   - Rotate API keys regularly
   - Encrypted storage for portal credentials

2. **Audit Trail**
   - Log all submission attempts
   - Store submission confirmations
   - Track document modifications
   - Maintain chain of custody

3. **Data Protection**
   - Encrypt sensitive bid data
   - Secure transmission (HTTPS, VPN)
   - Access control and authentication
   - GDPR/compliance considerations

### Configuration

```python
# config/submission_config.py

SUBMISSION_CONFIG = {
    "max_concurrent_submissions": 5,
    "retry_attempts": 3,
    "retry_backoff_base": 2,  # exponential: 2, 4, 8 seconds
    "queue_poll_interval": 60,  # seconds
    "deadline_warning_hours": 24,

    "portals": {
        "sam.gov": {
            "api_key_env": "SAM_GOV_API_KEY",
            "base_url": "https://api.sam.gov",
            "timeout": 300,  # seconds
            "max_file_size": 100 * 1024 * 1024,  # 100MB
            "allowed_formats": ["PDF", "DOCX"],
        },
        "gsa_ebuy": {
            "credentials_env": "GSA_EBUY_CREDENTIALS",
            "use_browser_automation": True,
            "headless": True,
        }
    },

    "notifications": {
        "email": {
            "enabled": True,
            "recipients": ["bid-team@company.com"],
        },
        "slack": {
            "enabled": True,
            "webhook_url_env": "SLACK_WEBHOOK_URL",
        }
    }
}
```

## Integration Points

### Dashboard ↔ Submission Agent
- Dashboard triggers submissions from approved bids
- Real-time status updates via WebSocket
- User can modify and resubmit from dashboard
- Confirmation display in dashboard

### Discovery Agent → Dashboard → Submission Agent
```
RFP Discovered
    ↓
Triaged & Scored (Discovery Agent)
    ↓
Pipeline Processing (RAG, Compliance, Pricing, Decision)
    ↓
Human Review (Dashboard)
    ↓
Approval (Dashboard)
    ↓
Document Generation
    ↓
Submission Queue (Submission Agent)
    ↓
Submitted to Portal
    ↓
Confirmation Tracked (Dashboard)
```

## Testing Strategy

### Dashboard Testing
1. **Unit Tests**: Component testing with Jest/React Testing Library
2. **Integration Tests**: API endpoint testing
3. **E2E Tests**: Cypress or Playwright for user workflows
4. **Performance Tests**: Load testing with k6 or Artillery
5. **Accessibility Tests**: axe-core for WCAG compliance

### Submission Agent Testing
1. **Unit Tests**: Portal adapter logic
2. **Integration Tests**: Test portals/sandboxes
3. **Mock Tests**: Simulate portal responses
4. **Retry Tests**: Verify error handling and retries
5. **Security Tests**: Credential handling, encryption

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer (Nginx)                 │
└─────────────────────────────────────────────────────────┘
                         ↓
        ┌────────────────┴────────────────┐
        ↓                                  ↓
┌──────────────────┐            ┌──────────────────────┐
│  Frontend        │            │  Backend API         │
│  (React)         │            │  (FastAPI)           │
│  Port 3000       │            │  Port 8000           │
└──────────────────┘            └──────────────────────┘
                                         ↓
        ┌────────────────────────────────┴────────────────┐
        ↓                        ↓                         ↓
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Submission      │  │  PostgreSQL      │  │  Redis           │
│  Agent Workers   │  │  Database        │  │  Cache/Queue     │
│  (Celery)        │  │                  │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Success Metrics

### Dashboard KPIs
- Page load time < 2 seconds
- Real-time update latency < 500ms
- 95% uptime SLA
- User task completion rate > 90%
- Time to review decision < 5 minutes

### Submission Agent KPIs
- Submission success rate > 95%
- Average submission time < 10 minutes
- Zero missed deadlines
- Retry success rate > 80%
- Confirmation verification rate 100%

## Risk Mitigation

### Technical Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Portal API changes | High | Version monitoring, adapter abstraction |
| Rate limiting | Medium | Queue management, retry logic |
| Authentication failures | High | Credential rotation, fallback methods |
| Network failures | Medium | Retry logic, offline queueing |
| File size limits | Low | Pre-validation, compression |

### Operational Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Missed deadlines | Critical | Early warnings, manual override |
| Document errors | High | Multi-stage validation, preview |
| Incorrect submissions | High | Audit trail, rollback capability |
| Portal downtime | Medium | Status monitoring, rescheduling |

## Documentation Deliverables

1. **API Documentation** (OpenAPI/Swagger)
2. **User Guide** for dashboard usage
3. **Admin Guide** for submission agent configuration
4. **Runbook** for common operations
5. **Troubleshooting Guide** for error scenarios
6. **Architecture Decision Records** (ADRs)

## Next Steps

1. **Review and approve this plan**
2. **Set up development environment**
3. **Create project repositories**
4. **Begin Week 1: Backend API development**
5. **Schedule weekly progress reviews**

## Appendix

### Technology References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Tailwind CSS v4.1](https://tailwindcss.com/)
- [Playwright Automation](https://playwright.dev/)
- [SAM.gov API](https://open.gsa.gov/api/entity-api/)

### Estimated Resource Requirements
- **Development Team**: 2-3 full-stack developers
- **Timeline**: 11 weeks (concurrent phases)
- **Infrastructure**: Cloud hosting, database, storage
- **Third-party Services**: Portal API access, notification services

---

**Document Version**: 1.0
**Last Updated**: November 14, 2025
**Status**: Ready for Review
