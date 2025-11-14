import xml.etree.ElementTree as ET
import pandas as pd
import json
import os
from datetime import datetime

# Optional visualization imports
try:
import matplotlib.pyplot as plt
import seaborn as sns
VISUALIZATION_AVAILABLE = True
except ImportError:
VISUALIZATION_AVAILABLE = False
print("Warning: matplotlib/seaborn not available. Skipping visualizations.")
def parse_gcs_bucket_listing(xml_file_path):
    """Parse the Google Cloud Storage bucket listing XML file"""
    print("=== PARSING GOOGLE CLOUD STORAGE BUCKET LISTING ===\n")
    # Parse XML
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    # Extract namespace
    namespace = {'gcs': 'http://doc.s3.amazonaws.com/2006-03-01'}
    # Find bucket name
    bucket_name = root.find('.//gcs:Name', namespace).text
    print(f"Bucket Name: {bucket_name}")
    # Extract all file contents
    contents = root.findall('.//gcs:Contents', namespace)
    print(f"Total Files Available: {len(contents)}")
    datasets = []
    total_size_bytes = 0
    for content in contents:
        key = content.find('gcs:Key', namespace).text
        size = int(content.find('gcs:Size', namespace).text)
        last_modified = content.find('gcs:LastModified', namespace).text
        etag = content.find('gcs:ETag', namespace).text
        # Parse file information
        file_name = os.path.basename(key)
        file_path = key
        file_ext = os.path.splitext(file_name)[1].lower()
        # Extract year from filename if present
        year = None
        if 'FY' in file_name:
            try:
                year = int(file_name.split('FY')[1][:4])
            except:
                pass
        # Size in human readable format
        if size < 1024:
            size_str = f"{size}B"
        elif size < 1024**2:
            size_str = f"{size/1024:.1f}KB"
        elif size < 1024**3:
            size_str = f"{size/(1024**2):.1f}MB"
        else:
            size_str = f"{size/(1024**3):.2f}GB"
        datasets.append({
            'file_name': file_name,
            'file_path': key,
            'file_extension': file_ext,
            'size_bytes': size,
            'size_human': size_str,
            'last_modified': last_modified,
            'etag': etag,
            'fiscal_year': year,
            'download_url': f'https://storage.googleapis.com/{bucket_name}/{key}'
        })
        total_size_bytes += size
    print(f"Total Dataset Size: {total_size_bytes/(1024**3):.2f}GB")
    # Convert to DataFrame
    df = pd.DataFrame(datasets)
    return df, bucket_name, total_size_bytes
