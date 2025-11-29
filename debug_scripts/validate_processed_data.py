import json
import os
from datetime import datetime

import pandas as pd


def validate_processed_datasets():
    """Validate all processed datasets and generate comprehensive report"""
    print("=== VALIDATING PROCESSED DATASETS ===\n")
    base_path = "/app/government_rfp_bid_1927/data/processed"
    # Files to validate
    files_to_check = {
        'master_parquet': 'rfp_master_dataset.parquet',
        'master_csv': 'rfp_master_dataset.csv',
        'bottled_water': 'bottled_water_rfps.parquet',
        'construction': 'construction_rfps.parquet',
        'delivery': 'delivery_rfps.parquet',
        'metadata': 'processing_metadata.json'
    }
    validation_results = {}
    # Check file existence and sizes
    print("File Existence and Size Check:")
    for file_type, filename in files_to_check.items():
        file_path = os.path.join(base_path, filename)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024**2)
            print(f"  ✓ {filename}: {size_mb:.2f}MB")
            validation_results[file_type] = {
                'exists': True,
                'size_mb': size_mb,
                'path': file_path
            }
        else:
            print(f"  ✗ {filename}: NOT FOUND")
            validation_results[file_type] = {'exists': False}
    # Validate parquet files
    print("\nDataset Structure Validation:")
    parquet_files = ['master_parquet', 'bottled_water', 'construction', 'delivery']
    for file_type in parquet_files:
        if validation_results[file_type]['exists']:
            try:
                df = pd.read_parquet(validation_results[file_type]['path'])
                validation_results[file_type].update({
                    'rows': len(df),
                    'columns': len(df.columns),
                    'column_names': list(df.columns),
                    'data_types': df.dtypes.to_dict(),
                    'sample_data': df.head(2).to_dict('records') if len(df) > 0 else []
                })
                print(f"  ✓ {file_type}: {len(df):,} rows × {len(df.columns)} columns")
                # Category-specific validation
                if file_type != 'master_parquet':
                    category_name = file_type
                    if 'category' in df.columns:
                        category_dist = df['category'].value_counts()
                        print(f"    Categories: {dict(category_dist)}")
            except Exception as e:
                print(f"  ✗ {file_type}: Error loading - {e}")
                validation_results[file_type]['error'] = str(e)
    # Validate metadata
    print("\nMetadata Validation:")
    if validation_results['metadata']['exists']:
        try:
            with open(validation_results['metadata']['path']) as f:
                metadata = json.load(f)
            validation_results['metadata']['content'] = metadata
            print("  ✓ Metadata loaded successfully")
            print(f"    Total records: {metadata.get('total_records', 'N/A')}")
            print(f"    Categories: {metadata.get('category_distribution', {})}")
            print(f"    Average quality: {metadata.get('data_quality_stats', {}).get('mean_quality_score', 'N/A')}")
        except Exception as e:
            print(f"  ✗ Metadata: Error loading - {e}")
            validation_results['metadata']['error'] = str(e)
    return validation_results
def validate_data_consistency(validation_results):
    """Validate data consistency across datasets"""
    print("\n=== DATA CONSISTENCY VALIDATION ===\n")
    # Load master dataset for comparison
    if validation_results['master_parquet']['exists']:
        try:
            master_df = pd.read_parquet(validation_results['master_parquet']['path'])
            # Check category totals
            master_categories = master_df['category'].value_counts().to_dict()
            print(f"Master dataset categories: {master_categories}")
            # Compare with individual category files
            consistency_issues = []
            for category in ['bottled_water', 'construction', 'delivery']:
                if validation_results[category]['exists']:
                    category_df = pd.read_parquet(validation_results[category]['path'])
                    category_count = len(category_df)
                    master_count = master_categories.get(category, 0)
                    if category_count != master_count:
                        consistency_issues.append(f"{category}: Category file has {category_count} records, master has {master_count}")
                    else:
                        print(f"  ✓ {category}: Consistent ({category_count} records)")
            if consistency_issues:
                print("\nConsistency Issues:")
                for issue in consistency_issues:
                    print(f"  ✗ {issue}")
            else:
                print("\n✓ All category datasets consistent with master dataset")
            return consistency_issues
        except Exception as e:
            print(f"Error validating consistency: {e}")
            return [f"Error loading master dataset: {e}"]
    return ["Master dataset not available for consistency check"]
