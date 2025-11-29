import json
import os
from datetime import datetime

import chardet
import pandas as pd


def detect_file_encoding(file_path, sample_size=10000):
    """Detect file encoding using multiple methods"""
    print(f"Detecting encoding for {os.path.basename(file_path)}...")
    # Method 1: Use chardet on a sample
    with open(file_path, 'rb') as f:
        sample = f.read(sample_size)
        detection = chardet.detect(sample)
        detected_encoding = detection['encoding']
        confidence = detection['confidence']
    print(f"  Chardet detected: {detected_encoding} (confidence: {confidence:.2f})")
    # Method 2: Try common encodings
    common_encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1', 'utf-16']
    for encoding in common_encodings:
        try:
            with open(file_path, encoding=encoding) as f:
                # Try to read first few lines
                for i, line in enumerate(f):
                    if i > 10:  # Read first 10 lines
                        break
            print(f"  ✓ {encoding}: Successfully read sample")
            return encoding
        except UnicodeDecodeError:
            print(f"  ✗ {encoding}: Failed")
        except Exception as e:
            print(f"  ✗ {encoding}: Error - {e}")
    # Fallback to detected encoding
    return detected_encoding if detected_encoding else 'latin1'
def load_csv_with_encoding(file_path, encoding=None, max_rows=None):
    """Load CSV file with proper encoding handling"""
    if encoding is None:
        encoding = detect_file_encoding(file_path)
    print(f"Loading {os.path.basename(file_path)} with encoding: {encoding}")
    try:
        # Load with pandas, handling various issues
        df = pd.read_csv(
            file_path,
            encoding=encoding,
            nrows=max_rows,
            low_memory=False,
            on_bad_lines='skip',  # Skip bad lines instead of failing
            dtype=str  # Load everything as string initially
        )
        print(f"  ✓ Successfully loaded {len(df)} rows, {len(df.columns)} columns")
        return df, encoding
    except Exception as e:
        print(f"  ✗ Error loading with {encoding}: {e}")
        # Try with latin1 as fallback
        if encoding != 'latin1':
            print("  Retrying with latin1 encoding...")
            try:
                df = pd.read_csv(
                    file_path,
                    encoding='latin1',
                    nrows=max_rows,
                    low_memory=False,
                    on_bad_lines='skip',
                    dtype=str
                )
                print(f"  ✓ Successfully loaded with latin1: {len(df)} rows, {len(df.columns)} columns")
                return df, 'latin1'
            except Exception as e2:
                print(f"  ✗ Error loading with latin1: {e2}")
        return None, None
def analyze_data_structure(df, file_name):
    """Analyze the structure of loaded data"""
    print(f"\nAnalyzing structure of {file_name}:")
    print(f"  Shape: {df.shape}")
    print(f"  Columns ({len(df.columns)}): {list(df.columns)}")
    # Look for key columns
    columns_lower = [col.lower() for col in df.columns]
    key_column_patterns = {
        'solicitation_id': ['solicitation', 'opportunity', 'id', 'number'],
        'title': ['title', 'subject', 'description'],
        'agency': ['agency', 'organization', 'office', 'dept'],
        'posting_date': ['posted', 'date', 'published', 'created'],
        'deadline': ['deadline', 'due', 'closing', 'response'],
        'value': ['value', 'amount', 'dollar', 'price'],
        'nigp': ['nigp', 'commodity'],
        'naics': ['naics', 'industry', 'classification'],
        'location': ['location', 'state', 'place', 'address']
    }
    found_columns = {}
    for key, patterns in key_column_patterns.items():
        matches = []
        for col in df.columns:
            col_lower = col.lower()
            if any(pattern in col_lower for pattern in patterns):
                matches.append(col)
        if matches:
            found_columns[key] = matches
            print(f"  ✓ {key}: {matches}")
    # Show sample data
    print("\nSample data (first 2 rows):")
    for i, row in df.head(2).iterrows():
        print(f"  Row {i}: {dict(row)}")
        break  # Just show first row to avoid too much output
    return found_columns
