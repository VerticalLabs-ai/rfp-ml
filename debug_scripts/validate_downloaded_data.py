import json
import os
from datetime import datetime

import pandas as pd


def validate_downloaded_files():
    """Validate downloaded CSV files and examine their structure"""
    raw_data_path = "/app/government_rfp_bid_1927/data/raw"
    print("=== VALIDATING DOWNLOADED DATASETS ===\n")
    # Find all CSV files
    csv_files = [f for f in os.listdir(raw_data_path) if f.endswith(".csv")]
    validation_results = {}
    for csv_file in csv_files:
        file_path = os.path.join(raw_data_path, csv_file)
        file_size_mb = os.path.getsize(file_path) / (1024**2)
        print(f"Validating: {csv_file} ({file_size_mb:.1f}MB)")
        try:
            # Read first few rows to understand structure
            sample_df = pd.read_csv(file_path, nrows=5, low_memory=False)
            # Get basic info
            total_columns = len(sample_df.columns)
            # Try to get row count (approximation for large files)
            try:
                if file_size_mb > 100:  # For large files, estimate
                    with open(file_path) as f:
                        # Count lines in first 1MB
                        chunk = f.read(1024 * 1024)
                        lines_in_chunk = chunk.count("\n")
                        estimated_rows = int(
                            (lines_in_chunk * file_size_mb) - 1
                        )  # -1 for header
                    row_count = f"~{estimated_rows:,} (estimated)"
                else:
                    # For smaller files, get exact count
                    full_df = pd.read_csv(file_path, low_memory=False)
                    row_count = f"{len(full_df):,} (exact)"
            except Exception:
                row_count = "Unknown"
            validation_results[csv_file] = {
                "status": "SUCCESS",
                "file_size_mb": file_size_mb,
                "columns": list(sample_df.columns),
                "total_columns": total_columns,
                "estimated_rows": row_count,
                "sample_data": sample_df.head(2).to_dict("records"),
                "data_types": sample_df.dtypes.to_dict(),
            }
            print(f"  ✓ Columns: {total_columns}")
            print(f"  ✓ Rows: {row_count}")
            print("  ✓ Sample loaded successfully")
        except Exception as e:
            validation_results[csv_file] = {
                "status": "ERROR",
                "error": str(e),
                "file_size_mb": file_size_mb,
            }
            print(f"  ✗ Error: {e}")
        print()
    return validation_results


def analyze_rfp_data_structure(validation_results):
    """Analyze the structure of RFP data for key fields"""
    print("=== RFP DATA STRUCTURE ANALYSIS ===\n")
    # Look for common RFP fields across all files
    all_columns = set()
    for _, result in validation_results.items():
        if result["status"] == "SUCCESS":
            all_columns.update(result["columns"])
    # Key fields we're looking for
    key_fields_mapping = {
        "solicitation_id": ["solicitation", "id", "number", "rfp_id", "opportunity_id"],
        "title": ["title", "subject", "description", "name"],
        "agency": ["agency", "organization", "dept", "department", "office"],
        "posting_date": ["posted", "date", "published", "created"],
        "response_deadline": ["deadline", "due", "closing", "submission", "response"],
        "estimated_value": ["value", "amount", "price", "cost", "budget", "dollar"],
        "nigp_codes": ["nigp", "commodity", "code"],
        "naics_codes": ["naics", "industry", "classification"],
        "requirements": ["requirements", "description", "specifications", "details"],
        "location": ["location", "place", "state", "city", "address"],
    }
    print("COLUMN ANALYSIS:")
    print(f"Total unique columns found: {len(all_columns)}")
    # Find matching columns for each key field
    field_matches = {}
    for key_field, search_terms in key_fields_mapping.items():
        matches = []
        for col in all_columns:
            col_lower = col.lower()
            if any(term in col_lower for term in search_terms):
                matches.append(col)
        field_matches[key_field] = matches
        if matches:
            print(f"✓ {key_field}: {matches}")
        else:
            print(f"✗ {key_field}: No matches found")
    return field_matches, all_columns


def check_target_categories(validation_results):
    """Check for data related to target NIGP/NAICS categories"""
    print("\n=== TARGET CATEGORY ANALYSIS ===\n")
    target_nigp = ["065"]  # Water/beverages
    target_naics = [
        "312112",
        "236",
        "237",
        "484",
        "492",
    ]  # Beverages, construction, delivery
    category_findings = {}
    for file, result in validation_results.items():
        if result["status"] == "SUCCESS":
            print(f"Analyzing {file}:")
            # Look for NIGP/NAICS columns
            nigp_cols = [col for col in result["columns"] if "nigp" in col.lower()]
            naics_cols = [col for col in result["columns"] if "naics" in col.lower()]
            print(f"  NIGP columns: {nigp_cols}")
            print(f"  NAICS columns: {naics_cols}")
            # Check sample data for target categories
            found_categories = []
            for record in result["sample_data"]:
                record_str = str(record).lower()
                for nigp in target_nigp:
                    if nigp in record_str:
                        found_categories.append(f"NIGP {nigp}")
                for naics in target_naics:
                    if naics in record_str:
                        found_categories.append(f"NAICS {naics}")
            if found_categories:
                print(f"  ✓ Found target categories in sample: {set(found_categories)}")
            else:
                print(
                    "  ○ No target categories found in sample (may exist in full dataset)"
                )
            category_findings[file] = {
                "nigp_columns": nigp_cols,
                "naics_columns": naics_cols,
                "sample_categories": found_categories,
            }
        print()
    return category_findings


