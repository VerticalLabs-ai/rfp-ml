"""
Bid Pricing Table Generator
Generates detailed pricing breakdowns for multi-year, multi-deliverable RFP bids.
"""
import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CostCategory(Enum):
    """Categories of costs in a bid"""
    LABOR = "Labor"
    DESIGN = "Design"
    DEVELOPMENT = "Development"
    CONTENT = "Content"
    PHOTO_SOURCING = "Photo/Media Sourcing"
    HOSTING = "Hosting & Infrastructure"
    MAINTENANCE = "Maintenance & Support"
    PROJECT_MANAGEMENT = "Project Management"
    QUALITY_ASSURANCE = "Quality Assurance"
    TRAINING = "Training & Documentation"
    CONTINGENCY = "Contingency"
    OTHER = "Other"


@dataclass
class LineItem:
    """A single line item in the pricing table"""
    category: str
    description: str
    unit: str = "Fixed"
    quantity: float = 1.0
    unit_price: float = 0.0
    total: float = 0.0
    is_optional: bool = False
    notes: str = ""

    def calculate_total(self) -> float:
        self.total = self.quantity * self.unit_price
        return self.total


@dataclass
class YearlyBudget:
    """Budget breakdown for a single year"""
    year: int
    year_label: str  # e.g., "Year 1", "Year 4 (Optional)"
    is_optional: bool = False
    line_items: list[LineItem] = field(default_factory=list)
    subtotal: float = 0.0

    def calculate_subtotal(self) -> float:
        self.subtotal = sum(item.total for item in self.line_items)
        return self.subtotal


@dataclass
class DeliverableBudget:
    """Budget for a single deliverable (e.g., one website)"""
    deliverable_id: str
    deliverable_name: str
    description: str = ""
    yearly_budgets: list[YearlyBudget] = field(default_factory=list)
    total: float = 0.0

    def calculate_total(self) -> float:
        self.total = sum(yb.subtotal for yb in self.yearly_budgets if not yb.is_optional)
        return self.total

    def calculate_total_with_optional(self) -> float:
        return sum(yb.subtotal for yb in self.yearly_budgets)


@dataclass
class BidPricingTable:
    """Complete bid pricing table"""
    rfp_id: str
    rfp_title: str
    company_name: str
    generated_at: datetime = field(default_factory=datetime.utcnow)
    deliverables: list[DeliverableBudget] = field(default_factory=list)
    grand_total: float = 0.0
    grand_total_with_optional: float = 0.0
    notes: list[str] = field(default_factory=list)

    def calculate_totals(self):
        for deliverable in self.deliverables:
            for yearly in deliverable.yearly_budgets:
                for item in yearly.line_items:
                    item.calculate_total()
                yearly.calculate_subtotal()
            deliverable.calculate_total()

        self.grand_total = sum(d.total for d in self.deliverables)
        self.grand_total_with_optional = sum(d.calculate_total_with_optional() for d in self.deliverables)