def validate_data_quality(validation_results):
    """Validate data quality metrics"""
    print("\n=== DATA QUALITY VALIDATION ===\n")
    if validation_results['master_parquet']['exists']:
        try:
            master_df = pd.read_parquet(validation_results['master_parquet']['path'])
            # Check essential fields
            essential_fields = ['rfp_id', 'title', 'agency', 'naics_code', 'category']
            quality_issues = []
            print("Essential Field Completeness:")
            for field in essential_fields:
                if field in master_df.columns:
                    completeness = (master_df[field].notna() & (master_df[field] != 'nan')).mean()
                    print(f"  {field}: {completeness:.1%} complete")
                    if completeness < 0.9:
                        quality_issues.append(f"{field} only {completeness:.1%} complete")
                else:
                    quality_issues.append(f"{field} missing from dataset")
            # Check data quality score distribution
            if 'data_quality_score' in master_df.columns:
                quality_scores = master_df['data_quality_score']
                print("\nData Quality Score Distribution:")
                print(f"  Mean: {quality_scores.mean():.3f}")
                print(f"  Median: {quality_scores.median():.3f}")
                print(f"  High quality (≥0.8): {(quality_scores >= 0.8).mean():.1%}")
                print(f"  Low quality (<0.5): {(quality_scores < 0.5).mean():.1%}")
            # Check date fields
            date_fields = ['posted_date', 'response_deadline', 'award_date']
            print("\nDate Field Validation:")
            for field in date_fields:
                if field in master_df.columns:
                    valid_dates = pd.to_datetime(master_df[field], errors='coerce').notna()
                    print(f"  {field}: {valid_dates.mean():.1%} valid dates")
            # Check award amounts
            if 'award_amount_clean' in master_df.columns:
                valid_amounts = master_df['award_amount_clean'].notna()
                print("\nAward Amount Validation:")
                print(f"  Valid amounts: {valid_amounts.mean():.1%}")
                if valid_amounts.any():
                    amounts = master_df['award_amount_clean'].dropna()
                    print(f"  Range: ${amounts.min():,.2f} - ${amounts.max():,.2f}")
                    print(f"  Median: ${amounts.median():,.2f}")
            return quality_issues
        except Exception as e:
            return [f"Error validating data quality: {e}"]
    return ["Master dataset not available for quality validation"]
def generate_validation_report(validation_results, consistency_issues, quality_issues):
    """Generate comprehensive validation report"""
    print("\n=== GENERATING VALIDATION REPORT ===\n")
    # Create comprehensive report
    report = {
        'validation_timestamp': datetime.now().isoformat(),
        'file_validation': validation_results,
        'consistency_validation': {
            'issues_found': len(consistency_issues),
            'issues': consistency_issues
        },
        'quality_validation': {
            'issues_found': len(quality_issues),
            'issues': quality_issues
        },
        'overall_status': 'PASS' if len(consistency_issues) == 0 and len(quality_issues) == 0 else 'ISSUES_FOUND',
        'summary': {
            'files_created': sum(1 for r in validation_results.values() if r.get('exists', False)),
            'total_records': validation_results.get('master_parquet', {}).get('rows', 0),
            'categories_processed': len([k for k in validation_results.keys() if k in ['bottled_water', 'construction', 'delivery'] and validation_results[k].get('exists', False)])
        }
    }
    # Save detailed report
    report_path = "/app/government_rfp_bid_1927/analysis/data_processing_validation_report.json"
    os.makedirs("/app/government_rfp_bid_1927/analysis", exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    # Create human-readable summary
    summary_path = "/app/government_rfp_bid_1927/analysis/processing_pipeline_summary.md"
    with open(summary_path, 'w') as f:
        f.write("# RFP Data Processing Pipeline - Validation Report\n\n")
        f.write(f"**Validation Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Overall Status:** {report['overall_status']}\n\n")
        f.write("## Pipeline Results Summary\n\n")
        f.write(f"- **Total Records Processed:** {report['summary']['total_records']:,}\n")
        f.write(f"- **Files Created:** {report['summary']['files_created']}\n")
        f.write(f"- **Categories Processed:** {report['summary']['categories_processed']}\n\n")
        f.write("## File Creation Status\n\n")
        for file_type, result in validation_results.items():
            if result.get('exists'):
                f.write(f"- ✅ **{file_type}**: {result.get('size_mb', 0):.2f}MB")
                if 'rows' in result:
                    f.write(f" ({result['rows']:,} records)")
                f.write("\n")
            else:
                f.write(f"- ❌ **{file_type}**: NOT CREATED\n")
        f.write("\n## Data Quality Assessment\n\n")
        if quality_issues:
            f.write("### Issues Found:\n")
            for issue in quality_issues:
                f.write(f"- ⚠️ {issue}\n")
        else:
            f.write("✅ No significant data quality issues found.\n")
        f.write("\n## Data Consistency Check\n\n")
        if consistency_issues:
            f.write("### Issues Found:\n")
            for issue in consistency_issues:
                f.write(f"- ⚠️ {issue}\n")
        else:
            f.write("✅ All datasets are consistent.\n")
        f.write("\n## Next Steps\n\n")
        f.write("1. Proceed with Exploratory Data Analysis (EDA)\n")
        f.write("2. Generate comprehensive data insights and visualizations\n")
        f.write("3. Create baseline statistics for system requirements\n")
        f.write("4. Prepare data dictionary for downstream ML pipelines\n")
    print(f"✓ Validation report saved: {report_path}")
    print(f"✓ Summary report saved: {summary_path}")
    return report, report_path, summary_path
def main():
    # Validate processed datasets
    validation_results = validate_processed_datasets()
    # Check data consistency
    consistency_issues = validate_data_consistency(validation_results)
    # Validate data quality
    quality_issues = validate_data_quality(validation_results)
    # Generate comprehensive report
    report, report_path, summary_path = generate_validation_report(validation_results, consistency_issues, quality_issues)
    # Final summary
    print("\n=== VALIDATION COMPLETE ===")
    print(f"Overall Status: {report['overall_status']}")
    print(f"Files Created: {report['summary']['files_created']}")
    print(f"Total Records: {report['summary']['total_records']:,}")
    print(f"Quality Issues: {len(quality_issues)}")
    print(f"Consistency Issues: {len(consistency_issues)}")
    if report['overall_status'] == 'PASS':
        print("✅ DATA PROCESSING PIPELINE SUCCESSFUL")
        print("✅ All datasets validated and ready for EDA")
    else:
        print("⚠️ Issues found - review validation report")
if __name__ == "__main__":
    main()
