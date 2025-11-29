import json
import os
import xml.etree.ElementTree as ET

import pandas as pd


def explore_directory_structure(base_path):
    """Explore directory structure and catalog all files"""
    print(f"=== EXPLORING DIRECTORY: {base_path} ===\n")
    if not os.path.exists(base_path):
        print(f"ERROR: Directory {base_path} does not exist!")
        return None, []
    all_files = []
    total_size = 0
    file_types = {}
    # Walk through directory structure
    for root, dirs, files in os.walk(base_path):
        level = root.replace(base_path, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            file_path = os.path.join(root, file)
            try:
                file_size = os.path.getsize(file_path)
                total_size += file_size
                file_ext = os.path.splitext(file)[1].lower()
                file_types[file_ext] = file_types.get(file_ext, 0) + 1
                # Convert size to human readable
                if file_size < 1024:
                    size_str = f"{file_size}B"
                elif file_size < 1024**2:
                    size_str = f"{file_size/1024:.1f}KB"
                elif file_size < 1024**3:
                    size_str = f"{file_size/(1024**2):.1f}MB"
                else:
                    size_str = f"{file_size/(1024**3):.1f}GB"
                print(f"{subindent}{file} ({size_str})")
                all_files.append({
                    'path': file_path,
                    'name': file,
                    'size': file_size,
                    'extension': file_ext,
                    'relative_path': os.path.relpath(file_path, base_path)
                })
            except OSError as e:
                print(f"{subindent}{file} (ERROR: {e})")
    print("\n=== SUMMARY ===")
    print(f"Total files found: {len(all_files)}")
    print(f"Total size: {total_size/(1024**2):.2f}MB")
    print(f"File types: {file_types}")
    return all_files, file_types
def validate_sample_files(all_files, max_samples=5):
    """Attempt to read and validate sample files"""
    print("\n=== SAMPLE FILE VALIDATION ===\n")
    if not all_files:
        print("No files found to validate!")
        return {}
    validation_results = {}
    samples_tested = 0
    # Prioritize different file types for testing
    priority_extensions = ['.json', '.csv', '.xml', '.parquet', '.txt']
    for ext in priority_extensions:
        if samples_tested >= max_samples:
            break
        matching_files = [f for f in all_files if f['extension'] == ext]
        if not matching_files:
            continue
        # Test the largest file of this type (likely most representative)
        test_file = max(matching_files, key=lambda x: x['size'])
        file_path = test_file['path']
        print(f"Testing {ext} file: {test_file['name']} ({test_file['size']/(1024**2):.2f}MB)")
        try:
            if ext == '.json':
                with open(file_path, encoding='utf-8') as f:
                    # Try to read first few lines to check if it's JSON Lines or single JSON
                    first_line = f.readline().strip()
                    f.seek(0)
                    if first_line.startswith('[') or first_line.startswith('{'):
                        # Try regular JSON first
                        try:
                            data = json.load(f)
                            if isinstance(data, list):
                                sample_record = data[0] if data else {}
                                record_count = len(data)
                            else:
                                sample_record = data
                                record_count = 1
                            validation_results[file_path] = {
                                'status': 'SUCCESS',
                                'format': 'JSON',
                                'record_count': record_count,
                                'sample_keys': list(sample_record.keys()) if isinstance(sample_record, dict) else 'Non-dict record',
                                'sample_record': sample_record if isinstance(sample_record, dict) else str(sample_record)[:200]
                            }
                        except json.JSONDecodeError:
                            # Try JSON Lines format
                            f.seek(0)
                            lines = f.readlines()[:5]  # Read first 5 lines
                            records = []
                            for line in lines:
                                if line.strip():
                                    records.append(json.loads(line))
                            validation_results[file_path] = {
                                'status': 'SUCCESS',
                                'format': 'JSON Lines',
                                'record_count': f'~{len(lines)} (estimated from first 5 lines)',
                                'sample_keys': list(records[0].keys()) if records and isinstance(records[0], dict) else 'Non-dict record',
                                'sample_record': records[0] if records else {}
                            }
            elif ext == '.csv':
                df = pd.read_csv(file_path, nrows=5)  # Read first 5 rows
                validation_results[file_path] = {
                    'status': 'SUCCESS',
                    'format': 'CSV',
                    'columns': list(df.columns),
                    'record_count': '5+ (sample)',
                    'sample_data': df.head(2).to_dict('records')
                }
            elif ext == '.xml':
                tree = ET.parse(file_path)
                root = tree.getroot()
                validation_results[file_path] = {
                    'status': 'SUCCESS',
                    'format': 'XML',
                    'root_tag': root.tag,
                    'child_count': len(root),
                    'sample_structure': {child.tag: len(list(child)) for child in list(root)[:3]}
                }
            elif ext == '.parquet':
                df = pd.read_parquet(file_path, nrows=5)
                validation_results[file_path] = {
                    'status': 'SUCCESS',
                    'format': 'Parquet',
                    'columns': list(df.columns),
                    'record_count': '5+ (sample)',
                    'sample_data': df.head(2).to_dict('records')
                }
            elif ext == '.txt':
                with open(file_path, encoding='utf-8') as f:
                    lines = f.readlines()[:10]
                validation_results[file_path] = {
                    'status': 'SUCCESS',
                    'format': 'Text',
                    'line_count': len(lines),
                    'sample_content': ''.join(lines[:3])[:200]
                }
            print(f"✓ Successfully validated {test_file['name']}")
            samples_tested += 1
        except Exception as e:
            validation_results[file_path] = {
                'status': 'ERROR',
                'error': str(e),
                'format': ext
            }
            print(f"✗ Error validating {test_file['name']}: {e}")
            samples_tested += 1
    return validation_results
def main():
    base_path = "/app/government_rfp_bid_1927/data/dataset_rfp"
    # Explore directory structure
    all_files, file_types = explore_directory_structure(base_path)
    # Validate sample files
    validation_results = validate_sample_files(all_files)
    # Print detailed validation results
    print("\n=== DETAILED VALIDATION RESULTS ===\n")
    for file_path, result in validation_results.items():
        print(f"File: {os.path.basename(file_path)}")
        print(f"Status: {result['status']}")
        print(f"Format: {result['format']}")
        if result['status'] == 'SUCCESS':
            if 'record_count' in result:
                print(f"Records: {result['record_count']}")
            if 'columns' in result:
                print(f"Columns: {result['columns']}")
            if 'sample_keys' in result:
                print(f"Sample Keys: {result['sample_keys']}")
            if 'sample_record' in result:
                print(f"Sample Record: {result['sample_record']}")
        else:
            print(f"Error: {result['error']}")
        print("-" * 50)
    # Final recommendations
    print("\n=== RECOMMENDATIONS ===")
    if not all_files:
        print("❌ NO DATA FOUND - External data acquisition required")
        print("→ Proceed to download RFP data from sam.gov Google Cloud Storage")
    elif not validation_results or all(r['status'] == 'ERROR' for r in validation_results.values()):
        print("❌ DATA PRESENT BUT UNREADABLE - Investigation required")
        print("→ Check file formats and encoding issues")
    else:
        successful_validations = [r for r in validation_results.values() if r['status'] == 'SUCCESS']
        print(f"✓ USABLE DATA FOUND - {len(successful_validations)} file type(s) validated successfully")
        print("→ Proceed with existing data analysis")
        # Suggest best file format to use
        if any(r['format'] in ['JSON', 'JSON Lines'] for r in successful_validations):
            print("→ Recommend using JSON files as primary data source")
        elif any(r['format'] == 'CSV' for r in successful_validations):
            print("→ Recommend using CSV files as primary data source")
        elif any(r['format'] == 'Parquet' for r in successful_validations):
            print("→ Recommend using Parquet files as primary data source")
if __name__ == "__main__":
    main()