class PricingTableGenerator:
    """
    Generates detailed pricing tables for RFP bids.
    Supports multi-year, multi-deliverable breakdowns with optional items.
    """

    # Default hourly rates by role
    DEFAULT_RATES = {
        "project_manager": 150.0,
        "senior_developer": 175.0,
        "developer": 125.0,
        "designer": 135.0,
        "content_writer": 85.0,
        "qa_engineer": 110.0,
    }

    def __init__(self, rates: dict[str, float] | None = None):
        self.rates = rates or self.DEFAULT_RATES
        self.logger = logging.getLogger(__name__)

    def generate_website_pricing(
        self,
        rfp_data: dict[str, Any],
        company_profile: dict[str, Any],
        num_websites: int = 3,
        base_years: int = 3,
        optional_years: int = 2,
        base_budget_per_site: float = 50000.0,
    ) -> BidPricingTable:
        """
        Generate a pricing table for a multi-website, multi-year project.

        Args:
            rfp_data: RFP information
            company_profile: Company information
            num_websites: Number of websites to build
            base_years: Number of base contract years (1-3)
            optional_years: Number of optional years (4-5)
            base_budget_per_site: Base budget per website for Year 1
        """
        pricing_table = BidPricingTable(
            rfp_id=rfp_data.get("rfp_id", ""),
            rfp_title=rfp_data.get("title", "Website Development Project"),
            company_name=company_profile.get("company_name", ""),
        )

        # Website names - can be customized based on RFP
        website_names = [
            "Homeland Security Website",
            "Public Safety Website",
            "Regional Services Website",
        ]

        for i in range(num_websites):
            website_id = f"website_{i+1}"
            website_name = website_names[i] if i < len(website_names) else f"Website {i+1}"

            deliverable = self._generate_website_deliverable(
                deliverable_id=website_id,
                deliverable_name=website_name,
                base_years=base_years,
                optional_years=optional_years,
                base_budget=base_budget_per_site,
                is_first_website=(i == 0),  # First website has more setup costs
            )
            pricing_table.deliverables.append(deliverable)

        # Add notes
        pricing_table.notes = [
            "Year 1 includes full design, development, and deployment",
            "Years 2-3 include maintenance, hosting, and minor updates",
            "Years 4-5 are optional renewal years at client discretion",
            "Photo/Media sourcing is optional and billed as needed",
            "All prices are in USD and exclude applicable taxes",
        ]

        pricing_table.calculate_totals()
        return pricing_table

    def _generate_website_deliverable(
        self,
        deliverable_id: str,
        deliverable_name: str,
        base_years: int,
        optional_years: int,
        base_budget: float,
        is_first_website: bool = False,
    ) -> DeliverableBudget:
        """Generate budget for a single website across all years."""
        deliverable = DeliverableBudget(
            deliverable_id=deliverable_id,
            deliverable_name=deliverable_name,
            description=f"Development and maintenance of {deliverable_name}",
        )

        # Year 1 - Initial Development (most intensive)
        year1_budget = self._generate_year1_budget(
            base_budget,
            is_first_website
        )
        deliverable.yearly_budgets.append(year1_budget)

        # Years 2-3 - Maintenance
        for year in range(2, base_years + 1):
            maintenance_budget = self._generate_maintenance_budget(
                year=year,
                base_budget=base_budget * 0.15,  # 15% of initial for maintenance
                is_optional=False,
            )
            deliverable.yearly_budgets.append(maintenance_budget)

        # Years 4-5 - Optional Renewal
        for year in range(base_years + 1, base_years + optional_years + 1):
            optional_budget = self._generate_maintenance_budget(
                year=year,
                base_budget=base_budget * 0.15,
                is_optional=True,
            )
            deliverable.yearly_budgets.append(optional_budget)

        return deliverable

    def _generate_year1_budget(
        self,
        base_budget: float,
        is_first_website: bool
    ) -> YearlyBudget:
        """Generate Year 1 budget (initial development)."""
        budget = YearlyBudget(
            year=1,
            year_label="Year 1 (Initial Development)",
            is_optional=False,
        )

        # Distribute budget across categories
        # First website has additional setup/discovery costs
        setup_multiplier = 1.2 if is_first_website else 1.0

        budget.line_items = [
            LineItem(
                category=CostCategory.PROJECT_MANAGEMENT.value,
                description="Project planning, coordination, and oversight",
                unit="Hours",
                quantity=80 * setup_multiplier,
                unit_price=self.rates["project_manager"],
            ),
            LineItem(
                category=CostCategory.DESIGN.value,
                description="UI/UX design, wireframes, mockups",
                unit="Hours",
                quantity=120,
                unit_price=self.rates["designer"],
            ),
            LineItem(
                category=CostCategory.DEVELOPMENT.value,
                description="Frontend and backend development",
                unit="Hours",
                quantity=200,
                unit_price=self.rates["senior_developer"],
            ),
            LineItem(
                category=CostCategory.DEVELOPMENT.value,
                description="Additional development support",
                unit="Hours",
                quantity=100,
                unit_price=self.rates["developer"],
            ),
            LineItem(
                category=CostCategory.CONTENT.value,
                description="Content creation and migration",
                unit="Hours",
                quantity=60,
                unit_price=self.rates["content_writer"],
            ),
            LineItem(
                category=CostCategory.PHOTO_SOURCING.value,
                description="Stock photography and media assets",
                unit="Fixed",
                quantity=1,
                unit_price=2500.0,
                is_optional=True,
                notes="Optional - can use client-provided assets",
            ),
            LineItem(
                category=CostCategory.QUALITY_ASSURANCE.value,
                description="Testing, QA, and bug fixes",
                unit="Hours",
                quantity=60,
                unit_price=self.rates["qa_engineer"],
            ),
            LineItem(
                category=CostCategory.TRAINING.value,
                description="Staff training and documentation",
                unit="Hours",
                quantity=20,
                unit_price=self.rates["project_manager"],
            ),
            LineItem(
                category=CostCategory.HOSTING.value,
                description="Cloud hosting and infrastructure (Year 1)",
                unit="Annual",
                quantity=1,
                unit_price=6000.0,
            ),
            LineItem(
                category=CostCategory.CONTINGENCY.value,
                description="Contingency (10%)",
                unit="Fixed",
                quantity=1,
                unit_price=base_budget * 0.10,
            ),
        ]

        return budget

    def _generate_maintenance_budget(
        self,
        year: int,
        base_budget: float,
        is_optional: bool,
    ) -> YearlyBudget:
        """Generate maintenance year budget."""
        label = f"Year {year}"
        if is_optional:
            label += " (Optional)"

        budget = YearlyBudget(
            year=year,
            year_label=label,
            is_optional=is_optional,
        )

        budget.line_items = [
            LineItem(
                category=CostCategory.MAINTENANCE.value,
                description="Ongoing maintenance and support",
                unit="Hours",
                quantity=40,
                unit_price=self.rates["developer"],
            ),
            LineItem(
                category=CostCategory.HOSTING.value,
                description="Cloud hosting and infrastructure",
                unit="Annual",
                quantity=1,
                unit_price=6000.0,
            ),
            LineItem(
                category=CostCategory.PROJECT_MANAGEMENT.value,
                description="Account management and coordination",
                unit="Hours",
                quantity=20,
                unit_price=self.rates["project_manager"],
            ),
            LineItem(
                category=CostCategory.CONTENT.value,
                description="Content updates (as needed)",
                unit="Hours",
                quantity=20,
                unit_price=self.rates["content_writer"],
                is_optional=True,
                notes="Billed as used",
            ),
        ]

        return budget

    def to_csv(self, pricing_table: BidPricingTable) -> str:
        """
        Export pricing table to CSV format.

        Returns:
            CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Deliverable",
            "Year",
            "Category",
            "Description",
            "Unit",
            "Quantity",
            "Unit Price ($)",
            "Total ($)",
            "Optional",
            "Notes",
        ])

        # Data rows
        for deliverable in pricing_table.deliverables:
            for yearly in deliverable.yearly_budgets:
                for item in yearly.line_items:
                    writer.writerow([
                        deliverable.deliverable_name,
                        yearly.year_label,
                        item.category,
                        item.description,
                        item.unit,
                        item.quantity,
                        f"{item.unit_price:.2f}",
                        f"{item.total:.2f}",
                        "Yes" if item.is_optional or yearly.is_optional else "No",
                        item.notes,
                    ])

                # Yearly subtotal row
                writer.writerow([
                    deliverable.deliverable_name,
                    yearly.year_label,
                    "",
                    "SUBTOTAL",
                    "",
                    "",
                    "",
                    f"{yearly.subtotal:.2f}",
                    "Yes" if yearly.is_optional else "No",
                    "",
                ])

            # Deliverable total row
            writer.writerow([
                deliverable.deliverable_name,
                "",
                "",
                "DELIVERABLE TOTAL",
                "",
                "",
                "",
                f"{deliverable.total:.2f}",
                "",
                "",
            ])

        # Grand totals
        writer.writerow([])
        writer.writerow([
            "",
            "",
            "",
            "GRAND TOTAL (Base Contract)",
            "",
            "",
            "",
            f"{pricing_table.grand_total:.2f}",
            "",
            "",
        ])
        writer.writerow([
            "",
            "",
            "",
            "GRAND TOTAL (Including Optional Years)",
            "",
            "",
            "",
            f"{pricing_table.grand_total_with_optional:.2f}",
            "",
            "",
        ])

        return output.getvalue()

    def to_dict(self, pricing_table: BidPricingTable) -> dict[str, Any]:
        """Convert pricing table to dictionary for JSON serialization."""
        return {
            "rfp_id": pricing_table.rfp_id,
            "rfp_title": pricing_table.rfp_title,
            "company_name": pricing_table.company_name,
            "generated_at": pricing_table.generated_at.isoformat(),
            "deliverables": [
                {
                    "id": d.deliverable_id,
                    "name": d.deliverable_name,
                    "description": d.description,
                    "total": d.total,
                    "total_with_optional": d.calculate_total_with_optional(),
                    "yearly_budgets": [
                        {
                            "year": yb.year,
                            "year_label": yb.year_label,
                            "is_optional": yb.is_optional,
                            "subtotal": yb.subtotal,
                            "line_items": [
                                {
                                    "category": li.category,
                                    "description": li.description,
                                    "unit": li.unit,
                                    "quantity": li.quantity,
                                    "unit_price": li.unit_price,
                                    "total": li.total,
                                    "is_optional": li.is_optional,
                                    "notes": li.notes,
                                }
                                for li in yb.line_items
                            ],
                        }
                        for yb in d.yearly_budgets
                    ],
                }
                for d in pricing_table.deliverables
            ],
            "grand_total": pricing_table.grand_total,
            "grand_total_with_optional": pricing_table.grand_total_with_optional,
            "notes": pricing_table.notes,
        }


def create_pricing_table_generator(
    custom_rates: dict[str, float] | None = None,
) -> PricingTableGenerator:
    """Factory function to create a pricing table generator."""
    return PricingTableGenerator(rates=custom_rates)


if __name__ == "__main__":
    # Test the pricing table generator
    generator = create_pricing_table_generator()

    test_rfp = {
        "rfp_id": "RFP-TEST-001",
        "title": "3 Multi-Year Public Facing Regional Websites",
    }

    test_company = {
        "company_name": "IBYTE Enterprises, LLC",
    }

    pricing_table = generator.generate_website_pricing(
        rfp_data=test_rfp,
        company_profile=test_company,
        num_websites=3,
        base_years=3,
        optional_years=2,
    )

    print(f"Grand Total (Base): ${pricing_table.grand_total:,.2f}")
    print(f"Grand Total (With Optional): ${pricing_table.grand_total_with_optional:,.2f}")
    print("\nCSV Preview:")
    print(generator.to_csv(pricing_table)[:2000])
