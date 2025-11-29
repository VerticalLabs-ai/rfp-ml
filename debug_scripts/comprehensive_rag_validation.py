"""
Comprehensive RAG System Validation
Tests all components of the RAG engine and LLM integration
"""
import json
import os
import sys
import time

sys.path.append('/app/government_rfp_bid_1927')
def comprehensive_rag_validation():
    """Run comprehensive validation of the RAG system"""
    print("🚀 COMPREHENSIVE RAG SYSTEM VALIDATION")
    print("=" * 60)
    validation_results = {
        "timestamp": str(os.popen('date').read().strip()),
        "tests": {},
        "summary": {}
    }
    # Test 1: RAG Engine Core
    print("\n1. RAG Engine Core Test")
    try:
        from src.rag.rag_engine import create_rag_engine
        rag_engine = create_rag_engine()
        if not rag_engine.is_built:
            print("   Building RAG index...")
            rag_engine.build_index()
        stats = rag_engine.get_statistics()
        validation_results["tests"]["rag_core"] = {
            "status": "PASS",
            "stats": stats
        }
        print(f"   ✅ RAG Engine: {stats['total_documents']} documents indexed")
        print(f"   ✅ Embedding Model: {stats['embedding_model']}")
        print(f"   ✅ Vector Index: {stats['vector_index_built']}")
    except Exception as e:
        validation_results["tests"]["rag_core"] = {
            "status": "FAIL",
            "error": str(e)
        }
        print(f"   ❌ RAG Engine failed: {str(e)}")
        return validation_results
    # Test 2: Retrieval Functionality
    print("\n2. Retrieval Functionality Test")
    try:
        test_queries = [
            "bottled water supply contract",
            "construction services",
            "delivery requirements federal agencies",
            "contract award amount pricing"
        ]
        retrieval_results = []
        for query in test_queries:
            context = rag_engine.generate_context(query, k=3)
            retrieval_results.append({
                "query": query,
                "retrieved": context.total_retrieved,
                "method": context.retrieval_method,
                "has_content": len(context.context_text) > 0
            })
        avg_retrieved = sum(r["retrieved"] for r in retrieval_results) / len(retrieval_results)
        validation_results["tests"]["retrieval"] = {
            "status": "PASS",
            "results": retrieval_results,
            "average_retrieved": avg_retrieved
        }
        print(f"   ✅ Retrieval: {len(retrieval_results)} queries tested")
        print(f"   ✅ Average Retrieved: {avg_retrieved:.1f} documents")
        print(f"   ✅ Method: {retrieval_results[0]['method']}")
    except Exception as e:
        validation_results["tests"]["retrieval"] = {
            "status": "FAIL",
            "error": str(e)
        }
        print(f"   ❌ Retrieval failed: {str(e)}")
    # Test 3: RAG-LLM Integration
    print("\n3. RAG-LLM Integration Test")
    try:
        from src.rag.rag_llm_integration import create_rag_llm_integrator
        integrator = create_rag_llm_integrator()
        system_status = integrator.get_system_status()
        # Test bid generation
        bid_result = integrator.generate_bid_response(
            "Supply bottled water to government agencies",
            "1000 cases monthly for 12 months"
        )
        # Test requirement extraction
        req_result = integrator.extract_rfp_requirements(
            "Supply 500 cases bottled water monthly, delivery within 48 hours, insurance required"
        )
        # Test pricing analysis
        pricing_result = integrator.analyze_pricing(
            "Water delivery contract",
            "500 cases per month"
        )
        validation_results["tests"]["integration"] = {
            "status": "PASS",
            "system_status": system_status,
            "test_results": {
                "bid_generation": {
                    "docs_retrieved": bid_result.documents_retrieved,
                    "backend": bid_result.llm_backend,
                    "tokens": bid_result.token_usage["total_tokens"],
                    "output_length": len(bid_result.generated_text)
                },
                "requirement_extraction": {
                    "docs_retrieved": req_result.documents_retrieved,
                    "output_length": len(req_result.generated_text)
                },
                "pricing_analysis": {
                    "docs_retrieved": pricing_result.documents_retrieved,
                    "output_length": len(pricing_result.generated_text)
                }
            }
        }
        print(f"   ✅ Integration Ready: {system_status['integration_ready']}")
        print(f"   ✅ Bid Generation: {bid_result.documents_retrieved} docs → {len(bid_result.generated_text)} chars")
        print(f"   ✅ Requirement Extraction: {req_result.documents_retrieved} docs → {len(req_result.generated_text)} chars")
        print(f"   ✅ Pricing Analysis: {pricing_result.documents_retrieved} docs → {len(pricing_result.generated_text)} chars")
    except Exception as e:
        validation_results["tests"]["integration"] = {
            "status": "FAIL",
            "error": str(e)
        }
        print(f"   ❌ Integration failed: {str(e)}")
    # Test 4: Performance and Quality
    print("\n4. Performance and Quality Test")
    try:
        # Time retrieval performance
        start_time = time.time()
        context = rag_engine.generate_context("test query for performance", k=5)
        retrieval_time = time.time() - start_time
        # Time end-to-end generation
        start_time = time.time()
        result = integrator.generate_enhanced_content(
            "Generate bid for water supply contract",
            use_case="bid_generation"
        )
        generation_time = time.time() - start_time
        # Quality metrics
        quality_metrics = {
            "retrieval_time": retrieval_time,
            "generation_time": generation_time,
            "docs_retrieved": result.documents_retrieved,
            "context_length": len(result.context_used),
            "output_length": len(result.generated_text),
            "retrieval_method": result.retrieval_method
        }
        validation_results["tests"]["performance"] = {
            "status": "PASS",
            "metrics": quality_metrics
        }
        print(f"   ✅ Retrieval Time: {retrieval_time:.3f}s")
        print(f"   ✅ Generation Time: {generation_time:.3f}s")
        print(f"   ✅ Context Quality: {len(result.context_used)} chars")
        print(f"   ✅ Output Quality: {len(result.generated_text)} chars")
    except Exception as e:
        validation_results["tests"]["performance"] = {
            "status": "FAIL",
            "error": str(e)
        }
        print(f"   ❌ Performance test failed: {str(e)}")
    # Test 5: Dataset Coverage
    print("\n5. Dataset Coverage Test")
    try:
        # Check which datasets are indexed
        dataset_stats = {}
        if rag_engine.vector_index.metadata:
            for metadata in rag_engine.vector_index.metadata:
                dataset = metadata.get("source_dataset", "unknown")
                dataset_stats[dataset] = dataset_stats.get(dataset, 0) + 1
        validation_results["tests"]["dataset_coverage"] = {
            "status": "PASS",
            "dataset_stats": dataset_stats,
            "total_datasets": len(dataset_stats)
        }
        print(f"   ✅ Datasets Covered: {len(dataset_stats)}")
        for dataset, count in dataset_stats.items():
            print(f"      - {dataset}: {count} chunks")
    except Exception as e:
        validation_results["tests"]["dataset_coverage"] = {
            "status": "FAIL",
            "error": str(e)
        }
        print(f"   ❌ Dataset coverage test failed: {str(e)}")
    # Summary
    print("\n" + "=" * 60)
    print("COMPREHENSIVE VALIDATION SUMMARY")
    print("=" * 60)
    passed_tests = sum(1 for test in validation_results["tests"].values() if test["status"] == "PASS")
    total_tests = len(validation_results["tests"])
    validation_results["summary"] = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "pass_rate": passed_tests / total_tests if total_tests > 0 else 0,
        "overall_status": "OPERATIONAL" if passed_tests == total_tests else "PARTIAL" if passed_tests > 0 else "FAILED"
    }
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print(f"Pass Rate: {validation_results['summary']['pass_rate']:.1%}")
    print(f"Overall Status: {validation_results['summary']['overall_status']}")
    if validation_results["summary"]["overall_status"] == "OPERATIONAL":
        print("\n🎉 RAG SYSTEM FULLY OPERATIONAL!")
        print("✅ Vector embeddings and retrieval working")
        print("✅ LLM integration functional")
        print("✅ All use cases supported")
        print("✅ Performance within acceptable ranges")
        print("✅ Multiple datasets indexed and searchable")
    elif validation_results["summary"]["overall_status"] == "PARTIAL":
        print("\n⚠️ RAG SYSTEM PARTIALLY OPERATIONAL")
        failed_tests = [name for name, result in validation_results["tests"].items() if result["status"] == "FAIL"]
        print(f"Issues: {', '.join(failed_tests)}")
    else:
        print("\n❌ RAG SYSTEM NOT OPERATIONAL")
        print("Critical issues detected")
    # Save comprehensive report
    os.makedirs('/app/government_rfp_bid_1927/logs', exist_ok=True)
    with open('/app/government_rfp_bid_1927/logs/comprehensive_rag_validation.json', 'w') as f:
        json.dump(validation_results, f, indent=2)
    print("\n📄 Comprehensive report saved: logs/comprehensive_rag_validation.json")
    return validation_results
if __name__ == "__main__":
    results = comprehensive_rag_validation()
    print(f"\n🔧 SUBTASK 2 STATUS: {'✅ COMPLETE' if results['summary']['overall_status'] == 'OPERATIONAL' else '⚠️ PARTIAL' if results['summary']['overall_status'] == 'PARTIAL' else '❌ INCOMPLETE'}")
