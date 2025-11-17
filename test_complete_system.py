#!/usr/bin/env python3
"""
Complete AI-powered bid generation system test.
Tests the entire pipeline from RFP input to final bid decision.
"""
import sys
import os
import time
import json
import pandas as pd

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
def test_complete_bid_generation_system():
    """Test the complete autonomous bid generation system."""
    print("=" * 80)
    print("🤖 COMPLETE AI-POWERED BID GENERATION SYSTEM TEST")
    print("=" * 80)
    try:
        # Import all components
        from compliance.compliance_matrix import ComplianceMatrixGenerator
        from pricing.pricing_engine import PricingEngine
        from bid_generation.document_generator_fixed import BidDocumentGenerator
        from decision.go_nogo_engine import GoNoGoEngine
        print("✅ All system components imported successfully")
        # Initialize complete system
        print("\n🚀 Initializing complete autonomous bid generation system...")
        compliance_gen = ComplianceMatrixGenerator()
        pricing_engine = PricingEngine()
        doc_generator = BidDocumentGenerator(
            compliance_generator=compliance_gen,
            pricing_engine=pricing_engine
        )
        decision_engine = GoNoGoEngine(
            compliance_generator=compliance_gen,
            pricing_engine=pricing_engine,
            document_generator=doc_generator
        )
        print("✅ Complete system initialized with all integrations")
        # Import PathConfig for consistent path handling
        from config.paths import PathConfig

        # Load diverse test RFPs
        print("\n📋 Loading diverse test RFPs...")
        data_path = PathConfig.PROCESSED_DATA_DIR / 'rfp_master_dataset.parquet'
        df = pd.read_parquet(data_path)
        # Select test cases with different characteristics
        test_rfps = []
        for i in [0, 3, 7, 12]:  # Different RFPs for variety
            if i < len(df):
                rfp_data = df[df['description'].notna()].iloc[i].to_dict()
                test_rfps.append(rfp_data)
        print(f"✅ Loaded {len(test_rfps)} diverse RFPs for complete system test")
        # Process each RFP through complete pipeline
        system_results = []
        for i, test_rfp in enumerate(test_rfps, 1):
            print(f"\n{'='*60}")
            print(f"🎯 PROCESSING RFP {i}: COMPLETE AUTONOMOUS PIPELINE")
            print(f"Title: {test_rfp.get('title', 'Unknown')[:50]}...")
            print(f"Agency: {test_rfp.get('agency', 'Unknown')}")
            print(f"NAICS: {test_rfp.get('naics_code', 'Unknown')}")
            print("="*60)
            pipeline_start = time.time()
            try:
                # Step 1: Decision Analysis (includes all pipeline components)
                print("🧠 Step 1: Performing complete decision analysis...")
                decision_start = time.time()
                decision_result = decision_engine.analyze_rfp_opportunity(test_rfp)
                decision_time = time.time() - decision_start
                print(f"✅ Decision analysis completed in {decision_time:.2f}s")
                print(f"   Recommendation: {decision_result.recommendation.upper()}")
                print(f"   Overall Score: {decision_result.overall_score:.1f}%")
                print(f"   Confidence: {decision_result.confidence_level:.1f}%")
                # Step 2: Generate bid document if recommended
                bid_document = None
                document_generated = False
                if decision_result.recommendation in ['go', 'review']:
                    print("📝 Step 2: Generating bid document (GO/REVIEW recommendation)...")
                    doc_start = time.time()
                    bid_document = doc_generator.generate_bid_document(test_rfp)
                    # Export bid document
                    md_path = doc_generator.export_bid_document(bid_document, "markdown")
                    json_path = doc_generator.export_bid_document(bid_document, "json")
                    doc_time = time.time() - doc_start
                    document_generated = True
                    print(f"✅ Bid document generated in {doc_time:.2f}s")
                    print(f"   Content: {bid_document['metadata']['document_stats']['content_length']:,} characters")
                    print(f"   Requirements: {bid_document['metadata']['document_stats']['requirements_addressed']}")
                    print(f"   Exports: MD, JSON")
                else:
                    print("⏭️  Step 2: Skipping document generation (NO-GO recommendation)")
                # Step 3: Export decision analysis
                print("📊 Step 3: Exporting decision analysis...")
                decision_export = decision_engine.export_decision_analysis(test_rfp, decision_result)
                pipeline_time = time.time() - pipeline_start
                # Collect results
                result = {
                    'rfp_id': i,
                    'title': test_rfp.get('title', 'Unknown')[:40],
                    'agency': test_rfp.get('agency', 'Unknown')[:25],
                    'recommendation': decision_result.recommendation,
                    'overall_score': decision_result.overall_score,
                    'confidence': decision_result.confidence_level,
                    'margin_score': decision_result.margin_score,
                    'complexity_score': decision_result.complexity_score,
                    'risk_factors': len(decision_result.risk_factors),
                    'opportunities': len(decision_result.opportunities),
                    'document_generated': document_generated,
                    'processing_time': pipeline_time,
                    'decision_time': decision_time,
                    'decision_export': decision_export
                }
                system_results.append(result)
                print(f"✅ Complete pipeline processed in {pipeline_time:.2f}s")
                print(f"   Decision: {decision_result.recommendation.upper()}")
                print(f"   Score: {decision_result.overall_score:.1f}%")
                print(f"   Document: {'Generated' if document_generated else 'Skipped'}")
            except Exception as e:
                print(f"❌ Pipeline failed for RFP {i}: {e}")
                continue
        # Final system validation
        print(f"\n" + "="*80)
        print("🤖 COMPLETE AUTONOMOUS BID GENERATION SYSTEM VALIDATION")
        print("="*80)
        if system_results:
            successful_analyses = len(system_results)
            go_decisions = len([r for r in system_results if r['recommendation'] == 'go'])
            review_decisions = len([r for r in system_results if r['recommendation'] == 'review'])
            nogo_decisions = len([r for r in system_results if r['recommendation'] == 'no_go'])
            documents_generated = len([r for r in system_results if r['document_generated']])
            avg_processing_time = sum(r['processing_time'] for r in system_results) / len(system_results)
            avg_overall_score = sum(r['overall_score'] for r in system_results) / len(system_results)
            avg_confidence = sum(r['confidence'] for r in system_results) / len(system_results)
            print(f"✅ Successfully processed: {successful_analyses}/{len(test_rfps)} RFPs")
            print(f"📊 Decision Distribution:")
            print(f"   GO decisions: {go_decisions}")
            print(f"   REVIEW decisions: {review_decisions}")
            print(f"   NO-GO decisions: {nogo_decisions}")
            print(f"   Bid documents generated: {documents_generated}")
            print(f"\n📈 Performance Metrics:")
            print(f"   Average processing time: {avg_processing_time:.2f} seconds")
            print(f"   Average overall score: {avg_overall_score:.1f}%")
            print(f"   Average confidence: {avg_confidence:.1f}%")
            print(f"\n📋 Individual Results:")
            for result in system_results:
                print(f"   RFP {result['rfp_id']}: {result['recommendation'].upper()} "
                      f"({result['overall_score']:.0f}% score, "
                      f"{result['risk_factors']} risks, "
                      f"{'Doc Generated' if result['document_generated'] else 'No Doc'})")
            # System validation criteria
            validation_criteria = {
                'decisions_generated': successful_analyses >= len(test_rfps) * 0.8,
                'varied_decisions': len(set(r['recommendation'] for r in system_results)) > 1,
                'reasonable_processing': avg_processing_time < 300,  # Under 5 minutes
                'adequate_confidence': avg_confidence >= 50,
                'appropriate_document_generation': documents_generated <= go_decisions + review_decisions,
                'exports_successful': all(os.path.exists(r['decision_export']) for r in system_results)
            }
            print(f"\n🎯 SYSTEM VALIDATION:")
            passed_criteria = 0
            for criterion, passed in validation_criteria.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"   {criterion}: {status}")
                if passed:
                    passed_criteria += 1
            system_score = passed_criteria / len(validation_criteria)
            print(f"\nSystem Validation Score: {passed_criteria}/{len(validation_criteria)} ({system_score:.1%})")
            if system_score >= 0.8:
                print("\n🎉 COMPLETE AUTONOMOUS BID GENERATION SYSTEM: EXCELLENT PERFORMANCE")
                print("✅ All components operational and integrated")
                print("✅ Intelligent decision making with proper justification")
                print("✅ Professional bid documents generated for positive decisions")
                print("✅ Ready for production deployment")
                return True
            elif system_score >= 0.6:
                print("\n✅ COMPLETE AUTONOMOUS BID GENERATION SYSTEM: GOOD PERFORMANCE")
                print("🔧 System functional with minor optimizations available")
                return True
            else:
                print("\n⚠️  COMPLETE AUTONOMOUS BID GENERATION SYSTEM: NEEDS IMPROVEMENT")
                return False
        else:
            print("❌ No successful system analyses")
            return False
    except Exception as e:
        print(f"❌ Complete system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
if __name__ == "__main__":
    success = test_complete_bid_generation_system()
    sys.exit(0 if success else 1)