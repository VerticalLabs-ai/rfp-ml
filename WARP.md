# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

AI-powered government RFP (Request for Proposal) bid generation system that leverages ML, RAG (Retrieval-Augmented Generation), and LLMs to automate RFP discovery, analysis, compliance matrix generation, pricing, go/no-go decisions, and bid document generation.

## System Architecture

The system follows a pipeline architecture with loosely coupled components:

1. **Discovery Agent** → Discovers and triages government RFPs from sources like SAM.gov
2. **RAG Engine** → Vector-based semantic search using FAISS and sentence transformers (431M+ embedding vectors)
3. **Compliance Matrix Generator** → Extracts requirements and generates compliant responses using RAG context
4. **Pricing Engine** → AI-powered competitive pricing with margin compliance
5. **Go/No-Go Engine** → Decision analysis scoring bid opportunities
6. **Document Generator** → Multi-format bid document generation (HTML, JSON, Markdown, PDF)

**Data Flow**: RFP Input → Discovery Agent → RAG Context Retrieval → Compliance + Pricing Analysis → Go/No-Go Decision → Bid Document Generation

## Environment Setup

### Virtual Environment with uv

This project uses `uv` for fast Python package management:

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install core ML/LLM dependencies (required)
uv pip install -r requirements.txt

# Install API/Dashboard dependencies (optional, only for web interface)
uv pip install -r requirements_api.txt
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
OPENAI_API_KEY=your_key_here
LLM_PROVIDER=openai  # Options: openai, huggingface, local
LLM_MODEL_NAME=gpt-4-turbo-preview
```

## Common Development Commands

### Build RAG Index (Required First Step)

Before running the system, build the vector index:

```bash
source .venv/bin/activate
python build_and_test_rag.py
```

This loads processed RFP datasets from `data/processed/`, generates embeddings, builds FAISS vector index, and saves artifacts to `data/embeddings/`.

### Run Tests

The project uses **standalone Python test scripts** (not pytest framework):

```bash
# Complete system pipeline
python test_complete_system.py

# Integrated pipeline (RAG + Compliance + Pricing + Document Gen)
python test_complete_pipeline.py

# Compliance with RAG integration
python test_compliance_with_rag.py

# Sector-specific queries
python test_sector_queries.py

# RAG system only
python build_and_test_rag.py

# Compliance matrix validation
python validate_compliance_matrix.py
```

### Component-Specific Tests

```bash
# RAG system
python tests/test_rag_system.py
python tests/comprehensive_rag_validation.py

# Pricing engine
python tests/test_pricing_engine.py
python tests/integrated_pricing_validation.py

# LLM infrastructure
python tests/test_llm_config.py
python tests/validate_llm_infrastructure.py

# Discovery agent
python tests/test_discovery_integration.py
```

### Pytest Suite

For tests that use pytest fixtures:

```bash
pytest tests/test_llm_config.py
pytest tests/test_pricing_engine.py
pytest tests/test_rag_system.py
pytest tests/test_tasks.py
pytest tests/test_go_nogo_dynamic.py
```

### Docker Deployment

```bash
# Full system (frontend + backend + Redis + worker)
docker-compose up -d --build

# Or using make commands
make build   # Build containers
make up      # Start services
make down    # Stop services
make logs    # View logs
make clean   # Remove all containers, images, and volumes
```

Services:
- **Frontend**: http://localhost:80
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Debug Scripts

Located in `debug_scripts/` for development troubleshooting:

```bash
# Test LLM configuration
python debug_scripts/demo_llm_usage.py

# Test pricing calculations
python debug_scripts/demo_pricing_samples.py

# Deep RAG validation
python debug_scripts/comprehensive_rag_validation.py

# Verify RAG index integrity
python debug_scripts/check_rag_index_health.py
```

### Backend API Server

```bash
# Manual start (alternative to Docker)
./scripts/start_backend.sh

# Or directly with uvicorn
cd api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Architecture Patterns

### Path Configuration

All components use `PathConfig` from `src/config/paths.py` for environment-agnostic path resolution:

- Dynamically detects project root in local or Docker environments
- Defaults to `/app/government_rfp_bid_1927/` in Docker
- Auto-resolves to actual project directory when running locally
- Lazy initialization of directories on first access

When initializing components, paths are automatically handled via `PathConfig`.

### Component Integration

Components follow loose coupling with optional dependencies:

- **RAG Engine** can be passed to Compliance, Pricing, and Document generators
- **LLM Config** is optional with mock fallback
- Each component works standalone or integrated
- Dependencies injected through constructors

