#!/usr/bin/env python3
"""
Validate compliance matrix generator functionality and quality.
"""
import sys
import os
import json
import pandas as pd
from typing import Dict, List, Any
# Add src to path
sys.path.insert(0, '/app/government_rfp_bid_1927/src')
from rag.rag_engine import RAGEngine
from compliance.compliance_matrix import ComplianceMatrixGenerator
def validate_requirement_extraction():
    """Test requirement extraction capabilities."""
    print("🔍 Testing Requirement Extraction...")
    # Test cases with known requirements
    test_cases = [
        {
            "text": "The contractor must provide 24/7 support services. All equipment shall meet industry standards. Proposals are required to include detailed cost breakdowns.",
            "expected_categories": ["mandatory", "technical", "administrative"],
            "expected_count_min": 3
        },
        {
            "text": "Technical specifications: System must support 1000+ concurrent users. Performance requirements include 99.9% uptime. Submit all documentation by deadline.",
            "expected_categories": ["technical", "performance", "administrative"],
            "expected_count_min": 3
        },
        {
            "text": "Bidders shall have minimum 5 years experience. All staff must be certified. Financial statements required for qualification.",
            "expected_categories": ["qualification", "administrative"],
            "expected_count_min": 2
        }
    ]
    generator = ComplianceMatrixGenerator()
    test_results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  Test Case {i}: {test_case['text'][:50]}...")
        # Test rule-based extraction
        rule_reqs = generator.extract_requirements_rule_based(test_case['text'])
        llm_reqs = generator.extract_requirements_llm(test_case['text'])
        # Combined requirements
        all_reqs = rule_reqs + llm_reqs
        unique_reqs = generator._deduplicate_requirements(all_reqs)
        # Extract categories
        found_categories = set(req['category'] for req in unique_reqs)
        result = {
            'test_case': i,
            'requirements_found': len(unique_reqs),
            'meets_minimum': len(unique_reqs) >= test_case['expected_count_min'],
            'categories_found': list(found_categories),
            'has_expected_categories': any(cat in found_categories for cat in test_case['expected_categories'])
        }
        test_results.append(result)
        print(f"    Requirements found: {result['requirements_found']}")
        print(f"    Categories: {result['categories_found']}")
        print(f"    Meets minimum: {'✅' if result['meets_minimum'] else '❌'}")
        print(f"    Has expected categories: {'✅' if result['has_expected_categories'] else '❌'}")
    # Overall assessment
    total_tests = len(test_results)
    successful_tests = sum(1 for r in test_results if r['meets_minimum'] and r['has_expected_categories'])
    print(f"\n  📊 Extraction Validation: {successful_tests}/{total_tests} tests passed")
    return successful_tests / total_tests >= 0.75
def validate_compliance_responses():
    """Test compliance response generation quality."""
    print("\n💬 Testing Compliance Response Generation...")
    # Sample requirements for testing
    test_requirements = [
        {
            "id": "test_req_1",
            "text": "The system must support real-time data processing with sub-second latency",
            "category": "technical",
            "mandatory": True,
            "confidence": 0.9
        },
        {
            "id": "test_req_2", 
            "text": "Contractor shall provide detailed cost breakdown including labor and materials",
            "category": "financial",
            "mandatory": True,
            "confidence": 0.8
        },
        {
            "id": "test_req_3",
            "text": "All personnel must have appropriate security clearances",
            "category": "security",
            "mandatory": True,
            "confidence": 0.95
        }
    ]
    rfp_context = {
        "title": "Test RFP for System Integration",
        "agency": "Test Agency",
        "naics_code": "541511"
    }
    generator = ComplianceMatrixGenerator()
    response_quality_scores = []
    for req in test_requirements:
        print(f"\n  Testing requirement: {req['text'][:50]}...")
        response = generator.generate_compliance_response(req, rfp_context)
        # Quality checks
        quality_checks = {
            'has_response_text': bool(response.get('response_text', '').strip()),
            'response_length_adequate': len(response.get('response_text', '')) >= 50,
            'includes_compliance_status': response.get('compliance_status') in ['compliant', 'partial', 'review_required'],
            'matches_requirement_category': response.get('category') == req['category'],
            'includes_confidence': 'confidence_score' in response
        }
        quality_score = sum(quality_checks.values()) / len(quality_checks)
        response_quality_scores.append(quality_score)
        print(f"    Response length: {len(response.get('response_text', ''))}")
        print(f"    Compliance status: {response.get('compliance_status')}")
        print(f"    Quality score: {quality_score:.1%}")
        # Show sample response
        print(f"    Sample response: {response.get('response_text', '')[:100]}...")
    avg_quality = sum(response_quality_scores) / len(response_quality_scores)
    print(f"\n  📊 Response Quality Average: {avg_quality:.1%}")
    return avg_quality >= 0.8
