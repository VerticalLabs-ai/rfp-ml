import pandas as pd
import numpy as np
import os
import json
import re
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

def load_all_rfp_datasets(raw_data_path):
    print("=== LOADING ALL RFP DATASETS ===\n")
    csv_files = [f for f in os.listdir(raw_data_path) if f.endswith('.csv')]
    datasets = {}
    total_records = 0
    for csv_file in csv_files:
        file_path = os.path.join(raw_data_path, csv_file)
        print(f"Loading {csv_file}...")
        try:
            # Load full dataset with latin1 encoding
            df = pd.read_csv(
                file_path,
                encoding='latin1',
                low_memory=False,
                on_bad_lines='skip',
                dtype=str  # Load as strings to avoid type issues
            )
            datasets[csv_file] = df
            total_records += len(df)
            print(f"  ✓ Loaded {len(df):,} records")
        except Exception as e:
            print(f"  ✗ Error loading {csv_file}: {e}")
    print(f"\nTotal records loaded: {total_records:,}")
    return datasets

def standardize_schema(datasets):
    print("\n=== STANDARDIZING SCHEMA ===\n")
    # Define standardized column mapping
    standard_columns = {
        'rfp_id': 'NoticeId',
        'title': 'Title', 
        'solicitation_number': 'Sol#',
        'agency': 'Department/Ind.Agency',
        'sub_agency': 'Sub-Tier',
        'office': 'Office',
        'posted_date': 'PostedDate',
        'response_deadline': 'ResponseDeadLine',
        'naics_code': 'NaicsCode',
        'classification_code': 'ClassificationCode',
        'set_aside': 'SetASide',
        'award_amount': 'Award$',
        'awardee': 'Awardee',
        'state': 'State',
        'city': 'City',
        'zip_code': 'ZipCode',
        'description': 'Description',
        'link': 'Link',
        'award_date': 'AwardDate',
        'active': 'Active',
        'type': 'Type'
    }
    standardized_datasets = {}
    for file_name, df in datasets.items():
        print(f"Standardizing {file_name}...")
        # Create standardized DataFrame
        std_df = pd.DataFrame()
        for std_col, orig_col in standard_columns.items():
            if orig_col in df.columns:
                std_df[std_col] = df[orig_col]
            else:
                std_df[std_col] = np.nan
        # Add source file information
        std_df['source_file'] = file_name
        std_df['fiscal_year'] = extract_fiscal_year(file_name)
        standardized_datasets[file_name] = std_df
        print(f"  ✓ Standardized to {len(std_df.columns)} columns")
    return standardized_datasets

def extract_fiscal_year(filename):
    if 'FY' in filename:
        match = re.search(r'FY(\d{4})', filename)
        if match:
            return int(match.group(1))
    elif 'ContractOpportunities' in filename:
        return 2025  # Current opportunities
    return None

def filter_target_categories(datasets):
    print("\n=== FILTERING TARGET CATEGORIES ===\n")
    # Target NAICS codes
    target_naics = {
        'bottled_water': ['312112'],  # Bottled water manufacturing
        'construction': ['236', '237'],  # Construction (starts with)
        'delivery': ['484', '492']  # Truck transportation, Couriers
    }
    # Also include classification codes that might be relevant
    target_classifications = {
        'bottled_water': ['065', '8955'],  # Water, beverages
        'construction': ['176', '177', '178', '179'],  # Construction materials
        'delivery': ['DG11', '4810']  # Transportation services
    }
    filtered_datasets = {}
    category_counts = {}
    for file_name, df in datasets.items():
        print(f"Filtering {file_name}:")
        # Create category filters
        bottled_water_filter = create_category_filter(df, target_naics['bottled_water'], target_classifications['bottled_water'])
        construction_filter = create_category_filter(df, target_naics['construction'], target_classifications['construction'])
        delivery_filter = create_category_filter(df, target_naics['delivery'], target_classifications['delivery'])
        # Apply filters
        bottled_water_rfps = df[bottled_water_filter].copy()
        construction_rfps = df[construction_filter].copy()
        delivery_rfps = df[delivery_filter].copy()
        # Combine all target RFPs
        target_rfps = pd.concat([bottled_water_rfps, construction_rfps, delivery_rfps]).drop_duplicates(subset=['rfp_id'])
        # Add category labels
        target_rfps['category'] = 'other'
        target_rfps.loc[target_rfps['rfp_id'].isin(bottled_water_rfps['rfp_id']), 'category'] = 'bottled_water'
        target_rfps.loc[target_rfps['rfp_id'].isin(construction_rfps['rfp_id']), 'category'] = 'construction'
        target_rfps.loc[target_rfps['rfp_id'].isin(delivery_rfps['rfp_id']), 'category'] = 'delivery'
        # Handle overlapping categories
        overlapping = target_rfps.duplicated(subset=['rfp_id'], keep=False)
        if overlapping.any():
            target_rfps.loc[overlapping, 'category'] = 'multiple_categories'
        filtered_datasets[file_name] = target_rfps
        # Count by category
        counts = {
            'bottled_water': len(bottled_water_rfps),
            'construction': len(construction_rfps),
            'delivery': len(delivery_rfps),
            'total_target': len(target_rfps),
            'original_total': len(df)
        }
        category_counts[file_name] = counts
        print(f"  Bottled Water: {counts['bottled_water']:,}")
        print(f"  Construction: {counts['construction']:,}")
        print(f"  Delivery: {counts['delivery']:,}")
        print(f"  Total Target: {counts['total_target']:,} ({counts['total_target']/counts['original_total']*100:.1f}%)")
    return filtered_datasets, category_counts

