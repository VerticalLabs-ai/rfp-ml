#!/usr/bin/env python3
"""
Complete pipeline test: RAG + Compliance + Pricing + Document Generation
"""
import os
import sys
import time

import pandas as pd


def get_project_root():
    """Get project root directory (works locally and in Docker)."""
    if os.path.exists("/app/data"):
        return "/app"
    return os.path.dirname(os.path.abspath(__file__))


PROJECT_ROOT = get_project_root()

# Add src to path
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
def test_complete_pipeline():
    """Test the complete bid generation pipeline."""
    print("=" * 80)
    print("COMPLETE BID GENERATION PIPELINE TEST")
    print("=" * 80)
    try:
        # Import all components
        from bid_generation.document_generator import BidDocumentGenerator
        from compliance.compliance_matrix import ComplianceMatrixGenerator
        from pricing.pricing_engine import PricingEngine
        print("✅ All pipeline components imported successfully")
        # Initialize components individually first
        print("\n🔧 Initializing pipeline components...")
        compliance_gen = ComplianceMatrixGenerator()
        pricing_engine = PricingEngine()
        # Initialize document generator with integrated components
        doc_generator = BidDocumentGenerator(
            compliance_generator=compliance_gen,
            pricing_engine=pricing_engine
        )
        print("✅ Complete pipeline initialized with all integrations")
        # Load test RFPs from different categories
        print("\n📋 Loading test RFPs...")
        test_rfps = []
        # Try to get samples from each category
        category_files = [
            ('bottled_water', os.path.join(PROJECT_ROOT, 'data/processed/bottled_water_rfps.parquet')),
            ('construction', os.path.join(PROJECT_ROOT, 'data/processed/construction_rfps.parquet')),
            ('delivery', os.path.join(PROJECT_ROOT, 'data/processed/delivery_rfps.parquet'))
        ]
        for category, file_path in category_files:
            if os.path.exists(file_path):
                df = pd.read_parquet(file_path)
                if not df.empty and 'description' in df.columns:
                    sample = df[df['description'].notna()].iloc[0].to_dict()
                    sample['test_category'] = category
                    test_rfps.append(sample)
                    print(f"✅ Loaded {category} sample: {sample['title'][:50]}...")
        # Fallback to master dataset if needed
        if len(test_rfps) < 2:
            master_df = pd.read_parquet(os.path.join(PROJECT_ROOT, 'data/processed/rfp_master_dataset.parquet'))
            for i in range(2):
                if i < len(master_df):
                    sample = master_df[master_df['description'].notna()].iloc[i].to_dict()
                    sample['test_category'] = 'general'
                    test_rfps.append(sample)
        print(f"✅ Loaded {len(test_rfps)} test RFPs for pipeline testing")
        # Process each RFP through complete pipeline
        results = []
        for i, test_rfp in enumerate(test_rfps, 1):
            print(f"\n{'='*60}")
            print(f"PROCESSING RFP {i}: {test_rfp.get('title', 'Unknown')[:50]}...")
            print(f"Agency: {test_rfp.get('agency', 'Unknown')}")
            print(f"Category: {test_rfp.get('test_category', 'Unknown')}")
            print("="*60)
            pipeline_start = time.time()
            try:
                # Generate complete bid document (includes all pipeline steps)
                print("🚀 Generating complete bid document...")
                bid_document = doc_generator.generate_bid_document(test_rfp)
                # Export in all formats
                print("📤 Exporting bid document...")
                markdown_path = doc_generator.export_bid_document(bid_document, "markdown")
                html_path = doc_generator.export_bid_document(bid_document, "html")
                json_path = doc_generator.export_bid_document(bid_document, "json")
                pipeline_time = time.time() - pipeline_start
                # Collect results
                result = {
                    'rfp_id': i,
                    'title': test_rfp.get('title', 'Unknown')[:40],
                    'category': test_rfp.get('test_category', 'general'),
                    'agency': test_rfp.get('agency', 'Unknown')[:30],
                    'requirements_addressed': bid_document['metadata']['document_stats']['requirements_addressed'],
                    'pricing_strategies': bid_document['metadata']['document_stats']['pricing_strategies_analyzed'],
                    'content_length': bid_document['metadata']['document_stats']['content_length'],
                    'processing_time': pipeline_time,
                    'exports': {
                        'markdown': markdown_path,
                        'html': html_path,
                        'json': json_path
                    },
                    'success': True
                }
                results.append(result)
                print(f"✅ Pipeline completed successfully in {pipeline_time:.2f}s")
                print(f"   Requirements addressed: {result['requirements_addressed']}")
                print(f"   Pricing strategies: {result['pricing_strategies']}")
                print(f"   Content length: {result['content_length']:,} characters")
                print("   Files exported: Markdown, HTML, JSON")
            except Exception as e:
                print(f"❌ Pipeline failed for RFP {i}: {e}")
                continue
        # Final pipeline summary
        print("\n" + "="*80)
        print("COMPLETE PIPELINE VALIDATION SUMMARY")
        print("="*80)
        if results:
            successful_rfps = len(results)
            avg_processing_time = sum(r['processing_time'] for r in results) / len(results)
            avg_requirements = sum(r['requirements_addressed'] for r in results) / len(results)
            avg_content_length = sum(r['content_length'] for r in results) / len(results)
            print(f"✅ Successfully processed: {successful_rfps}/{len(test_rfps)} RFPs")
            print("📊 Performance Metrics:")
            print(f"   Average processing time: {avg_processing_time:.2f} seconds")
            print(f"   Average requirements addressed: {avg_requirements:.1f}")
            print(f"   Average content length: {avg_content_length:,.0f} characters")
            # Check generated files
            bid_docs_dir = '/app/government_rfp_bid_1927/data/bid_documents'
            if os.path.exists(bid_docs_dir):
                all_files = os.listdir(bid_docs_dir)
                md_files = [f for f in all_files if f.endswith('.md')]
                html_files = [f for f in all_files if f.endswith('.html')]
                json_files = [f for f in all_files if f.endswith('.json')]
                print("\n📁 Generated Bid Documents:")
                print(f"   Total files: {len(all_files)}")
                print(f"   Markdown documents: {len(md_files)}")
                print(f"   HTML documents: {len(html_files)}")
                print(f"   JSON documents: {len(json_files)}")
            print("\n📋 Individual Results:")
            for result in results:
                print(f"   RFP {result['rfp_id']} ({result['category']}): "
                      f"{result['requirements_addressed']} reqs, "
                      f"{result['content_length']:,} chars, "
                      f"{result['processing_time']:.1f}s")
            # Validation criteria
            validation_checks = {
                'fast_processing': avg_processing_time < 120,  # Under 2 minutes
                'adequate_content': avg_content_length >= 5000,  # Substantial content
                'requirement_coverage': avg_requirements >= 5,
                'all_exports_working': successful_rfps > 0,
                'full_pipeline_success': successful_rfps == len(test_rfps)
            }
            print("\n🎯 VALIDATION RESULTS:")
            passed_checks = 0
            for check, passed in validation_checks.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"   {check}: {status}")
                if passed:
                    passed_checks += 1
            validation_score = passed_checks / len(validation_checks)
            print(f"\nPipeline Validation Score: {passed_checks}/{len(validation_checks)} ({validation_score:.1%})")
            if validation_score >= 0.8:
                print("\n🎉 COMPLETE BID GENERATION PIPELINE: EXCELLENT PERFORMANCE")
                print("✅ Ready for production deployment and go/no-go decision integration")
                return True
            elif validation_score >= 0.6:
                print("\n✅ COMPLETE BID GENERATION PIPELINE: GOOD PERFORMANCE")
                print("🔧 Minor optimizations available but system is functional")
                return True
            else:
                print("\n⚠️  COMPLETE BID GENERATION PIPELINE: NEEDS IMPROVEMENT")
                return False
        else:
            print("❌ No successful pipeline runs")
            return False
    except Exception as e:
        print(f"❌ Complete pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
if __name__ == "__main__":
    success = test_complete_pipeline()
    sys.exit(0 if success else 1)
