# This script defines Go/No-Go scoring and export for discovered RFPs using the agent.
import os
import json
import pandas as pd
from datetime import datetime

def evaluate_go_nogo(agent, triaged_df: pd.DataFrame) -> pd.DataFrame:
    from src.decision.go_nogo_engine import GoNoGoEngine
    from dataclasses import asdict
    nogo_engine = GoNoGoEngine()
    results = []
    for _, row in triaged_df.iterrows():
        rfp_data = row.to_dict()
        try:
            decision = nogo_engine.analyze_rfp_opportunity(rfp_data)
            decision_dict = asdict(decision)
        except Exception as e:
            decision_dict = {"recommendation": "error", "overall_score": -1, "confidence_level": 0}
        full_row = rfp_data.copy()
        full_row.update(decision_dict)
        results.append(full_row)
    return pd.DataFrame(results)

def export_outputs(df: pd.DataFrame, file_tag="discovered_rfps_sample"):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = "/app/government_rfp_bid_1927/data/discovered_rfps"
    os.makedirs(out_dir, exist_ok=True)
    meta = {
        "discovery_timestamp": datetime.now().isoformat(),
        "num_rfps": len(df)
    }
    # JSON
    output_json = {
        "metadata": meta,
        "rfps": df.to_dict(orient="records")
    }
    json_path = os.path.join(out_dir, f"{file_tag}_{now}.json")
    with open(json_path, "w") as jf:
        json.dump(output_json, jf, indent=2)
    # CSV
    csv_path = os.path.join(out_dir, f"{file_tag}_{now}.csv")
    df.to_csv(csv_path, index=False)
    print(f"Exported JSON: {json_path}\nExported CSV: {csv_path}")
    return json_path, csv_path

if __name__ == "__main__":
    from src.agents.discovery_agent import RFPDiscoveryAgent
    agent = RFPDiscoveryAgent(
        config_path="/app/government_rfp_bid_1927/src/agents/discovery_config.json"
    )
    df_all = pd.read_parquet("/app/government_rfp_bid_1927/data/processed/rfp_master_dataset.parquet")
    triaged = agent.triage_rfps(df_all)
    go_nogo_scored = evaluate_go_nogo(agent, triaged)
    export_outputs(go_nogo_scored)