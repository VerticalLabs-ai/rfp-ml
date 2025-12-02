#!/usr/bin/env python3
"""
Migrate RAG system to ChromaDB.

This script:
1. Initializes the ChromaDB engine
2. Builds the index from parquet files if empty
3. Verifies the migration was successful

Run locally:
    python scripts/migrate_to_chroma.py

Run in Docker:
    docker exec rfp_backend python /app/scripts/migrate_to_chroma.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Also add /app for Docker environment
if Path("/app").exists() and "/app" not in sys.path:
    sys.path.insert(0, "/app")


def migrate():
    """Run the ChromaDB migration."""
    print("=" * 60)
    print("ChromaDB Migration Script")
    print("=" * 60)

    try:
        from src.rag.chroma_rag_engine import get_rag_engine
    except ImportError as e:
        print(f"ERROR: Failed to import ChromaDB engine: {e}")
        print("Make sure chromadb is installed: pip install chromadb>=1.0.0")
        sys.exit(1)

    # Get the engine (singleton)
    print("\n1. Initializing ChromaDB engine...")
    try:
        engine = get_rag_engine()
        print(f"   ChromaDB path: {engine._persist_directory}")
    except Exception as e:
        print(f"   ERROR: {e}")
        sys.exit(1)

    # Check current state
    print("\n2. Checking current collection state...")
    stats = engine.get_statistics()
    print(f"   Collection: {stats['collection_name']}")
    print(f"   Documents: {stats['total_documents']}")

    # Build if empty
    if stats['total_documents'] == 0:
        print("\n3. Collection is empty, building from parquet files...")
        try:
            engine.build_index(force_rebuild=True)
            new_stats = engine.get_statistics()
            print(f"   Build complete: {new_stats['total_documents']} documents indexed")
        except Exception as e:
            print(f"   ERROR during build: {e}")
            sys.exit(1)
    else:
        print("\n3. Collection already populated, skipping build")

    # Verify with a test query
    print("\n4. Running test query...")
    try:
        results = engine.retrieve("government contract requirements", top_k=3)
        print(f"   Retrieved {len(results)} documents")
        if results:
            print(f"   Top result similarity: {results[0]['similarity']:.4f}")
    except Exception as e:
        print(f"   WARNING: Test query failed: {e}")

    # Final status
    print("\n" + "=" * 60)
    final_stats = engine.get_statistics()
    print("Migration Summary:")
    print(f"  - Collection: {final_stats['collection_name']}")
    print(f"  - Total documents: {final_stats['total_documents']}")
    print(f"  - Persist directory: {final_stats['persist_directory']}")
    print(f"  - Status: {'SUCCESS' if final_stats['total_documents'] > 0 else 'EMPTY (run rebuild)'}")
    print("=" * 60)

    return final_stats['total_documents'] > 0


def force_rebuild():
    """Force a complete rebuild of the ChromaDB index."""
    print("Force rebuilding ChromaDB index...")

    from src.rag.chroma_rag_engine import get_rag_engine
    engine = get_rag_engine()

    print(f"Current documents: {engine.collection.count()}")
    print("Starting rebuild...")

    engine.build_index(force_rebuild=True)

    print(f"Rebuild complete: {engine.collection.count()} documents")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate RAG system to ChromaDB")
    parser.add_argument("--force", action="store_true", help="Force rebuild even if documents exist")
    args = parser.parse_args()

    if args.force:
        success = force_rebuild()
    else:
        success = migrate()

    sys.exit(0 if success else 1)