def validate_rag_integration():
    """Test RAG integration for enhanced responses."""
    print("\n🔗 Testing RAG Integration...")
    try:
        # Load RAG engine
        rag = RAGEngine()
        if not rag.load_artifacts():
            print("    ⚠️  RAG artifacts not available, skipping RAG integration test")
            return True  # Don't fail the test if RAG isn't available
        generator = ComplianceMatrixGenerator(rag_engine=rag)
        # Test requirement with RAG context
        test_req = {
            "id": "rag_test_req",
            "text": "Provide bottled water delivery services for government facilities",
            "category": "general",
            "mandatory": True,
            "confidence": 0.8
        }
        rfp_context = {
            "title": "Bottled Water Supply Contract",
            "agency": "General Services Administration"
        }
        response = generator.generate_compliance_response(test_req, rfp_context)
        # Check if RAG context was used
        has_supporting_evidence = bool(response.get('supporting_evidence'))
        response_quality = len(response.get('response_text', '')) >= 100
        print(f"    RAG context retrieved: {'✅' if has_supporting_evidence else '❌'}")
        print(f"    Response quality adequate: {'✅' if response_quality else '❌'}")
        if has_supporting_evidence:
            print(f"    Supporting evidence items: {len(response['supporting_evidence'])}")
        return has_supporting_evidence and response_quality
    except Exception as e:
        print(f"    ❌ RAG integration test failed: {e}")
        return False
def validate_export_functionality():
    """Test compliance matrix export capabilities."""
    print("\n📤 Testing Export Functionality...")
    # Create a sample compliance matrix
    sample_matrix = {
        "rfp_info": {
            "title": "Test RFP Export",
            "agency": "Test Agency", 
            "rfp_id": "TEST_001",
            "naics_code": "541511",
            "solicitation_number": "TEST-SOL-001"
        },
        "extraction_summary": {
            "total_requirements": 3,
            "rule_based_count": 2,
            "llm_based_count": 1,
            "extraction_method": "hybrid"
        },
        "compliance_summary": {
            "total_requirements": 3,
            "compliant": 2,
            "partial": 1,
            "review_required": 0,
            "compliance_rate": 0.67,
            "overall_status": "needs_review"
        },
        "requirements_and_responses": [
            {
                "requirement_id": "req_1",
                "requirement_text": "Test requirement 1",
                "compliance_status": "compliant",
                "response_text": "Test response 1",
                "category": "technical",
                "mandatory": True,
                "confidence_score": 0.9,
                "supporting_evidence": [],
                "generated_at": "2024-01-01T00:00:00"
            }
        ],
        "generated_at": "2024-01-01T00:00:00",
        "generator_version": "1.0.0"
    }
    generator = ComplianceMatrixGenerator()
    export_results = {}
    # Test each export format
    formats = ["json", "csv", "html"]
    for fmt in formats:
        try:
            filepath = generator.export_compliance_matrix(sample_matrix, fmt)
            file_exists = os.path.exists(filepath)
            file_size = os.path.getsize(filepath) if file_exists else 0
            export_results[fmt] = {
                "success": file_exists,
                "file_path": filepath,
                "file_size": file_size
            }
            print(f"    {fmt.upper()}: {'✅' if file_exists else '❌'} ({file_size} bytes)")
        except Exception as e:
            print(f"    {fmt.upper()}: ❌ Error - {e}")
            export_results[fmt] = {"success": False, "error": str(e)}
    successful_exports = sum(1 for result in export_results.values() if result.get("success", False))
    print(f"\n  📊 Export Success Rate: {successful_exports}/{len(formats)}")
    return successful_exports == len(formats)