def create_category_filter(df, naics_patterns, classification_patterns):
    naics_filter = pd.Series(False, index=df.index)
    classification_filter = pd.Series(False, index=df.index)
    # NAICS code matching
    if 'naics_code' in df.columns:
        naics_series = df['naics_code'].astype(str).fillna('')
        for pattern in naics_patterns:
            naics_filter |= naics_series.str.startswith(pattern)
    # Classification code matching
    if 'classification_code' in df.columns:
        class_series = df['classification_code'].astype(str).fillna('')
        for pattern in classification_patterns:
            classification_filter |= class_series.str.contains(pattern, na=False)
    return naics_filter | classification_filter

def clean_and_process_data(filtered_datasets):
    print("\n=== CLEANING AND PROCESSING DATA ===\n")
    processed_datasets = {}
    for file_name, df in filtered_datasets.items():
        print(f"Processing {file_name}...")
        processed_df = df.copy()
        # Clean dates
        processed_df['posted_date'] = pd.to_datetime(processed_df['posted_date'], errors='coerce', utc=True)
        processed_df['response_deadline'] = pd.to_datetime(processed_df['response_deadline'], errors='coerce', utc=True)
        processed_df['award_date'] = pd.to_datetime(processed_df['award_date'], errors='coerce', utc=True)
        # Clean award amounts
        processed_df['award_amount_clean'] = clean_currency_column(processed_df['award_amount'])
        # Extract numeric values from description length
        processed_df['description_length'] = processed_df['description'].astype(str).str.len()
        processed_df['has_description'] = processed_df['description'].notna() & (processed_df['description'] != 'nan')
        # Calculate lead time (days between posting and deadline) - safely handle nulls
        try:
            date_diff = processed_df['response_deadline'] - processed_df['posted_date']
            processed_df['lead_time_days'] = date_diff.dt.days
        except Exception as e:
            print(f"    Warning: Could not calculate lead time - {e}")
            processed_df['lead_time_days'] = np.nan
        # Flag active vs completed RFPs
        processed_df['is_active'] = processed_df['active'].str.upper() == 'YES'
        processed_datasets[file_name] = processed_df
        print(f"  ✓ Processed {len(processed_df)} records")
    return processed_datasets

def clean_currency_column(currency_series):
    if currency_series.isna().all():
        return pd.Series([np.nan] * len(currency_series))
    # Convert to string and clean
    cleaned = currency_series.astype(str).str.replace(r'[^0-9.-]', '', regex=True)
    cleaned = pd.to_numeric(cleaned, errors='coerce')
    return cleaned

def create_master_dataset(processed_datasets):
    print("\n=== CREATING MASTER DATASET ===\n")
    # Combine all datasets
    all_dfs = []
    for file_name, df in processed_datasets.items():
        all_dfs.append(df)
    master_df = pd.concat(all_dfs, ignore_index=True)
    # Remove duplicates based on RFP ID
    original_count = len(master_df)
    master_df = master_df.drop_duplicates(subset=['rfp_id'], keep='first')
    deduplicated_count = len(master_df)
    print(f"Combined datasets: {original_count:,} records")
    print(f"After deduplication: {deduplicated_count:,} records")
    print(f"Duplicates removed: {original_count - deduplicated_count:,}")
    # Add data quality score
    master_df['data_quality_score'] = calculate_data_quality_score(master_df)
    return master_df

