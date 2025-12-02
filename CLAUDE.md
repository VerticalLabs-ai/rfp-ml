# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered government RFP (Request for Proposal) bid generation system. It uses machine learning, RAG (Retrieval-Augmented Generation), and LLMs to automate the process of analyzing RFPs, generating compliance matrices, pricing bids, making go/no-go decisions, and producing complete bid documents.

## Core System Architecture

The system follows a pipeline architecture with these main components:

1. **Discovery Agent** (`src/agents/discovery_agent.py`) - Discovers, filters, and triages RFPs from government sources
2. **RAG Engine** (`src/rag/chroma_rag_engine.py`) - **ChromaDB-based** vector search with automatic persistence and sentence transformers for contextual retrieval from historical RFP data
3. **Compliance Matrix Generator** (`src/compliance/compliance_matrix.py`) - Extracts requirements from RFPs and generates compliance responses
4. **Pricing Engine** (`src/pricing/pricing_engine.py`) - AI-powered pricing with margin compliance based on historical data
5. **Go/No-Go Engine** (`src/decision/go_nogo_engine.py`) - Decision analysis for bid opportunities
6. **Document Generator** (`src/bid_generation/document_generator.py`) - Produces complete bid documents in multiple formats

**Integration Flow**: RFP → Discovery Agent → RAG Context Retrieval → Compliance Matrix + Pricing → Go/No-Go Decision → Bid Document Generation

## Environment Setup

```bash
# Copy environment template
cp env.example .env

# Required environment variables
OPENAI_API_KEY=your_key_here
LLM_PROVIDER=openai  # or huggingface, local
LLM_MODEL_NAME=gpt-5.1
```

## Dependencies

Two requirements files:

- `requirements.txt` - Core ML & LLM packages (sentence-transformers, langchain, openai, transformers, torch, numpy<2.0.0)
- `requirements_api.txt` - API/Dashboard (fastapi, uvicorn, sqlalchemy, websockets, **chromadb**) - **Optional**, only needed for web interface

Install using uv:

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install core dependencies (ML + LLM)
uv pip install -r requirements.txt

# (Optional) Install API/Dashboard dependencies
uv pip install -r requirements_api.txt
```

## Common Development Tasks

### Running Tests

The project uses standalone Python test scripts (not pytest framework):

```bash
# Test complete system pipeline
python test_complete_system.py

# Test integrated pipeline (RAG + Compliance + Pricing + Document Generation)
python test_complete_pipeline.py

# Test compliance with RAG integration
python test_compliance_with_rag.py

# Test sector-specific queries
python test_sector_queries.py

# Test RAG system only
python build_and_test_rag.py

# Validate compliance matrix generation
python validate_compliance_matrix.py
```

### Testing Specific Components

```bash
# RAG system validation
python tests/test_rag_system.py
python tests/comprehensive_rag_validation.py
python tests/final_rag_validation_report.py

# Pricing engine validation
python tests/test_pricing_engine.py
python tests/integrated_pricing_validation.py

# LLM infrastructure validation
python tests/test_llm_config.py
python tests/validate_llm_infrastructure.py
python tests/final_llm_validation.py

# Discovery agent testing
python tests/test_discovery_integration.py
```

### RAG System (ChromaDB)

The RAG system uses **ChromaDB** for persistent vector storage with automatic index management.

```bash
# Check RAG status via API
curl http://localhost:8000/api/v1/rag/status

# Rebuild RAG index from parquet files
curl -X POST http://localhost:8000/api/v1/rag/rebuild

# RAG data is stored in data/chroma/ (persists across container restarts)
# ChromaDB handles indexing automatically - no manual build required

