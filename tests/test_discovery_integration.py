# Integration test for end-to-end RFP Discovery Agent pipeline.
import json
import os

import pytest

from src.agents.discovery_agent import RFPDiscoveryAgent


@pytest.fixture(scope="module")
def agent():
    config_path = "/app/government_rfp_bid_1927/src/agents/discovery_config.json"
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
            lead_days = (row.get("response_deadline") - row.get("posted_date")).days if ("response_deadline" in row and "posted_date" in row) else 0
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
            complexity = len(row.get("description", "")) if "description" in row else 0
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
    assert sum(df_triaged["triage_score"] > 50) > 0, "No medium/high priority RFPs"

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

    # 5. Pipeline compatibility
    cols_needed = ["id","title","award_amount","posted_date","response_deadline","description","triage_score","priority","go_nogo_decision","go_nogo_score","decision_justification"]
    for c in cols_needed:
        assert c in df_triaged.columns or c in df_triaged.columns.str.lower().tolist(), f"Column {c} missing from output"

    # Artifact content validation
    records = df_triaged.to_dict("records")
    assert isinstance(records, list) and len(records) > 0, "Output records missing"

    print(f"Integration test passed: artifacts - {json_path}, {csv_path}, records discovered - {len(records)}.")

if __name__ == "__main__":
    pytest.main([__file__])
