import logging
from datetime import timedelta
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

class ForecastingService:
    """
    Service for predicting future RFP opportunities based on historical data.
    Uses cyclical pattern analysis to identify recurring contracts.
    """

    def __init__(self, historical_data_path: str = None):
        self.data_path = historical_data_path

    def train_on_file(self, file_path: str) -> pd.DataFrame:
        """
        Load a CSV file and prepare it for forecasting.
        In a real system, this might train a model or build an index.
        For this MVP, we return a DataFrame of 'recurring patterns'.
        """
        # Load Data (using the same robust loading logic as the plugin)
        try:
            # Try default encoding
            df = pd.read_csv(file_path, low_memory=False)
        except UnicodeDecodeError:
             df = pd.read_csv(file_path, low_memory=False, encoding='latin1')

        # Normalize columns
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

        # Column Mapping
        column_map = {
            "department/ind.agency": "agency",
            "department": "agency",
            "posteddate": "posted_date",
            "posted": "posted_date"
        }
        df = df.rename(columns=column_map)

        # Required columns
        req_cols = ['agency', 'title', 'posted_date']
        for c in req_cols:
            if c not in df.columns:
                logger.error(f"Missing required column {c} in {file_path}. Found: {df.columns.tolist()}")
                return pd.DataFrame()

        # Date conversion
        df['posted_date'] = pd.to_datetime(df['posted_date'], errors='coerce')
        df = df.dropna(subset=['posted_date', 'title', 'agency'])

        return df

    def predict_upcoming_opportunities(self, df: pd.DataFrame, confidence_threshold: float = 0.7) -> list[dict[str, Any]]:
        """
        Identify recurring opportunities and predict their next release date.
        
        Algorithm:
        1. Group by Agency and Title (exact match for MVP, fuzzy later).
        2. Calculate time deltas between postings.
        3. If deltas are consistent (std dev low) and mean is ~365 days, predict next.
        """
        predictions = []

        # Simple grouping: Agency + First 20 chars of Title (to catch "Annual Maintenance 2023" vs "2024")
        df['title_stub'] = df['title'].str.slice(0, 20).str.lower()

        grouped = df.groupby(['agency', 'title_stub'])

        for (agency, _title_stub), group in grouped:
            if len(group) < 2:
                continue

            dates = group['posted_date'].sort_values()
            deltas = dates.diff().dt.days.dropna()

            mean_delta = deltas.mean()
            std_delta = deltas.std()

            # Check for annual cycle (approx 365 days, allow variance)
            is_annual = 300 <= mean_delta <= 420
            consistency = 1.0

            if len(deltas) > 1 and std_delta > 30:
                consistency = 0.5

            if is_annual:
                last_date = dates.iloc[-1]
                next_date = last_date + timedelta(days=mean_delta)

                # Calculate confidence
                confidence = 0.8 * consistency
                if len(group) > 3:
                    confidence += 0.1

                if confidence >= confidence_threshold:
                    predictions.append({
                        "predicted_title": group.iloc[-1]['title'],  # Use most recent title
                        "agency": agency,
                        "predicted_date": next_date.strftime("%Y-%m-%d"),
                        "confidence": round(confidence, 2),
                        "basis": f"Based on {len(group)} historical postings with avg gap of {int(mean_delta)} days",
                        "last_posted": last_date.strftime("%Y-%m-%d")
                    })

        return predictions

# Test block
if __name__ == "__main__":
    # Create dummy data for testing
    data = {
        "agency": ["Dept of Water"] * 3,
        "title": ["Annual Water Supply 2021", "Annual Water Supply 2022", "Annual Water Supply 2023"],
        "posted_date": ["2021-01-15", "2022-01-20", "2023-01-18"]
    }
    df = pd.DataFrame(data)
    service = ForecastingService()
    preds = service.predict_upcoming_opportunities(df)
    print(preds)