def save_validation_report(
    validation_results, field_matches, category_findings, base_path
):
    """Save comprehensive validation report"""
    print("=== SAVING VALIDATION REPORT ===\n")
    # Create comprehensive report
    report = {
        "validation_timestamp": datetime.now().isoformat(),
        "files_validated": len(validation_results),
        "successful_validations": len(
            [r for r in validation_results.values() if r["status"] == "SUCCESS"]
        ),
        "total_size_mb": sum([r["file_size_mb"] for r in validation_results.values()]),
        "file_details": validation_results,
        "field_mapping_analysis": field_matches,
        "category_analysis": category_findings,
        "next_steps": [
            "Load full datasets and apply filtering for target categories",
            "Standardize schema across all datasets",
            "Extract and clean key fields (dates, values, categories)",
            "Perform comprehensive EDA on filtered data",
            "Create master processed dataset",
        ],
    }
    # Save detailed validation report
    os.makedirs(f"{base_path}/data/processed", exist_ok=True)
    report_path = f"{base_path}/data/processed/data_validation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"✓ Validation report saved: {report_path}")
    # Create summary for human reading
    summary_path = f"{base_path}/analysis/data_validation_summary.md"
    os.makedirs(f"{base_path}/analysis", exist_ok=True)
    with open(summary_path, "w") as f:
        f.write("# RFP Dataset Validation Summary\n\n")
        f.write(
            f"**Validation Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )
        f.write("## Downloaded Files Status\n\n")
        for file, result in validation_results.items():
            status_emoji = "✅" if result["status"] == "SUCCESS" else "❌"
            f.write(f"- {status_emoji} **{file}** ({result['file_size_mb']:.1f}MB)\n")
            if result["status"] == "SUCCESS":
                f.write(f"  - Columns: {result['total_columns']}\n")
                f.write(f"  - Rows: {result['estimated_rows']}\n")
            else:
                f.write(f"  - Error: {result.get('error', 'Unknown error')}\n")
        f.write("\n## Key Field Analysis\n\n")
        for field, matches in field_matches.items():
            if matches:
                f.write(f"- ✅ **{field}**: {', '.join(matches)}\n")
            else:
                f.write(f"- ❌ **{field}**: No matching columns found\n")
        f.write("\n## Target Category Analysis\n\n")
        f.write("Looking for NIGP codes: 065 (water/beverages)\n")
        f.write(
            "Looking for NAICS codes: 312112 (beverages), 236/237 (construction), 484/492 (delivery)\n\n"
        )
        for file, findings in category_findings.items():
            f.write(f"**{file}:**\n")
            f.write(
                f"- NIGP columns: {findings['nigp_columns'] if findings['nigp_columns'] else 'None found'}\n"
            )
            f.write(
                f"- NAICS columns: {findings['naics_columns'] if findings['naics_columns'] else 'None found'}\n"
            )
            f.write(
                f"- Sample categories: {findings['sample_categories'] if findings['sample_categories'] else 'None in sample'}\n\n"
            )
        f.write("## Next Steps\n\n")
        for i, step in enumerate(report["next_steps"], 1):
            f.write(f"{i}. {step}\n")
    print(f"✓ Validation summary saved: {summary_path}")
    return report_path, summary_path


def main():
    base_path = "/app/government_rfp_bid_1927"
    # Validate downloaded files
    validation_results = validate_downloaded_files()
    # Analyze data structure
    field_matches, all_columns = analyze_rfp_data_structure(validation_results)
    # Check for target categories
    category_findings = check_target_categories(validation_results)
    # Save comprehensive report
    report_path, summary_path = save_validation_report(
        validation_results, field_matches, category_findings, base_path
    )
    print("\n=== VALIDATION COMPLETE ===")
    print(
        f"✓ {len([r for r in validation_results.values() if r['status'] == 'SUCCESS'])}/{len(validation_results)} files validated successfully"
    )
    print(
        f"✓ Total data size: {sum([r['file_size_mb'] for r in validation_results.values()]):.1f}MB"
    )
    print("✓ Analysis reports saved")
    print("\nReady to proceed with data loading and processing!")


if __name__ == "__main__":
    main()
