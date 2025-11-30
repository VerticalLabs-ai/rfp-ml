import os
from typing import Any

import pandas as pd

from src.agents.plugins.base_plugin import DataSourcePlugin
from src.config.paths import PathConfig


class LocalCSVPlugin(DataSourcePlugin):
    """Plugin for fetching opportunities from a local CSV file (Archived Data)."""

    def __init__(self, file_path: str = None):
        """
        Args:
            file_path: Optional specific path to CSV. Defaults to FY2025_archived_opportunities.csv in data/raw.
        """
        self.file_path = file_path or (PathConfig.DATA_DIR / "raw" / "FY2025_archived_opportunities.csv")

    @property
    def name(self) -> str:
        return "Local CSV Archive"

    def search(self, days_back: int = 30, limit: int = 50, **kwargs) -> list[dict[str, Any]]:
        """
        Reads from local CSV. Note: 'days_back' is used to filter if possible,
        otherwise we return a sample of 'limit'.
        """
        print(f"LocalCSVPlugin: Reading from {self.file_path}...")

        if not os.path.exists(self.file_path):
            print(f"Warning: Data file {self.file_path} not found.")
            return []

        try:
            # Read CSV with fallback encodings
            encodings = ['utf-8', 'cp1252', 'latin1', 'iso-8859-1']
            df = None

            for encoding in encodings:
                try:
                    df = pd.read_csv(self.file_path, low_memory=False, encoding=encoding)
                    # print(f"Successfully read CSV with encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    continue

            if df is None:
                print(f"Failed to read CSV with any of the attempted encodings: {encodings}")
                return []

            # Normalize column names
            df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]

            # Map columns
            column_mapping = {
                "solicitation_number": "solicitation_number",
                "solicitation": "solicitation_number",
                "solicitation#": "solicitation_number",
                "notice_id": "solicitation_number",
                "title": "title",
                "opportunity_title": "title",
                "agency": "agency",
                "department/ind._agency": "agency",
                "department": "agency",
                "office": "office",
                "posted_date": "posted_date",
                "posted": "posted_date",
                "response_deadline": "response_deadline",
                "response_date": "response_deadline",
                "deadline": "response_deadline",
                "description": "description",
                "award_amount": "award_amount",
                "amount": "award_amount",
                "naics_code": "naics_code",
                "naics": "naics_code",
                "link": "url",
                "url": "url"
            }

            df_mapped = df.rename(columns=column_mapping)

            # Keep only relevant columns
            valid_cols = [c for c in df_mapped.columns if c in column_mapping.values() or c in [
                "solicitation_number", "title", "agency", "office", "posted_date",
                "response_deadline", "description", "award_amount", "naics_code", "url"
            ]]
            df_mapped = df_mapped[valid_cols]

            # --- Mock Filter Logic ---
            # In a real scenario, we would filter by date here.
            # For now, we stick to the original logic of sampling 'limit' rows
            # to simulate discovery.
            if len(df_mapped) > limit:
                df_mapped = df_mapped.sample(n=limit).reset_index(drop=True)

            # Convert to list of dicts
            results = df_mapped.to_dict(orient="records")

            # Ensure 'source' field
            for r in results:
                r["source"] = "local_csv"

            return results

        except Exception as e:
            print(f"Error reading CSV data: {e}")
            return []
