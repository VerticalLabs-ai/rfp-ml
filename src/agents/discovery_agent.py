# Extends the RFPDiscoveryAgent class for end-to-end triage, Go/No-Go scoring, and output format

import os
import sys
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import asdict

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.paths import PathConfig

# Try import of GoNoGoEngine; it's optional and handled gracefully in methods
try:
    from decision.go_nogo_engine import GoNoGoEngine
except Exception:
    GoNoGoEngine = None


class RFPDiscoveryAgent:
    """Autonomous agent for RFP discovery, filtering, triage, Go/No-Go scoring, and output generation."""

    def __init__(self, config_path: Optional[str] = None, config_override: Optional[Dict] = None):
        """Initialize agent with config file or dict override."""
        self.config: Dict[str, Any] = {}
        if config_path and os.path.exists(config_path):
            with open(config_path, "r") as f:
                try:
                    self.config = json.load(f)
                except Exception:
                    self.config = {}
        if config_override:
            self.config.update(config_override)
        # Default values if missing in config
        self.triage_thresholds = self.config.get(
            "triage_thresholds",
            {
                "weights": {"cat": 0.25, "value": 0.25, "deadline": 0.25, "complexity": 0.25},
                "score_min": 60,
            },
        )
        self.output_directory = self.config.get(
            "output_directory", str(PathConfig.DATA_DIR / "discovered_rfps")
        )
        self.target_categories = self.config.get("target_categories", ["bottled_water", "construction", "delivery"])
        self.agent_version = self.config.get("agent_version", "v1.0.0")
        os.makedirs(self.output_directory, exist_ok=True)

    def discover_opportunities(self, days_window: int = 30, limit: int = 50, log_samples: int = 5, api_key: Optional[str] = None) -> pd.DataFrame:
        """
        Discover opportunities using registered plugins (SAM.gov, Local CSV).
        
        Args:
            days_window: How many days back to search
            limit: Maximum number of results to return
            log_samples: Number of samples to log (unused in API mode)
            api_key: Optional SAM.gov API key override
        """
        from src.agents.plugins import SAMGovPlugin, LocalCSVPlugin
        
        all_results = []
        
        # 1. Try SAM.gov API
        sam_plugin = SAMGovPlugin(api_key=api_key)
        try:
            print(f"Attempting discovery via {sam_plugin.name} (last {days_window} days, limit {limit})...")
            results = sam_plugin.search(days_back=days_window, limit=limit)
            if results:
                all_results.extend(results)
                print(f"Successfully fetched {len(results)} opportunities from {sam_plugin.name}.")
            else:
                print(f"No opportunities found via {sam_plugin.name}.")
        except Exception as e:
            print(f"Error during {sam_plugin.name} discovery: {e}")

        # 2. Fallback to CSV if API returned nothing
        if not all_results:
            print("Falling back to Local CSV Archive...")
            csv_plugin = LocalCSVPlugin()
            try:
                results = csv_plugin.search(days_back=days_window, limit=limit)
                if results:
                    all_results.extend(results)
                    print(f"Successfully fetched {len(results)} opportunities from {csv_plugin.name}.")
            except Exception as e:
                print(f"Error during {csv_plugin.name} discovery: {e}")

        df_api = pd.DataFrame(all_results)

        # 3. Common Processing (Cleaning & Enrichment)
        if df_api.empty:
            return df_api

        # Ensure required columns
        required_cols = ["title", "solicitation_number", "agency", "description", "response_deadline", "award_amount", "posted_date"]
        for col in required_cols:
            if col not in df_api.columns:
                df_api[col] = None

        # Clean award_amount
        def clean_amount(val):
            if pd.isna(val): return 0.0
            if isinstance(val, (int, float)): return float(val)
            try:
                return float(str(val).replace('$', '').replace(',', ''))
            except:
                return 0.0
        
        df_api["award_amount_clean"] = df_api["award_amount"].apply(clean_amount)
        
        # Calculate description length
        df_api["description_length"] = df_api["description"].fillna("").astype(str).apply(len)
        
        # Infer category
        def infer_category(row):
            text = (str(row.get("title", "")) + " " + str(row.get("description", ""))).lower()
            if "water" in text: return "bottled_water"
            if "construction" in text or "paving" in text: return "construction"
            if "delivery" in text: return "delivery"
            if "software" in text or "it" in text or "cloud" in text: return "IT"
            return "General"
        
        df_api["category"] = df_api.apply(infer_category, axis=1)
        
        # Convert dates
        df_api["response_deadline"] = pd.to_datetime(df_api["response_deadline"], errors='coerce')
        df_api["posted_date"] = pd.to_datetime(df_api["posted_date"], errors='coerce')
        
        return df_api

    def triage_rfps(self, df) -> pd.DataFrame:
        """
        Assign triage scores based on category match, contract value, urgency, and complexity.
        Returns filtered DataFrame with triage_score.
        """
        if df.empty:
            return df
            
        today = pd.Timestamp.now(tz='UTC')
        
        # Ensure timezone awareness for deadline if needed, or make both naive
        if 'response_deadline' in df.columns:
            # Convert to UTC if not already
            if df['response_deadline'].dt.tz is None:
                df['response_deadline'] = df['response_deadline'].dt.tz_localize('UTC')
            else:
                df['response_deadline'] = df['response_deadline'].dt.tz_convert('UTC')
        
        cat_match = df['category'].apply(lambda x: 1.0 if x in self.target_categories else 0.6)
        value_score = df['award_amount_clean'].fillna(0).apply(lambda x: min(max((x - 5000)/200000, 0), 1.0))
        
        # Calculate days to deadline
        days_to_deadline = (df['response_deadline'] - today).dt.days.fillna(0).clip(lower=0)
        
        deadline_score = days_to_deadline.apply(lambda x: 1.0 if x < 10 else 0.6 if x < 30 else 0.2)
        complexity_score = df['description_length'].fillna(0).apply(lambda x: min(x/5000, 1.0))
        
        weights = self.triage_thresholds.get("weights", {"cat":0.25, "value":0.25, "deadline":0.25, "complexity":0.25})
        
        composite = (weights["cat"]*cat_match + weights["value"]*value_score +
                     weights["deadline"]*deadline_score + weights["complexity"]*complexity_score)
        
        df['triage_score'] = (composite * 100).clip(0, 100).round(2)
        
        # Filter by score
        df = df[df['triage_score'] >= self.triage_thresholds.get("score_min", 60)]
        
        return df

    def evaluate_go_nogo(self, triaged_df: pd.DataFrame) -> pd.DataFrame:
        """Apply Go/No-Go engine for opportunity scoring and augment DataFrame with decision results.
        
        If the GoNoGoEngine is not available, raise ImportError so callers can fallback.
        """
        if GoNoGoEngine is None:
            raise ImportError("GoNoGoEngine unavailable, cannot score RFPs for Go/No-Go.")

        nogo_engine = GoNoGoEngine()
        results = []
        for _, row in triaged_df.iterrows():
            rfp_data = row.to_dict()
            try:
                decision = nogo_engine.analyze_rfp_opportunity(rfp_data)
                # Attempt to convert dataclass-like objects to dict, otherwise use __dict__ or mapping
                try:
                    decision_dict = asdict(decision)
                except Exception:
                    if hasattr(decision, "__dict__"):
                        decision_dict = decision.__dict__
                    elif isinstance(decision, dict):
                        decision_dict = decision
                    else:
                        # Fallback generic mapping
                        decision_dict = {k: getattr(decision, k, None) for k in dir(decision) if not k.startswith("__")}
            except Exception:
                decision_dict = {"recommendation": "error", "overall_score": -1, "confidence_level": 0, "justification": "engine_error"}
            
            full_row = rfp_data.copy()
            # Make sure decision keys don't override important source fields unexpectedly
            full_row.update(decision_dict)
            results.append(full_row)
            
        return pd.DataFrame(results)

    def export_outputs(self, df: pd.DataFrame, file_tag: str = "discovered_rfps") -> (str, str):
        """Save triaged and scored RFPs in both JSON and CSV formats, compatible with downstream bid engine."""
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = self.output_directory
        os.makedirs(out_dir, exist_ok=True)

        meta = {
            "discovery_timestamp": datetime.now().isoformat(),
            "agent_version": getattr(self, "agent_version", "v1.0.0"),
            "filter_criteria": getattr(self, "triage_thresholds", {}),
            "num_rfps": len(df),
        }
        # JSON
        output_json = {
            "metadata": meta,
            "rfps": df.to_dict(orient="records"),
        }
        json_path = os.path.join(out_dir, f"{file_tag}_{now}.json")
        with open(json_path, "w") as jf:
            json.dump(output_json, jf, indent=2, default=str)
        # CSV
        csv_path = os.path.join(out_dir, f"{file_tag}_{now}.csv")
        df.to_csv(csv_path, index=False)
        print(f"Exported JSON: {json_path}\nExported CSV: {csv_path}")
        return json_path, csv_path


