# CLI script for autonomous RFP discovery, triage, Go/No-Go scoring, and output generation

import sys
import os
import pandas as pd
import json
from datetime import datetime

sys.path.insert(0, '/app/government_rfp_bid_1927/src')
from agents.discovery_agent import RFPDiscoveryAgent

def main():
    config_path = "/app/government_rfp_bid_1927/src/agents/discovery_config.json"
    data_path = "/app/government_rfp_bid_1927/data/processed/rfp_master_dataset.parquet"

    agent = RFPDiscoveryAgent(config_path=config_path)
    all_rfps = pd.read_parquet(data_path)
    print(f"Loaded {len(all_rfps)} RFPs from {data_path}")

    triaged = agent.triage_rfps(all_rfps)
    print(f"Triaged to {len(triaged)} RFPs")

    scored = agent.evaluate_go_nogo(triaged)
    print("Go/No-Go scoring complete")
    
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "/app/government_rfp_bid_1927/data/discovered_rfps"
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, f"discovered_rfps_{now}.json")
    csv_path = os.path.join(output_dir, f"discovered_rfps_{now}.csv")
    
    # Output JSON
    meta = {
        "discovery_timestamp": datetime.now().isoformat(),
        "num_rfps": len(scored)
    }
    output_json = {
        "metadata": meta,
        "rfps": scored.to_dict(orient="records")
    }
    with open(json_path, "w") as jf:
        json.dump(output_json, jf, indent=2)
    # Output CSV
    scored.to_csv(csv_path, index=False)
    
    print(f"Exported JSON: {json_path}")
    print(f"Exported CSV: {csv_path}")

if __name__ == "__main__":
    main()