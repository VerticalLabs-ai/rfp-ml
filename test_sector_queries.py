#!/usr/bin/env python3
"""
Test RAG system with sector-specific queries.
"""
import os
import sys
import pickle
import time
import json
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
def load_rag_system():
    """Load the RAG system components."""
    embeddings_dir = "/app/government_rfp_bid_1927/data/embeddings"
    # Load model
    model = SentenceTransformer("all-MiniLM-L6-v2")
    # Load FAISS index
    index_path = os.path.join(embeddings_dir, "faiss_index.bin")
    index = faiss.read_index(index_path)
    # Load documents and metadata
    with open(os.path.join(embeddings_dir, "documents.pkl"), 'rb') as f:
        documents = pickle.load(f)
    with open(os.path.join(embeddings_dir, "metadata.pkl"), 'rb') as f:
        metadata = pickle.load(f)
    return model, index, documents, metadata
def retrieve_documents(model, index, documents, metadata, query, k=5):
    """Retrieve top-k documents for a query."""
    # Generate query embedding
    query_embedding = model.encode([query])
    faiss.normalize_L2(query_embedding)
    # Search
    scores, indices = index.search(query_embedding.astype(np.float32), k)
    # Prepare results
    results = []
    for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
        if idx < len(documents):
            result = {
                'rank': i + 1,
                'score': float(score),
                'text': documents[idx],
                'metadata': metadata[idx]
            }
            results.append(result)
    return results
def test_sector_performance():
    """Test performance for each RFP sector."""
    print("Loading RAG system...")
    model, index, documents, metadata = load_rag_system()
    # Test queries by sector
    sector_tests = {
        'bottled_water': [
            "bottled water supply for government offices",
            "drinking water delivery services",
            "water dispensing and bottle replacement"
        ],
        'construction': [
            "building construction and renovation",
            "infrastructure development projects", 
            "facility construction management"
        ],
        'delivery': [
            "logistics and transportation services",
            "freight delivery for government",
            "courier and shipping services"
        ]
    }
    print(f"\n{'='*80}")
    print("SECTOR-SPECIFIC QUERY TESTING")
    print(f"{'='*80}")
    print(f"Total documents in index: {index.ntotal:,}")
    print(f"Embedding dimension: {model.get_sentence_embedding_dimension()}")
    overall_results = {}
    for sector, queries in sector_tests.items():
        print(f"\n{'-'*60}")
        print(f"TESTING {sector.upper()} SECTOR")
        print(f"{'-'*60}")
        sector_stats = {
            'queries_tested': len(queries),
            'retrieval_times': [],
            'relevance_scores': [],
            'category_matches': 0
        }
        for i, query in enumerate(queries, 1):
            print(f"\nQuery {i}: {query}")
            # Measure retrieval time
            start_time = time.time()
            results = retrieve_documents(model, index, documents, metadata, query, k=3)
            retrieval_time = time.time() - start_time
            sector_stats['retrieval_times'].append(retrieval_time)
            print(f"Retrieval time: {retrieval_time:.3f}s")
            if results:
                # Calculate relevance score
                avg_score = sum(r['score'] for r in results) / len(results)
                sector_stats['relevance_scores'].append(avg_score)
                # Check if top result matches expected category
                top_result = results[0]
                if top_result['metadata']['category'] == sector:
                    sector_stats['category_matches'] += 1
                print(f"Average relevance score: {avg_score:.3f}")
                print("Top 3 results:")
                for result in results:
                    print(f"  Rank {result['rank']}: Score {result['score']:.3f}")
                    print(f"    Category: {result['metadata']['category']}")
                    print(f"    Title: {result['metadata']['title'][:80]}...")
                    print(f"    Agency: {result['metadata']['agency']}")
                    print()
        # Calculate sector performance metrics
        avg_retrieval_time = sum(sector_stats['retrieval_times']) / len(sector_stats['retrieval_times'])
        avg_relevance = sum(sector_stats['relevance_scores']) / len(sector_stats['relevance_scores']) if sector_stats['relevance_scores'] else 0
        category_match_rate = sector_stats['category_matches'] / len(queries)
        sector_performance = {
            'average_retrieval_time': avg_retrieval_time,
            'average_relevance_score': avg_relevance,
            'category_match_rate': category_match_rate,
            'queries_tested': len(queries)
        }
        overall_results[sector] = sector_performance
        print(f"\nSECTOR PERFORMANCE SUMMARY:")
        print(f"  Average retrieval time: {avg_retrieval_time:.3f}s")
        print(f"  Average relevance score: {avg_relevance:.3f}")
        print(f"  Category match rate: {category_match_rate:.1%}")
    # Overall assessment
    print(f"\n{'='*80}")
    print("OVERALL PERFORMANCE ASSESSMENT")
    print(f"{'='*80}")
    total_queries = sum(r['queries_tested'] for r in overall_results.values())
    avg_retrieval_time = sum(r['average_retrieval_time'] for r in overall_results.values()) / len(overall_results)
    avg_relevance = sum(r['average_relevance_score'] for r in overall_results.values()) / len(overall_results)
    avg_category_match = sum(r['category_match_rate'] for r in overall_results.values()) / len(overall_results)
    print(f"Total queries tested: {total_queries}")
    print(f"Overall average retrieval time: {avg_retrieval_time:.3f}s")
    print(f"Overall average relevance score: {avg_relevance:.3f}")
    print(f"Overall category match rate: {avg_category_match:.1%}")
    # Performance criteria
    performance_criteria = {
        'fast_retrieval': avg_retrieval_time < 0.5,  # Sub 500ms
        'good_relevance': avg_relevance > 0.3,      # Reasonable similarity scores
        'category_accuracy': avg_category_match > 0.5,  # >50% category matches
        'system_responsive': all(r['average_retrieval_time'] < 1.0 for r in overall_results.values())
    }
    print(f"\nPERFORMANCE VALIDATION:")
    passed_criteria = 0
    for criterion, passed in performance_criteria.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {criterion}: {status}")
        if passed:
            passed_criteria += 1
    success_rate = passed_criteria / len(performance_criteria)
    print(f"\nVALIDATION SCORE: {passed_criteria}/{len(performance_criteria)} ({success_rate:.1%})")
    if success_rate >= 0.75:
        print("🎉 RAG SYSTEM VALIDATION: EXCELLENT PERFORMANCE")
        return True
    elif success_rate >= 0.5:
        print("✅ RAG SYSTEM VALIDATION: ACCEPTABLE PERFORMANCE") 
        return True
    else:
        print("❌ RAG SYSTEM VALIDATION: NEEDS IMPROVEMENT")
        return False
if __name__ == "__main__":
    success = test_sector_performance()
    sys.exit(0 if success else 1)