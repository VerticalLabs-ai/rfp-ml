import json
import logging
import os
import re
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
            "meta": self.meta,
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
        self.output_dir = output_dir or str(
            PathConfig.DATA_DIR / "post_award_checklists"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger = logger

    def generate_from_bid_document(
        self, rfp_data: dict[str, Any], bid_document_content: dict[str, Any]
    ) -> ComplianceChecklist:
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
        compliance_matrix = bid_document_content.get("sections", {}).get(
            "compliance_matrix", {}
        )
        requirements_and_responses = compliance_matrix.get(
            "requirements_and_responses", []
        )

        for i, req in enumerate(requirements_and_responses):
            checklist_items.append(
                ChecklistItem(
                    id=f"REQ-{rfp_id}-{i + 1}",
                    description=f"Ensure ongoing compliance with: {req.get('requirement_text', '')}",
                    status="pending",
                    assigned_to="Project Manager",  # Default assignment
                    meta={
                        "source": "compliance_matrix",
                        "original_requirement_id": req.get("requirement_id"),
                        "compliance_status_pre_award": req.get("compliance_status"),
                    },
                )
            )

        # Extract deliverables/milestones from technical approach
        technical_approach = bid_document_content.get("sections", {}).get(
            "technical_approach", {}
        )

        extracted_tasks = self._extract_tasks_from_technical_approach(
            technical_approach, rfp_id
        )

        # Fallback to common post-award tasks if nothing extracted
        if not extracted_tasks:
            common_post_award_tasks = [
                "Conduct Project Kick-off Meeting with Agency",
                "Finalize Project Management Plan",
                "Establish Reporting Cadence and Channels",
                "Onboard Key Personnel",
                "Procure Initial Materials/Resources",
                "Set up Financial Tracking and Invoicing System",
                "Submit First Progress Report (within 30 days)",
                "Monitor Contract Performance Metrics",
            ]
            extracted_tasks = [
                {
                    "description": task_desc,
                    "due_date_offset": (i + 1) * 7,  # days from now
                    "priority": "high" if i < 2 else "medium",
                }
                for i, task_desc in enumerate(common_post_award_tasks)
            ]

        for i, task_data in enumerate(extracted_tasks):
            checklist_items.append(
                ChecklistItem(
                    id=f"POSTAWARD-{rfp_id}-{i + 1}",
                    description=task_data.get("description", "Task"),
                    status="pending",
                    assigned_to=task_data.get("assigned_to", "Project Manager"),
                    due_date=datetime.utcnow()
                    + timedelta(days=task_data.get("due_date_offset", (i + 1) * 7)),
                    meta={
                        "source": task_data.get("source", "technical_approach"),
                        "priority": task_data.get("priority", "medium"),
                        **task_data.get("meta", {}),
                    },
                )
            )

        # Summary statistics
        total_items = len(checklist_items)
        pending_items = len(
            [item for item in checklist_items if item.status == "pending"]
        )

        summary = {
            "total_items": total_items,
            "pending_items": pending_items,
            "completed_items": total_items - pending_items,  # Simplistic for now
            "last_updated": datetime.utcnow().isoformat(),
        }

        return ComplianceChecklist(
            rfp_id=rfp_id,
            bid_document_id=bid_document_content.get(
                "bid_id"
            ),  # Assuming bid_document_content has bid_id
            items=checklist_items,
            summary=summary,
        )

    def _extract_tasks_from_technical_approach(
        self, technical_approach: dict[str, Any] | str, rfp_id: str
    ) -> list[dict[str, Any]]:
        """
        Extract tasks, deliverables, and milestones from technical approach section.

        Args:
            technical_approach: Technical approach section (dict or string)
            rfp_id: RFP ID for metadata

        Returns:
            List of task dictionaries with description, due_date_offset, priority, etc.
        """
        tasks: list[dict[str, Any]] = []

        # Handle string format (markdown/text)
        if isinstance(technical_approach, str):
            tasks.extend(self._parse_tasks_from_text(technical_approach))
            return tasks

        # Handle dict format
        if not isinstance(technical_approach, dict):
            return tasks

        # Extract explicit deliverables list
        deliverables = technical_approach.get("deliverables", [])
        if isinstance(deliverables, list) and deliverables:
            for i, deliverable in enumerate(deliverables):
                if isinstance(deliverable, str):
                    tasks.append(
                        {
                            "description": f"Deliver: {deliverable}",
                            "due_date_offset": (i + 1) * 14,  # 2 weeks apart
                            "priority": "high",
                            "source": "technical_approach_deliverables",
                            "meta": {"deliverable_index": i},
                        }
                    )
                elif isinstance(deliverable, dict):
                    tasks.append(
                        {
                            "description": deliverable.get(
                                "name", deliverable.get("description", "Deliverable")
                            ),
                            "due_date_offset": deliverable.get(
                                "days_offset", (i + 1) * 14
                            ),
                            "priority": deliverable.get("priority", "high"),
                            "assigned_to": deliverable.get("assigned_to"),
                            "source": "technical_approach_deliverables",
                            "meta": {"deliverable_id": deliverable.get("id")},
                        }
                    )

        # Extract tasks from project_management text
        project_management = technical_approach.get("project_management", "")
        if project_management:
            if isinstance(project_management, str):
                parsed_tasks = self._parse_tasks_from_text(project_management)
                # Offset these tasks to start after deliverables
                for task in parsed_tasks:
                    task["due_date_offset"] = (
                        task.get("due_date_offset", 0) + len(deliverables) * 14
                    )
                tasks.extend(parsed_tasks)

        # Extract timeline milestones if available
        timeline = technical_approach.get("timeline", {})
        if isinstance(timeline, dict):
            milestones = timeline.get("milestones", [])
            if isinstance(milestones, list):
                for milestone in milestones:
                    if isinstance(milestone, dict):
                        tasks.append(
                            {
                                "description": milestone.get(
                                    "name", milestone.get("description", "Milestone")
                                ),
                                "due_date_offset": milestone.get("days_offset", 0),
                                "priority": milestone.get("priority", "medium"),
                                "source": "technical_approach_timeline",
                                "meta": {"milestone_id": milestone.get("id")},
                            }
                        )

        return tasks

    def _parse_tasks_from_text(self, text: str) -> list[dict[str, Any]]:
        """
        Parse tasks/milestones from text content using pattern matching.

        Looks for:
        - Bullet points with action verbs
        - Numbered lists
        - Phrases like "within X days", "by week X", etc.
        """
        tasks: list[dict[str, Any]] = []

        if not text or not isinstance(text, str):
            return tasks

        # Pattern 1: Bullet points (-, *, •)
        bullet_pattern = r"[-*•]\s+([A-Z][^•\n]{10,200})"
        bullet_matches = re.findall(bullet_pattern, text, re.MULTILINE)

        for i, match in enumerate(bullet_matches[:10]):  # Limit to 10 tasks
            task_text = match.strip()
            # Skip if it's too short or looks like a header
            if len(task_text) < 15 or task_text.endswith(":"):
                continue

            # Extract time references
            days_offset = self._extract_time_reference(task_text)

            tasks.append(
                {
                    "description": task_text,
                    "due_date_offset": days_offset or (i + 1) * 7,
                    "priority": "high" if i < 3 else "medium",
                    "source": "technical_approach_text",
                }
            )

        # Pattern 2: Numbered lists
        numbered_pattern = r"\d+[.)]\s+([A-Z][^0-9\n]{10,200})"
        numbered_matches = re.findall(numbered_pattern, text, re.MULTILINE)

        for i, match in enumerate(numbered_matches[:10]):
            task_text = match.strip()
            if len(task_text) < 15 or task_text.endswith(":"):
                continue

            days_offset = self._extract_time_reference(task_text)

            tasks.append(
                {
                    "description": task_text,
                    "due_date_offset": days_offset or (len(bullet_matches) + i + 1) * 7,
                    "priority": "medium",
                    "source": "technical_approach_text",
                }
            )

        return tasks

    def _extract_time_reference(self, text: str) -> int | None:
        """
        Extract time reference from text (e.g., "within 30 days", "by week 2").

        Returns:
            Number of days offset, or None if not found
        """
        # Pattern: "within X days/weeks/months"
        within_pattern = r"within\s+(\d+)\s+(day|week|month)s?"
        match = re.search(within_pattern, text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            unit = match.group(2).lower()
            if unit == "day":
                return value
            elif unit == "week":
                return value * 7
            elif unit == "month":
                return value * 30

        # Pattern: "by week X" or "week X"
        week_pattern = r"week\s+(\d+)"
        match = re.search(week_pattern, text, re.IGNORECASE)
        if match:
            week_num = int(match.group(1))
            return week_num * 7

        # Pattern: "day X" or "by day X"
        day_pattern = r"day\s+(\d+)"
        match = re.search(day_pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return None

    def export_checklist(
        self, checklist: ComplianceChecklist, output_format: str = "json"
    ) -> str:
        """
        Export the compliance checklist to a file.
        """
        filename_base = f"post_award_checklist_{checklist.rfp_id}_{checklist.generated_at.strftime('%Y%m%d%H%M%S')}"

        if output_format.lower() == "json":
            filepath = os.path.join(self.output_dir, f"{filename_base}.json")
            with open(filepath, "w") as f:
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