# Basic triage function (kept outside of the class for simplicity)
def triage_basic(df: pd.DataFrame) -> pd.DataFrame:
    """Apply a simple triage scoring heuristic to a DataFrame of RFPs.
    
    Expects fields such as 'award_amount', 'response_deadline', 'posted_date', and 'description'.
    """
    score = []
    priority = []
    expl_list = []

    for _, row in df.iterrows():
        amt = row.get("award_amount", 0) if isinstance(row, dict) else row.award_amount if "award_amount" in row.index else 0

        # Compute lead_days safely
        lead_days = 0
        try:
            if ("response_deadline" in row and "posted_date" in row) or (
                hasattr(row, "response_deadline") and hasattr(row, "posted_date")
            ):
                rd = row.get("response_deadline", None) if isinstance(row, dict) else row.response_deadline
                pd_date = row.get("posted_date", None) if isinstance(row, dict) else row.posted_date
                if pd_date and rd:
                    lead_days = (pd.to_datetime(rd) - pd.to_datetime(pd_date)).days
        except Exception:
            lead_days = 0

        tri_score = 0
        expl = []

        if amt and 50000 <= amt <= 5000000:
            tri_score += 40
            expl.append("Award in preferred range")
        else:
            expl.append("Award out of preferred range")

        if lead_days and 15 <= lead_days <= 60:
            tri_score += 30
            expl.append("Deadline in preferred response window")
        else:
            expl.append("Deadline out of preferred window")

        complexity = 0
        try:
            desc = row.get("description", "") if isinstance(row, dict) else row.description if "description" in row.index else ""
            complexity = len(str(desc))
        except Exception:
            complexity = 0

        tri_score += min(complexity // 500, 10)
        expl.append(f"Complexity estimate: {complexity} chars")

        tri_score = min(max(int(tri_score), 0), 100)
        score.append(tri_score)
        priority.append("HIGH" if tri_score > 80 else "MEDIUM" if tri_score >= 50 else "LOW")
        expl_list.append(" | ".join(expl))

    df_out = df.copy()
    df_out["triage_score"] = score
    df_out["priority"] = priority
    df_out["score_explanation"] = expl_list
    return df_out


if __name__ == "__main__":
    config_path = str(PathConfig.SRC_DIR / "agents" / "discovery_config.json")

    agent = RFPDiscoveryAgent(config_path=config_path)

    # If the agent has a discover_opportunities method, use it; otherwise create a small sample DataFrame
    if hasattr(agent, "discover_opportunities"):
        try:
            df_rfps = agent.discover_opportunities(days_window=30, log_samples=2)
        except Exception as e:
            print(f"discover_opportunities failed: {e}")
            df_rfps = pd.DataFrame()
    else:
        # Create a sample DataFrame with plausible fields
        now = pd.Timestamp.now()
        sample = [
            {
                "id": 1,
                "title": "Water delivery",
                "award_amount": 100000,
                "posted_date": now - pd.Timedelta(days=10),
                "response_deadline": now + pd.Timedelta(days=20),
                "description": "Supply bottled water to several municipal locations.",
            },
            {
                "id": 2,
                "title": "Minor road construction",
                "award_amount": 2000000,
                "posted_date": now - pd.Timedelta(days=5),
                "response_deadline": now + pd.Timedelta(days=40),
                "description": "Paving and improvement of local roads. Includes traffic control and materials.",
            },
        ]
        df_rfps = pd.DataFrame(sample)

    if df_rfps is None or df_rfps.empty:
        print("No RFPs discovered.")
    else:
        # Apply triage scoring (simple version)
        df_triaged = triage_basic(df_rfps)
        print("Triage scoring applied.")

        # Try to use the agent's evaluate_go_nogo (which uses GoNoGoEngine if available).
        try:
            df_scored = agent.evaluate_go_nogo(df_triaged)
            print("Go/No-Go engine applied via agent.evaluate_go_nogo().")
        except Exception as e:
            # Fallback: derive decisions from triage_score
            print(f"Go/No-Go engine unavailable or failed: {e}. Using fallback logic.")
            g_scores = [int(r) for r in df_triaged["triage_score"].tolist()]
            threshold = agent.config.get("go_nogo_threshold", 60)
            g_decisions = ["go" if s > threshold else "no-go" for s in g_scores]
            g_justs = ["Fallback decision (no engine)" for _ in g_scores]
            df_triaged["go_nogo_decision"] = g_decisions
            df_triaged["go_nogo_score"] = g_scores
            df_triaged["decision_justification"] = g_justs
            df_scored = df_triaged

        print("Go/No-Go applied. Sample:")
        print(df_scored.head(2).to_string())

        # Save outputs in JSON/CSV format for downstream bid engine
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        outdir = agent.output_directory
        os.makedirs(outdir, exist_ok=True)
        csv_path = os.path.join(outdir, f"discovered_rfps_sample_{ts}.csv")
        json_path = os.path.join(outdir, f"discovered_rfps_sample_{ts}.json")

        df_scored.to_csv(csv_path, index=False)
        with open(json_path, "w") as jf:
            json.dump(df_scored.to_dict("records"), jf, indent=2, default=str)

        print(f"Saved CSV: {csv_path}\nSaved JSON: {json_path}")
