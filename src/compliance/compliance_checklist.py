import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

# Import path configuration
from src.config.paths import PathConfig

logger = logging.getLogger(__name__)

@dataclass
class ChecklistItem:
    """
    Represents a single item in the post-award compliance checklist.
    """
    id: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, waived
    assigned_to: str | None = None
    due_date: datetime | None = None
    notes: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "notes": self.notes,
            "meta": self.meta
        }

@dataclass
class ComplianceChecklist:
    """
    Post-award compliance checklist generated from RFP requirements.
    """
    rfp_id: str
    bid_document_id: str | None = None
    generated_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "draft"  # draft, active, complete
    items: list[ChecklistItem] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


class ComplianceChecklistGenerator:
    """
    Generates a post-award compliance checklist based on the final bid document.
    """
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or str(PathConfig.DATA_DIR / "post_award_checklists")
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger = logger

    def generate_from_bid_document(self, rfp_data: dict[str, Any], bid_document_content: dict[str, Any]) -> ComplianceChecklist:
        """
        Generate a compliance checklist from a finalized bid document's content.

        Args:
            rfp_data: The original RFP data.
            bid_document_content: The `content` section of the generated bid document,
                                  specifically containing `compliance_matrix` and `technical_approach`.

        Returns:
            A ComplianceChecklist object.
        """
        rfp_id = rfp_data.get("rfp_id", "unknown_rfp")
        checklist_items: list[ChecklistItem] = []

        # Extract requirements from compliance matrix
        compliance_matrix = bid_document_content.get("sections", {}).get("compliance_matrix", {})
        requirements_and_responses = compliance_matrix.get("requirements_and_responses", [])

        for i, req in enumerate(requirements_and_responses):
            checklist_items.append(ChecklistItem(
                id=f"REQ-{rfp_id}-{i+1}",
                description=f"Ensure ongoing compliance with: {req.get('requirement_text', '')}",
                status="pending",
                assigned_to="Project Manager", # Default assignment
                meta={
                    "source": "compliance_matrix",
                    "original_requirement_id": req.get("requirement_id"),
                    "compliance_status_pre_award": req.get("compliance_status")
                }
            ))

        # Extract deliverables/milestones from technical approach (mock for now)
        _technical_approach = bid_document_content.get("sections", {}).get("technical_approach", {})

        # Example: if there's a Gantt chart, extract its tasks
        # For now, manually create a few common post-award tasks
        common_post_award_tasks = [
            "Conduct Project Kick-off Meeting with Agency",
            "Finalize Project Management Plan",
            "Establish Reporting Cadence and Channels",
            "Onboard Key Personnel",
            "Procure Initial Materials/Resources",
            "Set up Financial Tracking and Invoicing System",
            "Submit First Progress Report (within 30 days)",
            "Monitor Contract Performance Metrics"
        ]

        for i, task_desc in enumerate(common_post_award_tasks):
            checklist_items.append(ChecklistItem(
                id=f"POSTAWARD-{rfp_id}-{i+1}",
                description=task_desc,
                status="pending",
                assigned_to="Project Manager",
                due_date=datetime.utcnow() + timedelta(days= (i+1) * 7), # Mock due dates
                meta={
                    "source": "post_award_template",
                    "priority": "high" if i < 2 else "medium"
                }
            ))

        # Summary statistics
        total_items = len(checklist_items)
        pending_items = len([item for item in checklist_items if item.status == "pending"])

        summary = {
            "total_items": total_items,
            "pending_items": pending_items,
            "completed_items": total_items - pending_items, # Simplistic for now
            "last_updated": datetime.utcnow().isoformat()
        }

        return ComplianceChecklist(
            rfp_id=rfp_id,
            bid_document_id=bid_document_content.get("bid_id"), # Assuming bid_document_content has bid_id
            items=checklist_items,
            summary=summary
        )

    def export_checklist(self, checklist: ComplianceChecklist, output_format: str = "json") -> str:
        """
        Export the compliance checklist to a file.
        """
        filename_base = f"post_award_checklist_{checklist.rfp_id}_{checklist.generated_at.strftime('%Y%m%d%H%M%S')}"

        if output_format.lower() == "json":
            filepath = os.path.join(self.output_dir, f"{filename_base}.json")
            with open(filepath, 'w') as f:
                json.dump(asdict(checklist), f, indent=2, default=str)
        elif output_format.lower() == "csv":
            filepath = os.path.join(self.output_dir, f"{filename_base}.csv")
            # Convert to pandas DataFrame for CSV export
            df_items = pd.DataFrame([asdict(item) for item in checklist.items])
            df_items.to_csv(filepath, index=False)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        self.logger.info(f"Exported compliance checklist to: {filepath}")
        return filepath

# Lazy factory for compliance checklist generator
_compliance_checklist_generator_instance: ComplianceChecklistGenerator | None = None


def get_compliance_checklist_generator() -> ComplianceChecklistGenerator:
    """Get or create the compliance checklist generator instance."""
    global _compliance_checklist_generator_instance
    if _compliance_checklist_generator_instance is None:
        _compliance_checklist_generator_instance = ComplianceChecklistGenerator()
    return _compliance_checklist_generator_instance


class _LazyGenerator:
    """Lazy wrapper for backward compatibility."""

    def __getattr__(self, name):
        return getattr(get_compliance_checklist_generator(), name)


# Backward-compatible alias (use get_compliance_checklist_generator() for new code)
compliance_checklist_generator = _LazyGenerator()