def check_target_categories_in_data(df, file_name):
    """Check for target NIGP/NAICS categories in the data"""
    print(f"\nChecking target categories in {file_name}:")
    target_patterns = {
        'bottled_water': ['065', 'water', 'beverage', 'drink'],
        'construction': ['236', '237', 'construction', 'building', 'contractor'],
        'delivery': ['484', '492', 'delivery', 'transport', 'logistics', 'shipping']
    }
    found_categories = {}
    # Convert all data to string for searching
    df_str = df.astype(str)
    all_text = ' '.join(df_str.values.flatten()).lower()
    for category, patterns in target_patterns.items():
        matches = []
        for pattern in patterns:
            if pattern in all_text:
                matches.append(pattern)
        if matches:
            found_categories[category] = matches
            print(f"  ✓ {category}: Found patterns {matches}")
        else:
            print(f"  ○ {category}: No patterns found in sample")
    return found_categories
def main():
    print("=== ROBUST DATA LOADING AND VALIDATION ===\n")
    raw_data_path = "/app/government_rfp_bid_1927/data/raw"
    csv_files = [f for f in os.listdir(raw_data_path) if f.endswith('.csv')]
    results = {}
    for csv_file in csv_files:
        print(f"\n{'='*60}")
        print(f"PROCESSING: {csv_file}")
        print('='*60)
        file_path = os.path.join(raw_data_path, csv_file)
        # Load with encoding detection (sample only for large files)
        sample_size = 1000 if os.path.getsize(file_path) > 100*1024*1024 else None
        df, encoding = load_csv_with_encoding(file_path, max_rows=sample_size)
        if df is not None:
            # Analyze structure
            found_columns = analyze_data_structure(df, csv_file)
            # Check for target categories
            target_categories = check_target_categories_in_data(df, csv_file)
            results[csv_file] = {
                'status': 'SUCCESS',
                'encoding': encoding,
                'shape': df.shape,
                'columns': list(df.columns),
                'found_key_columns': found_columns,
                'target_categories': target_categories,
                'sample_data': df.head(1).to_dict('records')[0] if len(df) > 0 else {}
            }
        else:
            results[csv_file] = {
                'status': 'FAILED',
                'encoding': None,
                'error': 'Could not load with any encoding'
            }
    # Save results
    print(f"\n{'='*60}")
    print("SAVING ANALYSIS RESULTS")
    print('='*60)
    os.makedirs("/app/government_rfp_bid_1927/data/processed", exist_ok=True)
    os.makedirs("/app/government_rfp_bid_1927/analysis", exist_ok=True)
    # Save detailed results
    results_path = "/app/government_rfp_bid_1927/data/processed/robust_data_analysis.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"✓ Detailed results saved: {results_path}")
    # Create summary report
    summary_path = "/app/government_rfp_bid_1927/analysis/data_loading_summary.md"
    with open(summary_path, 'w') as f:
        f.write("# RFP Data Loading Analysis\n\n")
        f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## File Loading Results\n\n")
        successful = 0
        for file, result in results.items():
            if result['status'] == 'SUCCESS':
                successful += 1
                f.write(f"### ✅ {file}\n")
                f.write(f"- **Encoding:** {result['encoding']}\n")
                f.write(f"- **Shape:** {result['shape']}\n")
                f.write(f"- **Key columns found:** {list(result['found_key_columns'].keys())}\n")
                f.write(f"- **Target categories:** {list(result['target_categories'].keys())}\n\n")
            else:
                f.write(f"### ❌ {file}\n")
                f.write(f"- **Error:** {result.get('error', 'Unknown error')}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- **Files processed:** {len(results)}\n")
        f.write(f"- **Successfully loaded:** {successful}\n")
        f.write(f"- **Ready for analysis:** {'Yes' if successful > 0 else 'No'}\n")
    print(f"✓ Summary report saved: {summary_path}")
    print("\n=== FINAL SUMMARY ===")
    successful_files = [f for f, r in results.items() if r['status'] == 'SUCCESS']
    print(f"✓ Successfully loaded {len(successful_files)}/{len(results)} files")
    if successful_files:
        print(f"✓ Files ready for analysis: {successful_files}")
        print("✓ Ready to proceed with data processing and EDA")
    else:
        print("✗ No files successfully loaded - need to investigate further")
if __name__ == "__main__":
    main()
