import sys
import os
import json
import pickle
import faiss
sys.path.append('/app/government_rfp_bid_1927/src')
def check_index_health():
    """Check the health and integrity of the RAG index"""
    print("=== RAG Index Health Check ===\n")
    index_path = "/app/government_rfp_bid_1927/data/embeddings/"
    # Check file existence
    required_files = [
        "faiss_index.bin",
        "metadata.json", 
        "embeddings.pkl",
        "index_info.json"
    ]
    print("1. File Existence Check:")
    all_files_exist = True
    for filename in required_files:
        filepath = os.path.join(index_path, filename)
        exists = os.path.exists(filepath)
        size = os.path.getsize(filepath) if exists else 0
        print(f"   {filename}: {'✓' if exists else '✗'} ({size:,} bytes)")
        if not exists:
            all_files_exist = False
    if not all_files_exist:
        print("\nERROR: Missing required index files!")
        return False
    # Load and validate index
    print("\n2. Index Validation:")
    try:
        # Load FAISS index
        index = faiss.read_index(os.path.join(index_path, "faiss_index.bin"))
        print(f"   FAISS index loaded: {index.ntotal:,} vectors")
        print(f"   Vector dimension: {index.d}")
        # Load metadata
        with open(os.path.join(index_path, "metadata.json"), 'r') as f:
            metadata = json.load(f)
        print(f"   Metadata entries: {len(metadata):,}")
        # Load embeddings
        with open(os.path.join(index_path, "embeddings.pkl"), 'rb') as f:
            embeddings = pickle.load(f)
        print(f"   Embeddings shape: {embeddings.shape}")
        # Load index info
        with open(os.path.join(index_path, "index_info.json"), 'r') as f:
            index_info = json.load(f)
        print(f"   Index built: {index_info['build_date']}")
        print(f"   Source documents: {index_info['num_documents']:,}")
        print(f"   Total chunks: {index_info['num_chunks']:,}")
        # Verify consistency
        print("\n3. Consistency Check:")
        consistent = True
        if index.ntotal != len(metadata):
            print(f"   ✗ Mismatch: FAISS vectors ({index.ntotal}) != metadata entries ({len(metadata)})")
            consistent = False
        else:
            print(f"   ✓ Vector count matches metadata entries")
        if embeddings.shape[0] != index.ntotal:
            print(f"   ✗ Mismatch: Embeddings ({embeddings.shape[0]}) != FAISS vectors ({index.ntotal})")
            consistent = False
        else:
            print(f"   ✓ Embeddings count matches FAISS vectors")
        if embeddings.shape[1] != index.d:
            print(f"   ✗ Mismatch: Embedding dim ({embeddings.shape[1]}) != FAISS dim ({index.d})")
            consistent = False
        else:
            print(f"   ✓ Embedding dimensions match")
        # Check metadata structure
        print("\n4. Metadata Structure Check:")
        if metadata:
            sample_meta = metadata[0]
            required_fields = ['document_id', 'chunk_id', 'category', 'chunk_text']
            for field in required_fields:
                if field in sample_meta:
                    print(f"   ✓ {field}: present")
                else:
                    print(f"   ✗ {field}: missing")
                    consistent = False
        # Category distribution
        print("\n5. Category Distribution:")
        categories = {}
        for meta in metadata:
            cat = meta.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
        for category, count in sorted(categories.items()):
            percentage = (count / len(metadata)) * 100
            print(f"   {category}: {count:,} chunks ({percentage:.1f}%)")
        # Performance test
        print("\n6. Performance Test:")
        import time
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        test_query = "bottled water delivery services"
        start_time = time.time()
        query_embedding = model.encode([test_query])
        faiss.normalize_L2(query_embedding)
        scores, indices = index.search(query_embedding.astype('float32'), 5)
        search_time = time.time() - start_time
        print(f"   Search time for top-5: {search_time*1000:.1f}ms")
        print(f"   Results found: {len([i for i in indices[0] if i != -1])}")
        # Overall health assessment
        print(f"\n=== INDEX HEALTH: {'GOOD' if consistent and len(metadata) > 1000 else 'NEEDS ATTENTION'} ===")
        return consistent and len(metadata) > 1000
    except Exception as e:
        print(f"   ERROR: Failed to validate index: {e}")
        return False
if __name__ == "__main__":
    health_ok = check_index_health()
    if health_ok:
        print("\nRAG index is healthy and ready for use.")
    else:
        print("\nRAG index has issues that need to be addressed.")