def analyze_dataset_catalog(df):
    """Analyze the dataset catalog"""
    print("\n=== DATASET CATALOG ANALYSIS ===\n")
    # Basic statistics
    print("File Type Distribution:")
    file_type_counts = df['file_extension'].value_counts()
    print(file_type_counts)
    print()
    # Size analysis
    print("Size Analysis:")
    total_size_gb = df['size_bytes'].sum() / (1024**3)
    print(f"Total Size: {total_size_gb:.2f}GB")
    print(f"Average File Size: {df['size_bytes'].mean()/(1024**2):.2f}MB")
    print(f"Largest File: {df.loc[df['size_bytes'].idxmax(), 'file_name']} ({df['size_bytes'].max()/(1024**3):.2f}GB)")
    print(f"Smallest File: {df.loc[df['size_bytes'].idxmin(), 'file_name']} ({df['size_bytes'].min()/(1024**2):.2f}MB)")
    print()
    # Fiscal year analysis
    csv_files = df[df['file_extension'] == '.csv'].copy()
    if not csv_files.empty:
        print("Fiscal Year Coverage (CSV files):")
        csv_files = csv_files.dropna(subset=['fiscal_year'])
        if not csv_files.empty:
            year_range = f"{csv_files['fiscal_year'].min()} - {csv_files['fiscal_year'].max()}"
            print(f"Year Range: {year_range}")
            print(f"Total Years: {csv_files['fiscal_year'].nunique()}")
            print(f"Years with Data: {sorted(csv_files['fiscal_year'].unique())}")
        print()
    # Identify key files
    print("Key Dataset Files:")
    key_files = []
    # Main current opportunities file
    main_csv = df[df['file_name'].str.contains('ContractOpportunitiesFullCSV', case=False, na=False)]
    if not main_csv.empty:
        file_info = main_csv.iloc[0]
        print(f"✓ Current Opportunities: {file_info['file_name']} ({file_info['size_human']})")
        key_files.append({
            'name': file_info['file_name'],
            'type': 'Current Opportunities',
            'size': file_info['size_human'],
            'url': file_info['download_url'],
            'priority': 1
        })
    # Documentation
    docs = df[df['file_name'].str.contains('Documentation', case=False, na=False)]
    if not docs.empty:
        file_info = docs.iloc[0]
        print(f"✓ Documentation: {file_info['file_name']} ({file_info['size_human']})")
        key_files.append({
            'name': file_info['file_name'],
            'type': 'Documentation',
            'size': file_info['size_human'],
            'url': file_info['download_url'],
            'priority': 2
        })
    # Recent years (2020-2025)
    recent_years = df[(df['fiscal_year'] >= 2020) & (df['file_extension'] == '.csv')].copy()
    if not recent_years.empty:
        print(f"✓ Recent Historical Data ({recent_years['fiscal_year'].min()}-{recent_years['fiscal_year'].max()}):")
        for _, row in recent_years.sort_values('fiscal_year', ascending=False).iterrows():
            print(f"  - {row['file_name']} ({row['size_human']})")
            key_files.append({
                'name': row['file_name'],
                'type': f'Historical FY{row["fiscal_year"]}',
                'size': row['size_human'],
                'url': row['download_url'],
                'priority': 3
            })
    return key_files
def create_download_recommendations(df, key_files):
    """Create prioritized download recommendations"""
    print("\n=== DOWNLOAD RECOMMENDATIONS ===\n")
    recommendations = {
        'immediate_priority': [],
        'high_priority': [],
        'medium_priority': [],
        'total_size_gb': 0
    }
    # Immediate priority: Current opportunities and documentation
    immediate = [f for f in key_files if f['priority'] <= 2]
    for file_info in immediate:
        recommendations['immediate_priority'].append(file_info)
        file_row = df[df['file_name'] == file_info['name']].iloc[0]
        recommendations['total_size_gb'] += file_row['size_bytes'] / (1024**3)
    # High priority: Recent 3 years of historical data
    recent_historical = [f for f in key_files if f['priority'] == 3 and any(year in f['name'] for year in ['2023', '2024', '2025'])]
    for file_info in recent_historical:
        recommendations['high_priority'].append(file_info)
        file_row = df[df['file_name'] == file_info['name']].iloc[0]
        recommendations['total_size_gb'] += file_row['size_bytes'] / (1024**3)
    # Medium priority: Earlier historical data
    earlier_historical = [f for f in key_files if f['priority'] == 3 and not any(year in f['name'] for year in ['2023', '2024', '2025'])]
    for file_info in earlier_historical:
        recommendations['medium_priority'].append(file_info)
    print("IMMEDIATE PRIORITY (Download First):")
    for file_info in recommendations['immediate_priority']:
        print(f"  ✓ {file_info['name']} ({file_info['size']}) - {file_info['type']}")
    print(f"\nHIGH PRIORITY (Core Analysis Dataset):")
    for file_info in recommendations['high_priority']:
        print(f"  ✓ {file_info['name']} ({file_info['size']}) - {file_info['type']}")
    print(f"\nMEDIUM PRIORITY (Extended Historical Analysis):")
    for file_info in recommendations['medium_priority'][:5]:  # Show first 5
        print(f"  ○ {file_info['name']} ({file_info['size']}) - {file_info['type']}")
    if len(recommendations['medium_priority']) > 5:
        print(f"  ... and {len(recommendations['medium_priority']) - 5} more historical files")
    print(f"\nEstimated Download Size (Immediate + High Priority): {recommendations['total_size_gb']:.2f}GB")
    return recommendations