### Data Models

Structured data uses dataclasses with JSON serialization:

- `PricingResult`, `PricingStrategy`, `CostBaseline` (pricing engine)
- `RAGConfig`, `RetrievalResult`, `RAGContext` (RAG engine)
- `RetrievalResult` contains document_id, content, metadata, similarity_score, source_dataset

### Text Processing for RAG

- **Chunking**: Default 512 tokens with 50 token overlap
- **Embeddings**: `sentence-transformers` with `all-MiniLM-L6-v2` model (384 dimensions)
- **Vector Search**: FAISS IndexFlatIP for cosine similarity
- **Index Size**: 431MB FAISS index with 1,000+ document chunks

### LLM Adapter Pattern

Supports multiple LLM providers through adapter pattern:

- **OpenAI** (primary)
- **HuggingFace** (fallback)
- **Local models**
- Mock LLM for testing (no API calls)

## Data Directory Structure

```
data/
├── raw/                    # Raw RFP CSVs (3.6GB+)
├── processed/              # Processed parquet files
│   ├── rfp_master_dataset.parquet (110MB)
│   ├── bottled_water_rfps.parquet
│   ├── construction_rfps.parquet
│   └── delivery_rfps.parquet
├── embeddings/             # RAG vector index (MUST be built first)
│   ├── faiss_index.bin (431MB)
│   ├── embeddings.npy (431MB)
│   ├── documents.pkl (479MB)
│   ├── metadata.pkl (22MB)
│   └── config.json
├── bid_documents/          # Generated bid documents
├── compliance/             # Compliance matrices (CSV, HTML, JSON)
├── pricing/                # Pricing calculations
├── templates/              # Response templates
└── content_library/        # Company profile and standard clauses
```

## Key Source Structure

```
src/
├── agents/                 # Discovery, submission, notification agents
│   ├── discovery_agent.py
│   ├── submission_agent.py
│   └── plugins/           # SAM.gov, local CSV plugins
├── rag/                    # Vector search and embedding
│   ├── rag_engine.py
│   └── build_index.py
├── compliance/             # Requirement extraction
│   └── compliance_matrix.py
├── pricing/                # AI pricing engine
│   ├── pricing_engine.py
│   └── win_probability.py
├── decision/               # Go/no-go analysis
│   └── go_nogo_engine.py
├── bid_generation/         # Document generation
│   ├── document_generator.py
│   └── visualizer.py
└── config/                 # Configuration and LLM adapters
    ├── paths.py           # Path configuration
    ├── settings.py        # Settings management
    ├── llm_adapter.py     # LLM abstraction
    └── llm_config.py      # LLM configuration
```

## Dataset Schema

Processed RFP parquet files include these key fields:

- `title`, `description` - RFP text content
- `agency`, `office` - Issuing government entities
- `naics_code` - Industry classification
- `award_amount` - Contract value (float)
- `award_date`, `response_deadline` - Dates (datetime)
- `category` - Detected category: bottled_water, construction, delivery, general

Category detection uses keyword matching in title/description.

## Development Notes

### Before Making Changes

1. **RAG Index**: Ensure RAG index is built (`python build_and_test_rag.py`) before running integrated tests
2. **Dependencies**: Verify component dependencies (RAG engine, LLM config)
3. **Path Usage**: Use `PathConfig` for all file paths, never hardcode
4. **Component Decoupling**: Maintain loose coupling; make dependencies optional where possible

### After Making Changes

1. **Run Integration Tests**: Validate with `python test_complete_system.py`
2. **Rebuild RAG Index**: If document processing changes
3. **Update Tests**: Add or update corresponding test scripts
4. **Check LLM Config**: Verify LLM integration still works (`python tests/test_llm_config.py`)

### Working with Components

When modifying or adding components:

- Follow dataclass patterns for structured data
- Support optional dependencies (RAG, LLM, etc.) with fallback behavior
- Use type hints for all function signatures
- Document classes and methods with docstrings
- Add self-contained test scripts in `tests/`
- Use `PathConfig` for all path operations

### Memory Considerations

- RAG index building requires 8GB+ RAM
- Embeddings are 431MB in memory when loaded
- For OOM issues: reduce chunk_size in RAGEngine or process datasets in smaller batches

### Dependencies Note

- **Core ML/LLM** (`requirements.txt`): Always required for ML pipeline
- **API/Dashboard** (`requirements_api.txt`): Optional, only for web interface (FastAPI, SQLAlchemy, Celery, Redis)
- Numpy version locked to `<2.0.0` for compatibility
