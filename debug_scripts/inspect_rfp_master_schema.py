# Inspect rfp_master_dataset.parquet for fields and types - essential for agent development

import sys

import pandas as pd


def main():
    try:
        path = '/app/government_rfp_bid_1927/data/processed/rfp_master_dataset.parquet'
        df = pd.read_parquet(path)
        print("Dataset shape:", df.shape)
        print("\nColumns:\n", df.columns.tolist())
        print("\nDtypes:\n", df.dtypes)
        print("\nSample row:\n", df.iloc[0].to_dict())
        print("\nMissing value counts:\n", df.isnull().sum())
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