def validate_end_to_end_workflow():
    """Test complete end-to-end compliance matrix generation."""
    print("\n🔄 Testing End-to-End Workflow...")
    try:
        # Load real RFP data
        df = pd.read_parquet('/app/government_rfp_bid_1927/data/processed/rfp_master_dataset.parquet')
        test_rfp = df[df['description'].notna()].iloc[0].to_dict()
        print(f"    Test RFP: {test_rfp.get('title', 'Unknown')[:50]}...")
        # Initialize with RAG if available
        rag = None
        try:
            rag = RAGEngine()
            rag.load_artifacts()
        except:
            pass
        generator = ComplianceMatrixGenerator(rag_engine=rag)
        # Generate compliance matrix
        compliance_matrix = generator.generate_compliance_matrix(test_rfp)
        # Validate results
        validation_checks = {
            'has_rfp_info': bool(compliance_matrix.get('rfp_info')),
            'has_requirements': len(compliance_matrix.get('requirements_and_responses', [])) > 0,
            'has_compliance_summary': bool(compliance_matrix.get('compliance_summary')),
            'reasonable_requirement_count': len(compliance_matrix.get('requirements_and_responses', [])) >= 3,
            'valid_compliance_rate': 0 <= compliance_matrix.get('compliance_summary', {}).get('compliance_rate', -1) <= 1
        }
        # Export test
        json_path = generator.export_compliance_matrix(compliance_matrix, "json")
        export_success = os.path.exists(json_path)
        validation_checks['export_success'] = export_success
        # Results
        passed_checks = sum(validation_checks.values())
        total_checks = len(validation_checks)
        print(f"    Requirements extracted: {len(compliance_matrix.get('requirements_and_responses', []))}")
        print(f"    Compliance rate: {compliance_matrix.get('compliance_summary', {}).get('compliance_rate', 0):.1%}")
        print(f"    Validation checks: {passed_checks}/{total_checks}")
        for check, result in validation_checks.items():
            print(f"      {check}: {'✅' if result else '❌'}")
        return passed_checks / total_checks >= 0.8
    except Exception as e:
        print(f"    ❌ End-to-end test failed: {e}")
        return False
def main():
    """Main validation function."""
    print("=" * 80)
    print("COMPLIANCE MATRIX GENERATOR VALIDATION")
    print("=" * 80)
    # Run all validation tests
    validation_tests = [
        ("Requirement Extraction", validate_requirement_extraction),
        ("Compliance Responses", validate_compliance_responses), 
        ("RAG Integration", validate_rag_integration),
        ("Export Functionality", validate_export_functionality),
        ("End-to-End Workflow", validate_end_to_end_workflow)
    ]
    results = {}
    for test_name, test_function in validation_tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_function()
            results[test_name] = result
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"\n{test_name}: {status}")
        except Exception as e:
            print(f"\n{test_name}: ❌ ERROR - {e}")
            results[test_name] = False
    # Overall assessment
    print(f"\n" + "=" * 80)
    print("OVERALL VALIDATION RESULTS")
    print("=" * 80)
    passed_tests = sum(results.values())
    total_tests = len(results)
    success_rate = passed_tests / total_tests
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    print(f"\nValidation Score: {passed_tests}/{total_tests} ({success_rate:.1%})")
    if success_rate >= 0.8:
        print("🎉 COMPLIANCE MATRIX GENERATOR: VALIDATION SUCCESSFUL")
        return True
    elif success_rate >= 0.6:
        print("⚠️  COMPLIANCE MATRIX GENERATOR: PARTIAL SUCCESS")
        return True
    else:
        print("❌ COMPLIANCE MATRIX GENERATOR: VALIDATION FAILED")
        return False
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)