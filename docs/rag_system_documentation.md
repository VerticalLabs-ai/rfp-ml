# RAG System Documentation

## Overview

The RAG (Retrieval-Augmented Generation) System provides intelligent context retrieval for the Government RFP Bid Generation system. It uses **ChromaDB** for persistent vector storage with automatic index management.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ChromaDB RAG Engine                       │
│                (src/rag/chroma_rag_engine.py)                │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────┐     │
│  │  Sentence       │    │      ChromaDB Client        │     │
│  │  Transformers   │    │   (PersistentClient)        │     │
│  │  (all-MiniLM)   │    │   data/chroma/              │     │
│  └────────┬────────┘    └──────────────┬──────────────┘     │
│           │                            │                     │
│           ▼                            ▼                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              rfp_documents Collection               │    │
│  │   - 13,600+ indexed documents                       │    │
│  │   - HNSW index (cosine similarity)                  │    │
│  │   - Auto-persisted to disk                          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

- **Automatic Persistence**: ChromaDB automatically saves data to `data/chroma/`
- **Singleton Pattern**: Single engine instance across all requests
- **Eager Initialization**: RAG loads at FastAPI startup
- **Batch Processing**: Handles large datasets (5000 docs per batch)
- **Health Checks**: `/api/v1/rag/ready` endpoint for Docker

## Usage

### Python API

```python
from src.rag.chroma_rag_engine import get_rag_engine

# Get singleton engine
engine = get_rag_engine()

# Retrieve documents
results = engine.retrieve(
    query="government contract requirements",
    top_k=5,
    similarity_threshold=0.3
)

for doc in results:
    print(f"Score: {doc['similarity']:.3f}")
    print(f"Content: {doc['content'][:200]}")
    print(f"Metadata: {doc['metadata']}")

# Check status
stats = engine.get_statistics()
print(f"Total documents: {stats['total_documents']}")
```

### REST API

```bash
# Check status
curl http://localhost:8000/api/v1/rag/status

# Health check
curl http://localhost:8000/api/v1/rag/ready

# Rebuild index
curl -X POST http://localhost:8000/api/v1/rag/rebuild

# Detailed health
curl http://localhost:8000/api/v1/rag/health
```

## Data Flow

1. **Startup**: FastAPI lifespan initializes ChromaDB engine
2. **Index Check**: If collection is empty, builds from parquet files
3. **Persistence**: ChromaDB auto-saves to `data/chroma/`
4. **Retrieval**: Queries use HNSW index with cosine similarity
5. **Results**: Returns documents with similarity scores and metadata

## Configuration

The engine auto-detects paths for Docker vs local development:

- **Docker**: `/app/data/chroma/`
- **Local**: `data/chroma/` (relative to project root)

## Migration from FAISS

The system was migrated from FAISS to ChromaDB in December 2024:

| Aspect             | FAISS (Old)            | ChromaDB (New)      |
| ------------------ | ---------------------- | ------------------- |
| Persistence        | Manual save/load       | Automatic           |
| Index Management   | Manual build_index()   | Auto-managed        |
| Multiple Instances | Bug-prone              | Singleton pattern   |
| Initialization     | Lazy (failed silently) | Eager at startup    |
| Health Check       | None                   | `/api/v1/rag/ready` |

### Backward Compatibility

Old imports still work via compatibility shim:

```python
# Old (still works, redirects to ChromaDB)
from src.rag.rag_engine import RAGEngine, create_rag_engine

# New (recommended)
from src.rag.chroma_rag_engine import get_rag_engine
```

## Files

| File                                     | Purpose                       |
| ---------------------------------------- | ----------------------------- |
| `src/rag/chroma_rag_engine.py`           | Main ChromaDB implementation  |
| `src/rag/rag_engine.py`                  | Compatibility shim            |
| `src/rag/rag_engine_faiss_deprecated.py` | Archived FAISS implementation |
| `scripts/migrate_to_chroma.py`           | Migration script              |
| `data/chroma/`                           | Persistent storage directory  |
