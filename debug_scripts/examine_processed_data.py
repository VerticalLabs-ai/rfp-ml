import os

import pandas as pd


def examine_data_structure():
    processed_dir = "/app/government_rfp_bid_1927/data/processed"
    # Check available files
    files = [f for f in os.listdir(processed_dir) if f.endswith('.parquet')]
    print(f"Available parquet files: {files}")
    for file in files:
        filepath = os.path.join(processed_dir, file)
        try:
            df = pd.read_parquet(filepath)
            print(f"\n=== {file} ===")
            print(f"Shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            print("Sample data:")
            print(df.head(2))
            # Check for text content that can be embedded
            text_columns = []
            for col in df.columns:
                if df[col].dtype == 'object':
                    sample_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else ""
                    if isinstance(sample_val, str) and len(sample_val) > 50:
                        text_columns.append(col)
            print(f"Text columns suitable for embedding: {text_columns}")
        except Exception as e:
            print(f"Error reading {file}: {e}")
if __name__ == "__main__":
    examine_data_structure()
