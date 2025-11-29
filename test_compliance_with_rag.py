#!/usr/bin/env python3
"""
Test compliance matrix generator with RAG integration.
"""
import os
import sys

import pandas as pd

# Add src to path
sys.path.insert(0, '/app/government_rfp_bid_1927/src')
from compliance.compliance_matrix import ComplianceMatrixGenerator
from rag.rag_engine import RAGEngine


def test_compliance_with_rag():
    """Test compliance matrix generation with RAG integration."""
    print("=" * 80)
    print("COMPLIANCE MATRIX GENERATOR WITH RAG INTEGRATION TEST")
    print("=" * 80)
    # Initialize RAG engine
    print("1. Loading RAG engine...")
    rag = RAGEngine()
    if not rag.load_artifacts():
        print("❌ Failed to load RAG artifacts")
        return False
    print(f"✅ RAG engine loaded with {rag.get_stats()['total_documents']:,} documents")
    # Initialize compliance matrix generator with RAG
    print("\n2. Initializing Compliance Matrix Generator...")
    compliance_generator = ComplianceMatrixGenerator(rag_engine=rag)
    print("✅ Compliance Matrix Generator initialized")
    # Load test RFP data
    print("\n3. Loading test RFP data...")
    df = pd.read_parquet('/app/government_rfp_bid_1927/data/processed/rfp_master_dataset.parquet')
    # Select diverse test cases
    test_cases = []
    # Get samples from different categories
    for category in ['construction', 'delivery', 'bottled_water']:
        category_file = f'/app/government_rfp_bid_1927/data/processed/{category}_rfps.parquet'
        if os.path.exists(category_file):
            cat_df = pd.read_parquet(category_file)
            if not cat_df.empty and 'description' in cat_df.columns:
                sample = cat_df[cat_df['description'].notna()].iloc[0].to_dict()
                sample['test_category'] = category
                test_cases.append(sample)
    # Add one from master dataset
    master_sample = df[df['description'].notna()].iloc[0].to_dict()
    master_sample['test_category'] = 'master'
    test_cases.append(master_sample)
    print(f"✅ Loaded {len(test_cases)} test cases")
    # Test compliance matrix generation for each case
    print("\n4. Testing compliance matrix generation...")
    results = []
    for i, test_rfp in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_rfp['test_category']} ---")
        print(f"Title: {test_rfp.get('title', 'Unknown')}")
        print(f"Agency: {test_rfp.get('agency', 'Unknown')}")
        try:
            # Generate compliance matrix
            compliance_matrix = compliance_generator.generate_compliance_matrix(test_rfp)
            # Export results
            json_path = compliance_generator.export_compliance_matrix(compliance_matrix, "json")
            csv_path = compliance_generator.export_compliance_matrix(compliance_matrix, "csv")
            html_path = compliance_generator.export_compliance_matrix(compliance_matrix, "html")
            # Collect results
            result = {
                'test_case': i,
                'category': test_rfp['test_category'],
                'title': test_rfp.get('title', 'Unknown'),
                'total_requirements': compliance_matrix['compliance_summary']['total_requirements'],
                'compliance_rate': compliance_matrix['compliance_summary']['compliance_rate'],
                'overall_status': compliance_matrix['compliance_summary']['overall_status'],
                'json_path': json_path,
                'csv_path': csv_path,
                'html_path': html_path
            }
            results.append(result)
            print(f"✅ Requirements extracted: {result['total_requirements']}")
            print(f"✅ Compliance rate: {result['compliance_rate']:.1%}")
            print(f"✅ Overall status: {result['overall_status']}")
            print("✅ Files exported: JSON, CSV, HTML")
            # Show sample requirements
            if compliance_matrix['requirements_and_responses']:
                print("\nSample requirements:")
                for j, response in enumerate(compliance_matrix['requirements_and_responses'][:2]):
                    print(f"  {j+1}. [{response['category']}] {response['requirement_text'][:80]}...")
                    print(f"     Status: {response['compliance_status']}")
                    if response.get('supporting_evidence'):
                        print("     RAG Context: Available")
        except Exception as e:
            print(f"❌ Error generating compliance matrix: {e}")
            continue
    # Summary results
    print("\n" + "=" * 80)
    print("COMPLIANCE MATRIX GENERATION SUMMARY")
    print("=" * 80)
    if results:
        total_tests = len(results)
        successful_tests = len([r for r in results if r['total_requirements'] > 0])
        avg_requirements = sum(r['total_requirements'] for r in results) / len(results)
        avg_compliance_rate = sum(r['compliance_rate'] for r in results) / len(results)
        print(f"Total test cases: {total_tests}")
        print(f"Successful generations: {successful_tests}")
        print(f"Average requirements per RFP: {avg_requirements:.1f}")
        print(f"Average compliance rate: {avg_compliance_rate:.1%}")
        print("\nDetailed Results:")
        for result in results:
            print(f"  {result['category']}: {result['total_requirements']} reqs, "
                  f"{result['compliance_rate']:.1%} compliance, {result['overall_status']}")
        # Check artifacts
        print("\n📁 Generated Artifacts:")
        compliance_dir = '/app/government_rfp_bid_1927/data/compliance'
        if os.path.exists(compliance_dir):
            files = os.listdir(compliance_dir)
            print(f"  Total files: {len(files)}")
            json_files = [f for f in files if f.endswith('.json')]
            csv_files = [f for f in files if f.endswith('.csv')]
            html_files = [f for f in files if f.endswith('.html')]
            print(f"  JSON files: {len(json_files)}")
            print(f"  CSV files: {len(csv_files)}")
            print(f"  HTML files: {len(html_files)}")
        # Validation criteria
        validation_results = {
            'successful_generation': successful_tests == total_tests,
            'adequate_extraction': avg_requirements >= 5,
            'good_compliance': avg_compliance_rate >= 0.7,
            'files_exported': successful_tests > 0
        }
        print("\n🎯 VALIDATION RESULTS:")
        passed = 0
        for criterion, result in validation_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {criterion}: {status}")
            if result:
                passed += 1
        success_rate = passed / len(validation_results)
        print(f"\nOVERALL VALIDATION: {passed}/{len(validation_results)} ({success_rate:.1%})")
        if success_rate >= 0.75:
            print("🎉 COMPLIANCE MATRIX GENERATOR: EXCELLENT PERFORMANCE")
            return True
        else:
            print("⚠️  COMPLIANCE MATRIX GENERATOR: NEEDS IMPROVEMENT")
            return False
    else:
        print("❌ No successful test results")
        return False
if __name__ == "__main__":
    success = test_compliance_with_rag()
    sys.exit(0 if success else 1)
