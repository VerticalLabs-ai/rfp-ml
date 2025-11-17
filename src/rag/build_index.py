"""
Build FAISS index from all processed RFP datasets
Comprehensive indexing script for the RAG system
"""
import sys
import os
import time
import json
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from rag.rag_engine import RAGEngine, RAGConfig
from config.paths import PathConfig
def build_comprehensive_index(force_rebuild: bool = False) -> Dict[str, Any]:
    """
    Build comprehensive FAISS index from all RFP datasets
    Args:
        force_rebuild: Whether to rebuild even if index exists
    Returns:
        Build statistics and validation results
    """
    print("🏗️ BUILDING COMPREHENSIVE RAG INDEX")
    print("=" * 60)
    # Configure RAG engine for optimal performance
    config = RAGConfig(
        embedding_model="all-MiniLM-L6-v2",  # Fast and effective
        chunk_size=512,
        chunk_overlap=50,
        top_k=10,
        batch_size=32,
        similarity_threshold=0.3
    )
    # Create RAG engine
    print("\n1️⃣ Initializing RAG Engine...")
    rag_engine = RAGEngine(config)
    print(f"   ✓ Embedding model: {config.embedding_model}")
    print(f"   ✓ Chunk size: {config.chunk_size} tokens")
    print(f"   ✓ Chunk overlap: {config.chunk_overlap} tokens")
    print(f"   ✓ Batch size: {config.batch_size}")
    # Check if index already exists
    if not force_rebuild and rag_engine._index_exists():
        print("\n⚠️  Index already exists. Use force_rebuild=True to rebuild.")
        print("   Loading existing index...")
        try:
            load_stats = rag_engine.load_index()
            print(f"   ✓ Loaded index with {load_stats['total_chunks']} chunks")
            return {"status": "loaded_existing", **load_stats}
        except Exception as e:
            print(f"   ❌ Failed to load existing index: {e}")
            print("   Proceeding with rebuild...")
            force_rebuild = True
    # Build index
    print("\n2️⃣ Building FAISS Index...")
    print("   This may take several minutes depending on dataset size...")
    try:
        start_time = time.time()
        build_stats = rag_engine.build_index(force_rebuild=True)
        total_time = time.time() - start_time
        print(f"\n   ✅ Index build completed!")
        print(f"   📊 Build Statistics:")
        print(f"      • Total documents: {build_stats['total_documents']:,}")
        print(f"      • Total chunks: {build_stats['total_chunks']:,}")
        print(f"      • Embedding dimension: {build_stats['embedding_dimension']}")
        print(f"      • Index type: {build_stats['index_type']}")
        print(f"      • Build time: {build_stats['build_time_seconds']:.2f}s")
        print(f"      • Processing rate: {build_stats['chunks_per_second']:.1f} chunks/second")
        # Validate index
        print("\n3️⃣ Validating Index...")
        validation_results = rag_engine.validate_index()
        print(f"   Index integrity: {'✅' if validation_results['index_integrity'] else '❌'}")
        print(f"   Embedding consistency: {'✅' if validation_results['embedding_consistency'] else '❌'}")
        if 'search_performance' in validation_results:
            perf = validation_results['search_performance']
            print(f"   Search performance:")
            print(f"      • Average search time: {perf['avg_search_time']:.3f}s")
            print(f"      • Max search time: {perf['max_search_time']:.3f}s")
            print(f"      • Test queries: {perf['total_test_queries']}")
        print(f"   Overall health: {validation_results['overall_health'].upper()}")
        # Get detailed index statistics
        print("\n4️⃣ Index Statistics...")
        index_stats = rag_engine.get_index_stats()
        print(f"   📊 Index Overview:")
        print(f"      • Total chunks: {index_stats['total_chunks']:,}")
        print(f"      • Index size: {index_stats['index_size']:,} vectors")
        print(f"      • Embedding dimension: {index_stats['embedding_dimension']}")
        if 'source_distribution' in index_stats:
            print(f"   📁 Source Distribution:")
            for source, count in index_stats['source_distribution'].items():
                print(f"      • {source}: {count:,} chunks")
        # Test sample searches
        print("\n5️⃣ Testing Sample Searches...")
        test_queries = [
            "bottled water delivery service requirements",
            "construction project bid specifications", 
            "logistics and transportation services",
            "government contract compliance standards",
            "emergency response capabilities"
        ]
        search_results = {}
        for query in test_queries:
            try:
                results = rag_engine.search(query, k=3)
                search_results[query] = {
                    "num_results": len(results),
                    "top_score": results[0]["score"] if results else 0.0,
                    "avg_score": sum(r["score"] for r in results) / len(results) if results else 0.0
                }
                print(f"   ✓ '{query[:30]}...': {len(results)} results (top score: {results[0]['score']:.3f})" if results else f"   ⚠️ '{query[:30]}...': No results")
            except Exception as e:
                print(f"   ❌ '{query[:30]}...': Search failed - {e}")
                search_results[query] = {"error": str(e)}
        # Compile final results
        final_results = {
            "status": "success",
            "build_stats": build_stats,
            "validation_results": validation_results,
            "index_stats": index_stats,
            "search_test_results": search_results,
            "total_build_time": total_time
        }
        # Save results to file
        logs_dir = PathConfig.PROJECT_ROOT / "logs"
        logs_dir.mkdir(exist_ok=True)
        results_path = logs_dir / "rag_build_results.json"
        with open(results_path, 'w') as f:
            json.dump(final_results, f, indent=2)
        print(f"\n📄 Results saved to: {results_path}")
        print("\n" + "=" * 60)
        print("🎉 RAG INDEX BUILD COMPLETED SUCCESSFULLY!")
        print("✅ FAISS index is ready for semantic search")
        print("✅ System validated and tested")
        print("🚀 Ready for RAG-enhanced bid generation")
        print("=" * 60)
        return final_results
    except Exception as e:
        error_results = {
            "status": "error",
            "error": str(e),
            "build_time": time.time() - start_time if 'start_time' in locals() else 0
        }
        print(f"\n❌ Index build failed: {e}")
        return error_results
def main():
    """Main function for building the index"""
    import argparse
    parser = argparse.ArgumentParser(description="Build FAISS index for RAG system")
    parser.add_argument("--force-rebuild", action="store_true", 
                       help="Force rebuild even if index exists")
    args = parser.parse_args()
    # Build index
    results = build_comprehensive_index(force_rebuild=args.force_rebuild)
    # Exit with appropriate code
    if results["status"] == "success":
        exit(0)
    else:
        exit(1)
if __name__ == "__main__":
    main()