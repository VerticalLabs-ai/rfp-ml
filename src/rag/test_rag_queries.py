#!/usr/bin/env python3
"""
Quick test script to demonstrate RAG functionality with sample queries.
"""
import json

from src.rag.rag_engine import RAGEngine
def test_rag_queries():
    """Test RAG with specific queries for each sector."""
    print("Initializing RAG Engine...")
    rag = RAGEngine()
    # Load the index
    if not rag.load_artifacts():
        print("Failed to load RAG artifacts. Please run the main RAG engine first.")
        return
    # Test queries for each sector
    test_cases = [
        {
            "sector": "Bottled Water",
            "query": "bottled water supply and delivery for federal agencies",
            "expected_keywords": ["water", "bottle", "supply", "delivery"]
        },
        {
            "sector": "Construction", 
            "query": "building renovation and construction management services",
            "expected_keywords": ["construction", "building", "renovation", "management"]
        },
        {
            "sector": "Delivery/Logistics",
            "query": "transportation and logistics services for government supplies",
            "expected_keywords": ["transportation", "logistics", "delivery", "freight"]
        }
    ]
    print("\n" + "="*80)
    print("RAG QUERY TESTING RESULTS")
    print("="*80)
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['sector']}")
        print(f"Query: {test_case['query']}")
        print("-" * 60)
        # Retrieve relevant documents
        results = rag.retrieve(test_case['query'], k=3)
        if not results:
            print("No results found!")
            continue
        for j, result in enumerate(results, 1):
            print(f"\nResult {j} (Score: {result['score']:.3f}):")
            print(f"Category: {result['metadata']['category']}")
            print(f"Title: {result['metadata']['title']}")
            print(f"Source: {result['metadata']['source_file']}")
            print(f"Contract Value: ${result['metadata'].get('total_contract_value', 'N/A')}")
            print(f"Text Preview: {result['text'][:200]}...")
    # Overall system statistics
    stats = rag.get_stats()
    print(f"\n" + "="*80)
    print("SYSTEM STATISTICS")
    print("="*80)
    print(f"Total Documents: {stats['total_documents']:,}")
    print(f"Index Size: {stats['index_size']:,}")
    print(f"Model: {stats['model_name']}")
    print(f"Embedding Dimension: {stats['embedding_dimension']}")
    print(f"\nCategory Distribution:")
    for category, count in stats['category_distribution'].items():
        percentage = (count / stats['total_documents']) * 100
        print(f"  {category}: {count:,} documents ({percentage:.1f}%)")
if __name__ == "__main__":
    test_rag_queries()