# For local development/migration:
python scripts/migrate_to_chroma.py
```

**Key RAG endpoints:**
- `GET /api/v1/rag/status` - Check index status and document count
- `GET /api/v1/rag/ready` - Health check (returns 503 if not ready)
- `POST /api/v1/rag/rebuild` - Rebuild index from parquet files
- `GET /api/v1/rag/health` - Detailed health check

### Debug Scripts

Located in `debug_scripts/` for development and troubleshooting:

- `demo_llm_usage.py` - Test LLM configuration
- `demo_pricing_samples.py` - Test pricing calculations
- `comprehensive_rag_validation.py` - Deep RAG system validation
- `check_rag_index_health.py` - Verify RAG index integrity

## Data Directory Structure

```
data/
├── raw/                    # Raw RFP data
├── processed/              # Processed parquet files
│   ├── rfp_master_dataset.parquet
│   ├── bottled_water_rfps.parquet
│   ├── construction_rfps.parquet
│   └── delivery_rfps.parquet
├── chroma/                 # ChromaDB persistent storage (auto-managed)
│   ├── chroma.sqlite3      # Vector index metadata
│   └── [uuid]/             # Collection data
├── embeddings/             # Legacy FAISS index (deprecated)
├── bid_documents/          # Generated bid documents (HTML, JSON, MD)
├── compliance/             # Compliance matrices (CSV, HTML, JSON)
├── pricing/                # Pricing data and calculations
├── templates/              # Response templates
└── content_library/        # Company profile and standard clauses
```

## Key Design Patterns

### Path Configuration

All components use absolute paths defaulting to `/app/government_rfp_bid_1927/` for Docker compatibility. When running locally, these paths may need adjustment in component initialization.

### Component Integration

Components are designed for loose coupling with optional dependencies:

- RAG engine can be passed to Compliance, Pricing, and Document generators
- LLM config is optional with mock fallback
- Each component works standalone or integrated

### Text Processing

- RAG uses chunking (default 512 tokens with 50 token overlap)
- Embeddings generated using `sentence-transformers` (all-MiniLM-L6-v2)
- **ChromaDB** with HNSW index for cosine similarity search
- Automatic batching for large document sets (5000 docs per batch)

### Data Models

Components use dataclasses for structured data:

- `PricingResult`, `PricingStrategy`, `CostBaseline`
- Serializable to JSON for persistence

### RAG Usage

```python
# Get the singleton ChromaDB RAG engine
from src.rag.chroma_rag_engine import get_rag_engine

engine = get_rag_engine()

# Retrieve relevant documents
results = engine.retrieve("government contract requirements", top_k=5)
for doc in results:
    print(f"Score: {doc['similarity']:.3f} - {doc['content'][:100]}")

# Check status
stats = engine.get_statistics()
print(f"Total documents: {stats['total_documents']}")
```

## Development Notes

- The system expects processed RFP data in parquet format with specific schema (title, description, agency, naics_code, award_amount, etc.)
- **RAG is auto-initialized at startup** - ChromaDB handles persistence automatically
- LLM integration uses adapter pattern supporting OpenAI, HuggingFace, and local models
- Category detection uses keywords in title/description: bottled_water, construction, delivery, general
- All test scripts are self-contained and can be run directly with `python script_name.py`

## Working with Components

When modifying components:

1. Check component dependencies (RAG engine, LLM config, etc.)
2. Update corresponding test scripts
3. Use `POST /api/v1/rag/rebuild` if document processing changes
4. Validate with integration tests before committing

## RAG Migration Notes (December 2024)

The RAG system was migrated from FAISS to ChromaDB for improved reliability:

- **Old implementation**: `src/rag/rag_engine_faiss_deprecated.py` (archived)
- **New implementation**: `src/rag/chroma_rag_engine.py`
- **Compatibility shim**: `src/rag/rag_engine.py` redirects to ChromaDB
- **Data location**: `data/chroma/` (auto-persisted)

Key improvements:
- Automatic persistence (survives container restarts)
- Singleton pattern prevents multiple engine instances
- Eager initialization at startup
- Health check endpoint for Docker
