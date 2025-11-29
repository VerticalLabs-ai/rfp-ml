"""
RAG Engine Validation and Testing Script
"""
import json
import os
import sys

sys.path.append('/app/government_rfp_bid_1927')
def test_rag_engine():
    """Comprehensive test of RAG engine functionality"""
    print("🔍 RAG ENGINE COMPREHENSIVE TEST")
    print("=" * 50)
    try:
        from src.rag.rag_engine import create_rag_engine
        print("✅ RAG Engine import successful")
        # Create RAG engine
        rag_engine = create_rag_engine()
        print("✅ RAG Engine created")
        # Get initial statistics
        initial_stats = rag_engine.get_statistics()
        print(f"📊 Initial stats: {initial_stats['is_built']}")
        # Build index
        print("\n🔨 Building RAG Index...")
        rag_engine.build_index()
        print("✅ RAG Index built successfully")
        # Get post-build statistics
        stats = rag_engine.get_statistics()
        print("\n📊 RAG ENGINE STATISTICS:")
        print(f"   Built: {stats['is_built']}")
        print(f"   Total Documents: {stats['total_documents']}")
        print(f"   Embedding Model: {stats['embedding_model']}")
        print(f"   Embedding Available: {stats['embedding_available']}")
        print(f"   Vector Index: {stats['vector_index_built']}")
        print(f"   TF-IDF Available: {stats['tfidf_available']}")
        # Test retrieval with different queries
        test_queries = [
            "bottled water delivery contract",
            "construction services government",
            "delivery services federal agencies",
            "water supply requirements",
            "contract award amount"
        ]
        print("\n🔍 TESTING RETRIEVAL:")
        retrieval_results = {}
        for query in test_queries:
            try:
                context = rag_engine.generate_context(query, k=3)
                retrieval_results[query] = {
                    "total_retrieved": context.total_retrieved,
                    "retrieval_method": context.retrieval_method,
                    "has_context": len(context.context_text) > 0,
                    "sample_docs": [doc.document_id for doc in context.retrieved_documents[:2]]
                }
                print(f"   '{query}': {context.total_retrieved} docs ({context.retrieval_method})")
                # Show sample retrieved content
                if context.retrieved_documents:
                    sample_doc = context.retrieved_documents[0]
                    print(f"      Sample: {sample_doc.content[:100]}... (score: {sample_doc.similarity_score:.3f})")
            except Exception as e:
                print(f"   '{query}': FAILED - {str(e)}")
                retrieval_results[query] = {"error": str(e)}
        # Test integration with LLM
        print("\n🤖 TESTING RAG + LLM INTEGRATION:")
        try:
            from src.config.llm_adapter import create_llm_interface
            llm_interface = create_llm_interface()
            # Test RAG-enhanced generation
            query = "Generate a bid for bottled water delivery to government agencies"
            context = rag_engine.generate_context(query)
            # Create enhanced prompt with retrieved context
            enhanced_prompt = f"""Query: {query}
Retrieved Context:
{context.context_text[:500]}...
Based on the above context, generate a professional bid response:"""
            result = llm_interface.generate_text(enhanced_prompt, use_case="bid_generation")
            print("   ✅ RAG + LLM Integration: SUCCESS")
            print(f"   Backend: {result['backend']}")
            print(f"   Context Length: {len(context.context_text)} chars")
            print(f"   Generated: {result['text'][:100]}...")
            integration_success = True
        except Exception as e:
            print(f"   ❌ RAG + LLM Integration: FAILED - {str(e)}")
            integration_success = False
        # Generate test report
        test_report = {
            "timestamp": str(os.popen('date').read().strip()),
            "rag_statistics": stats,
            "retrieval_tests": retrieval_results,
            "integration_success": integration_success,
            "total_queries_tested": len(test_queries),
            "successful_retrievals": sum(1 for r in retrieval_results.values() if "error" not in r),
            "average_docs_retrieved": sum(r.get("total_retrieved", 0) for r in retrieval_results.values() if "error" not in r) / len([r for r in retrieval_results.values() if "error" not in r]) if retrieval_results else 0
        }
        # Save test report
        os.makedirs('/app/government_rfp_bid_1927/logs', exist_ok=True)
        with open('/app/government_rfp_bid_1927/logs/rag_engine_test_report.json', 'w') as f:
            json.dump(test_report, f, indent=2)
        print("\n" + "=" * 50)
        print("✅ RAG ENGINE TEST SUMMARY")
        print("=" * 50)
        print(f"✅ Index Built: {stats['is_built']}")
        print(f"✅ Documents Indexed: {stats['total_documents']}")
        print(f"✅ Embedding System: {stats['embedding_available']}")
        print(f"✅ Retrieval Working: {test_report['successful_retrievals']}/{test_report['total_queries_tested']} queries")
        print(f"✅ LLM Integration: {integration_success}")
        print(f"✅ Average Retrieved: {test_report['average_docs_retrieved']:.1f} docs/query")
        print("\n📄 Test report saved: logs/rag_engine_test_report.json")
        return True
    except Exception as e:
        print(f"❌ RAG Engine test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
if __name__ == "__main__":
    success = test_rag_engine()
    if success:
        print("\n🎉 RAG ENGINE: OPERATIONAL AND READY")
        print("🔄 Ready for integration with bid generation pipeline")
    else:
        print("\n❌ RAG ENGINE: Issues detected")
