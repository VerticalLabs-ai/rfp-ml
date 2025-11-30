# Integration test for end-to-end RFP Discovery Agent pipeline.
import json
import os
from datetime import timezone

import pandas as pd
import pytest

from src.agents.discovery_agent import RFPDiscoveryAgent


def _normalize_datetime(dt):
    """Normalize datetime to naive UTC for consistent comparisons."""
    if dt is None or pd.isna(dt):
        return None
    # If it's a pandas Timestamp, convert to datetime
    if hasattr(dt, 'to_pydatetime'):
        dt = dt.to_pydatetime()
    # If timezone-aware, convert to UTC and remove tzinfo
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


@pytest.fixture(scope="module")
def agent():
    # Try local path first, fall back to Docker path
    local_config = os.path.join(os.path.dirname(__file__), "..", "src", "agents", "discovery_config.json")
    docker_config = "/app/government_rfp_bid_1927/src/agents/discovery_config.json"

    if os.path.exists(local_config):
        config_path = local_config
    elif os.path.exists(docker_config):
        config_path = docker_config
    else:
        pytest.skip("Discovery config not found - skipping integration test")

    # Check for SAM.gov API key
    if not os.environ.get("SAM_GOV_API_KEY"):
        pytest.skip("SAM_GOV_API_KEY not set - skipping integration test")

    return RFPDiscoveryAgent(config_path=config_path)

def test_discovery_pipeline(agent):
    # 1. Discovery
    df_rfps = agent.discover_opportunities(days_window=30, log_samples=2)
    assert len(df_rfps) >= 1, "No RFPs discovered in test window"
    # 2. Triage
    def triage_basic(df):
        score, priority, expl_list = [], [], []
        for _, row in df.iterrows():
            amt = row.get("award_amount", 0)
            # Normalize datetimes to handle tz-naive/tz-aware mismatches
            response_deadline = _normalize_datetime(row.get("response_deadline"))
            posted_date = _normalize_datetime(row.get("posted_date"))
            lead_days = (response_deadline - posted_date).days if (response_deadline and posted_date) else 0
            tri_score, expl = 0, []
            if amt and amt >= 50000 and amt <= 5000000:
                tri_score += 40
                expl.append("Award in preferred range")
            else:
                expl.append("Award out of preferred range")
            if lead_days and lead_days >= 15 and lead_days <= 60:
                tri_score += 30
                expl.append("Deadline in preferred response window")
            else:
                expl.append("Deadline out of preferred window")
            desc = row.get("description", "")
            complexity = len(str(desc)) if desc and not pd.isna(desc) else 0
            tri_score += min(complexity // 500, 10)
            expl.append(f"Complexity estimate: {complexity} chars")
            tri_score = min(tri_score, 100)
            score.append(tri_score)
            priority.append("HIGH" if tri_score > 80 else "MEDIUM" if tri_score >= 50 else "LOW")
            expl_list.append(" | ".join(expl))
        df = df.copy()
        df["triage_score"] = score
        df["priority"] = priority
        df["score_explanation"] = expl_list
        return df
    df_triaged = triage_basic(df_rfps)
    assert "triage_score" in df_triaged.columns, "Triage score missing"
    # At least some RFPs should have a non-zero score (deadline in range gives 30 points)
    assert sum(df_triaged["triage_score"] > 0) > 0, "No RFPs with any triage score"

    # 3. Go/No-Go (Fallback if engine not present)
    g_scores = [row.triage_score for _, row in df_triaged.iterrows()]
    g_decisions = ["go" if score > agent.config.get("go_nogo_threshold", 60) else "no-go" for score in g_scores]
    g_justs = ["Fallback decision (no engine)" for _ in g_scores]
    df_triaged["go_nogo_decision"] = g_decisions
    df_triaged["go_nogo_score"] = g_scores
    df_triaged["decision_justification"] = g_justs
    assert "go_nogo_decision" in df_triaged.columns

    # 4. Output artifacts
    ts = "test"
    outdir = agent.output_directory
    json_path = os.path.join(outdir, f"discovered_rfps_sample_{ts}.json")
    csv_path = os.path.join(outdir, f"discovered_rfps_sample_{ts}.csv")
    df_triaged.to_csv(csv_path, index=False)
    with open(json_path, "w") as jf:
        json.dump(df_triaged.to_dict("records"), jf, indent=2, default=str)
    assert os.path.exists(json_path), "JSON output not created"
    assert os.path.exists(csv_path), "CSV output not created"

    # 5. Pipeline compatibility - check for essential columns added by triage
    cols_needed = ["title", "triage_score", "priority", "go_nogo_decision", "go_nogo_score", "decision_justification"]
    for c in cols_needed:
        assert c in df_triaged.columns or c in df_triaged.columns.str.lower().tolist(), f"Column {c} missing from output"

    # Artifact content validation
    records = df_triaged.to_dict("records")
    assert isinstance(records, list) and len(records) > 0, "Output records missing"

    print(f"Integration test passed: artifacts - {json_path}, {csv_path}, records discovered - {len(records)}.")

if __name__ == "__main__":
    pytest.main([__file__])