def save_analysis_results(df, key_files, recommendations, base_path):
    """Save analysis results to files"""
    print("\n=== SAVING ANALYSIS RESULTS ===\n")
    # Create directories
    os.makedirs(f"{base_path}/data/processed", exist_ok=True)
    os.makedirs(f"{base_path}/analysis", exist_ok=True)
    # Save full dataset catalog
    catalog_path = f"{base_path}/data/processed/dataset_catalog.csv"
    df.to_csv(catalog_path, index=False)
    print(f"✓ Full dataset catalog saved: {catalog_path}")
    # Save download recommendations
    recommendations_path = f"{base_path}/data/processed/download_recommendations.json"
    with open(recommendations_path, 'w') as f:
        json.dump(recommendations, f, indent=2, default=str)
    print(f"✓ Download recommendations saved: {recommendations_path}")
    # Save key files metadata
    key_files_path = f"{base_path}/data/processed/key_files_metadata.json"
    with open(key_files_path, 'w') as f:
        json.dump(key_files, f, indent=2)
    print(f"✓ Key files metadata saved: {key_files_path}")
    # Create a simple download script
    download_script_path = f"{base_path}/debug_scripts/download_priority_datasets.sh"
    with open(download_script_path, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("# Priority dataset download script\n")
        f.write("# Generated automatically from dataset catalog analysis\n\n")
        f.write(f"mkdir -p {base_path}/data/raw\n")
        f.write(f"cd {base_path}/data/raw\n\n")
        f.write("echo 'Downloading immediate priority files...'\n")
        for file_info in recommendations['immediate_priority']:
            safe_name = file_info['name'].replace(' ', '_')
            f.write(f"wget -O '{safe_name}' '{file_info['url']}' || curl -o '{safe_name}' '{file_info['url']}'\n")
        f.write("\necho 'Downloading high priority files...'\n")
        for file_info in recommendations['high_priority']:
            safe_name = file_info['name'].replace(' ', '_')
            f.write(f"wget -O '{safe_name}' '{file_info['url']}' || curl -o '{safe_name}' '{file_info['url']}'\n")
        f.write("\necho 'Download complete!'\n")
        f.write("ls -lah\n")
    # Make script executable
    os.chmod(download_script_path, 0o755)
    print(f"✓ Download script created: {download_script_path}")
    return catalog_path, recommendations_path, download_script_path
def main():
    xml_file_path = "/app/government_rfp_bid_1927/data/dataset_rfp"
    base_path = "/app/government_rfp_bid_1927"
    # Parse the catalog
    df, bucket_name, total_size = parse_gcs_bucket_listing(xml_file_path)
    # Analyze the catalog
    key_files = analyze_dataset_catalog(df)
    # Create download recommendations
    recommendations = create_download_recommendations(df, key_files)
    # Save results
    catalog_path, rec_path, script_path = save_analysis_results(df, key_files, recommendations, base_path)
    print(f"\n=== SUMMARY ===")
    print(f"✓ Discovered {len(df)} datasets in sam.gov bucket")
    print(f"✓ Total available data: {total_size/(1024**3):.2f}GB")
    print(f"✓ Identified {len(key_files)} key files for RFP analysis")
    print(f"✓ Created prioritized download plan")
    print(f"✓ Ready to proceed with data acquisition")
    print(f"\nNEXT STEPS:")
    print(f"1. Run download script: bash {script_path}")
    print(f"2. Validate downloaded files")
    print(f"3. Begin data loading and analysis")
if __name__ == "__main__":
    main()