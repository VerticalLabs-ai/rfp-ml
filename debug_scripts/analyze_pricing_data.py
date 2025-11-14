import pandas as pd
import numpy as np
import json
from datetime import datetime
def analyze_historical_pricing():
    """Analyze historical award amounts from processed RFP datasets"""
    print("=== Historical Pricing Data Analysis ===\n")
    # Load all datasets to analyze pricing patterns
    datasets = {
        'bottled_water': '/app/government_rfp_bid_1927/data/processed/bottled_water_rfps.parquet',
        'construction': '/app/government_rfp_bid_1927/data/processed/construction_rfps.parquet', 
        'delivery': '/app/government_rfp_bid_1927/data/processed/delivery_rfps.parquet',
        'master': '/app/government_rfp_bid_1927/data/processed/rfp_master_dataset.parquet'
    }
    pricing_analysis = {}
    for category, filepath in datasets.items():
        try:
            df = pd.read_parquet(filepath)
            print(f"\n=== {category.upper()} CATEGORY ===")
            print(f"Total records: {len(df):,}")
            # Focus on award amount columns
            award_columns = []
            for col in df.columns:
                if any(term in col.lower() for term in ['award', 'amount', 'value', 'contract']):
                    award_columns.append(col)
            print(f"Award-related columns: {award_columns}")
            # Analyze the most relevant award column
            primary_award_col = None
            max_valid_values = 0
            for col in award_columns:
                if col in df.columns:
                    # Convert to numeric and count valid values
                    numeric_values = pd.to_numeric(df[col], errors='coerce')
                    valid_count = numeric_values.notna().sum()
                    if valid_count > max_valid_values:
                        max_valid_values = valid_count
                        primary_award_col = col
            if primary_award_col and max_valid_values > 0:
                print(f"Primary award column: {primary_award_col}")
                print(f"Valid award values: {max_valid_values:,} ({max_valid_values/len(df)*100:.1f}%)")
                # Convert to numeric for analysis
                awards = pd.to_numeric(df[primary_award_col], errors='coerce')
                valid_awards = awards.dropna()
                if len(valid_awards) > 0:
                    # Remove extreme outliers (above 99th percentile)
                    q99 = valid_awards.quantile(0.99)
                    filtered_awards = valid_awards[valid_awards <= q99]
                    # Statistical analysis
                    stats = {
                        'count': len(filtered_awards),
                        'mean': float(filtered_awards.mean()),
                        'median': float(filtered_awards.median()),
                        'std': float(filtered_awards.std()),
                        'min': float(filtered_awards.min()),
                        'max': float(filtered_awards.max()),
                        'q25': float(filtered_awards.quantile(0.25)),
                        'q75': float(filtered_awards.quantile(0.75)),
                        'q90': float(filtered_awards.quantile(0.90)),
                        'q95': float(filtered_awards.quantile(0.95))
                    }
                    print(f"Award Amount Statistics (filtered, n={stats['count']:,}):")
                    print(f"  Mean: ${stats['mean']:,.2f}")
                    print(f"  Median: ${stats['median']:,.2f}")
                    print(f"  Range: ${stats['min']:,.2f} - ${stats['max']:,.2f}")
                    print(f"  25th-75th percentile: ${stats['q25']:,.2f} - ${stats['q75']:,.2f}")
                    # Common award ranges for pricing baselines
                    ranges = {
                        'small': (0, 50000),
                        'medium': (50000, 500000),
                        'large': (500000, 5000000),
                        'mega': (5000000, float('inf'))
                    }
                    range_analysis = {}
                    for range_name, (min_val, max_val) in ranges.items():
                        if max_val == float('inf'):
                            in_range = filtered_awards[filtered_awards >= min_val]
                        else:
                            in_range = filtered_awards[(filtered_awards >= min_val) & (filtered_awards < max_val)]
                        if len(in_range) > 0:
                            range_analysis[range_name] = {
                                'count': len(in_range),
                                'percentage': len(in_range) / len(filtered_awards) * 100,
                                'median': float(in_range.median()),
                                'mean': float(in_range.mean())
                            }
                    print(f"Award Distribution by Size:")
                    for range_name, data in range_analysis.items():
                        print(f"  {range_name.capitalize()}: {data['count']:,} awards ({data['percentage']:.1f}%) - "
                              f"Median: ${data['median']:,.0f}")
                    pricing_analysis[category] = {
                        'primary_column': primary_award_col,
                        'statistics': stats,
                        'range_analysis': range_analysis,
                        'sample_size': len(filtered_awards)
                    }
                else:
                    print("No valid award amounts found")
                    pricing_analysis[category] = {'error': 'No valid award amounts'}
            else:
                print("No award amount column found with valid data")
                pricing_analysis[category] = {'error': 'No award amount columns'}
        except Exception as e:
            print(f"Error analyzing {category}: {e}")
            pricing_analysis[category] = {'error': str(e)}
    # Save analysis results
    analysis_path = '/app/government_rfp_bid_1927/data/pricing/historical_pricing_analysis.json'
    import os
    os.makedirs(os.path.dirname(analysis_path), exist_ok=True)
    with open(analysis_path, 'w') as f:
        json.dump(pricing_analysis, f, indent=2)
    print(f"\n=== Analysis saved to: {analysis_path} ===")
    return pricing_analysis
if __name__ == "__main__":
    analysis = analyze_historical_pricing()