def calculate_data_quality_score(df):
    score = pd.Series(0.0, index=df.index)
    # Essential fields (weight: 0.6)
    essential_fields = ['rfp_id', 'title', 'agency', 'posted_date', 'naics_code']
    for field in essential_fields:
        score += (df[field].notna() & (df[field] != 'nan')).astype(float) * 0.12
    # Important fields (weight: 0.3)
    important_fields = ['response_deadline', 'award_amount_clean', 'description']
    for field in important_fields:
        score += (df[field].notna() & (df[field] != 'nan')).astype(float) * 0.10
    # Additional fields (weight: 0.1)
    additional_fields = ['state', 'city', 'set_aside']
    for field in additional_fields:
        if field in df.columns:
            score += (df[field].notna() & (df[field] != 'nan')).astype(float) * 0.033
    return score.round(3)

def save_processed_data(master_df, processed_datasets, category_counts, base_path):
    print("\n=== SAVING PROCESSED DATA ===\n")
    # Create output directories
    os.makedirs(f"{base_path}/data/processed", exist_ok=True)
    # Save master dataset
    master_path = f"{base_path}/data/processed/rfp_master_dataset.parquet"
    master_df.to_parquet(master_path, index=False)
    print(f"✓ Master dataset saved: {master_path}")
    # Save CSV version for inspection
    csv_path = f"{base_path}/data/processed/rfp_master_dataset.csv"
    master_df.to_csv(csv_path, index=False)
    print(f"✓ Master dataset CSV saved: {csv_path}")
    # Save category-specific datasets
    for category in ['bottled_water', 'construction', 'delivery']:
        category_df = master_df[master_df['category'] == category]
        if len(category_df) > 0:
            category_path = f"{base_path}/data/processed/{category}_rfps.parquet"
            category_df.to_parquet(category_path, index=False)
            print(f"✓ {category} dataset saved: {category_path} ({len(category_df)} records)")
    # Save processing metadata
    metadata = {
        'processing_date': datetime.now().isoformat(),
        'total_records': len(master_df),
        'category_distribution': master_df['category'].value_counts().to_dict(),
        'fiscal_year_distribution': master_df['fiscal_year'].value_counts().to_dict(),
        'source_file_distribution': master_df['source_file'].value_counts().to_dict(),
        'data_quality_stats': {
            'mean_quality_score': master_df['data_quality_score'].mean(),
            'high_quality_records': (master_df['data_quality_score'] >= 0.8).sum(),
            'low_quality_records': (master_df['data_quality_score'] < 0.5).sum()
        },
        'category_counts_by_file': category_counts
    }
    metadata_path = f"{base_path}/data/processed/processing_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"✓ Processing metadata saved: {metadata_path}")
    return master_path, metadata_path

def main():
    base_path = "/app/government_rfp_bid_1927"
    raw_data_path = f"{base_path}/data/raw"
    # Load all datasets
    datasets = load_all_rfp_datasets(raw_data_path)
    if not datasets:
        print("❌ No datasets loaded successfully!")
        return
    # Standardize schema
    standardized_datasets = standardize_schema(datasets)
    # Filter for target categories
    filtered_datasets, category_counts = filter_target_categories(standardized_datasets)
    # Clean and process data
    processed_datasets = clean_and_process_data(filtered_datasets)
    # Create master dataset
    master_df = create_master_dataset(processed_datasets)
    # Save processed data
    master_path, metadata_path = save_processed_data(master_df, processed_datasets, category_counts, base_path)
    print(f"\n=== PROCESSING COMPLETE ===")
    print(f"✓ Master dataset: {len(master_df):,} RFPs across target categories")
    print(f"✓ Categories: {dict(master_df['category'].value_counts())}")
    print(f"✓ Fiscal years: {sorted(master_df['fiscal_year'].dropna().unique())}")
    print(f"✓ Average data quality: {master_df['data_quality_score'].mean():.3f}")
    print(f"✓ Ready for exploratory data analysis!")

if __name__ == "__main__":
    main()