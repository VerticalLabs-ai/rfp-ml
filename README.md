# AI-Powered Government RFP Bid Generation System

An intelligent, end-to-end automated system for discovering, analyzing, and generating competitive bids for government Request for Proposal (RFP) opportunities. This system leverages machine learning, Retrieval-Augmented Generation (RAG), and large language models to streamline the entire bid generation process.

## 🚀 Features

### Core Capabilities

- **Autonomous RFP Discovery**: Automatically discovers and filters relevant government RFPs from multiple sources
- **Intelligent Triage**: Scores and prioritizes opportunities based on alignment with business objectives
- **RAG-Powered Context Retrieval**: Semantic search across historical RFP data using FAISS vector indexing
- **Compliance Matrix Generation**: Automatically extracts requirements and generates compliant responses
- **AI-Powered Pricing**: Generates competitive pricing with margin compliance based on historical data
- **Go/No-Go Decision Engine**: Data-driven decision analysis for bid opportunities
- **Automated Document Generation**: Produces complete bid documents in multiple formats (HTML, JSON, Markdown, PDF)

### Technical Highlights

- Vector-based semantic search with 431M+ embedding vectors
- Support for multiple LLM providers (OpenAI, HuggingFace, local models)
- Scalable processing of multi-gigabyte RFP datasets
- Structured data models with JSON serialization
- Comprehensive validation and testing framework

## 📋 Table of Contents

- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Testing](#testing)
- [Data Management](#data-management)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## 🏗️ Architecture

The system follows a modular pipeline architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                     RFP Input Sources                            │
│         (SAM.gov, FBO, Government Contract Databases)            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Discovery Agent                               │
│         • RFP Discovery  • Filtering  • Triage                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      RAG Engine                                  │
│    • Vector Search  • FAISS Index  • Context Retrieval           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌───────────────────────┬─────────────────────┬───────────────────┐
│  Compliance Matrix    │   Pricing Engine    │  Go/No-Go Engine  │
│  • Requirements       │   • Cost Analysis   │  • Scoring        │
│  • Responses          │   • Margin Calc     │  • Risk Analysis  │
└───────────────────────┴─────────────────────┴───────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Bid Document Generator                          │
│         • Template Rendering  • Multi-format Export              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              Final Bid Documents (HTML, JSON, MD, PDF)           │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

- **Discovery Agent** (`src/agents/discovery_agent.py`): Autonomous RFP discovery and triage
- **RAG Engine** (`src/rag/rag_engine.py`): Vector-based semantic search using sentence transformers
- **Compliance Matrix** (`src/compliance/compliance_matrix.py`): Requirement extraction and response generation
- **Pricing Engine** (`src/pricing/pricing_engine.py`): AI-powered competitive pricing
- **Go/No-Go Engine** (`src/decision/go_nogo_engine.py`): Decision analysis and scoring
- **Document Generator** (`src/bid_generation/document_generator.py`): Multi-format bid document creation

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer and resolver
- 8GB+ RAM recommended for embeddings
- 10GB+ disk space for datasets and models

### Install uv

If you don't have `uv` installed, install it first:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### Install Dependencies

```bash
# Clone the repository
git clone https://github.com/VerticalLabs-ai/rfp-ml
cd rfp_ml

# Create virtual environment with uv
uv venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install core ML and LLM dependencies
uv pip install -r requirements.txt

# (Optional) Install API/Dashboard dependencies if running the web interface
uv pip install -r requirements_api.txt
```

### Key Dependencies

**Core ML & LLM Stack (`requirements.txt`):**

- **LLM Integration**: `openai>=1.3.0`, `transformers>=4.30.0`, `torch>=2.0.0`
- **Vector Search & RAG**: `faiss-cpu>=1.7.0`, `langchain>=0.1.0`, `sentence-transformers>=2.2.2`
- **Data Processing**: `pandas>=1.5.0`, `numpy<2.0.0`, `scikit-learn>=1.2.0`
- **Utilities**: `pydantic>=2.0.0`, `jinja2>=3.1.0`, `requests>=2.28.0`

**API/Dashboard (`requirements_api.txt` - Optional):**

- **Web Framework**: `fastapi>=0.104.0`, `uvicorn[standard]>=0.24.0`
- **Database**: `sqlalchemy>=2.0.0`, `alembic>=1.12.0`
- **Real-time**: `websockets>=12.0`
- **Automation**: `playwright>=1.40.0`, `selenium>=4.15.0`
- **Task Queue**: `celery>=5.3.0`, `redis>=5.0.0`

## ⚙️ Configuration

### Environment Setup

1. Copy the environment template:

```bash
cp env.example .env
```

2. Configure your `.env` file:

```bash
# OpenAI Configuration (Primary)
OPENAI_API_KEY=your_openai_api_key_here

# HuggingFace Configuration (Fallback)
HUGGINGFACE_API_KEY=your_huggingface_api_key_here
HUGGINGFACE_BASE_URL=https://api-inference.huggingface.co/models

# LLM Provider Selection
LLM_PROVIDER=openai  # Options: openai, huggingface, local

# Model Configuration
LLM_MODEL_NAME=gpt-5.1
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
LLM_TIMEOUT=30.0
```

### Path Configuration

The system defaults to Docker-style absolute paths (`/app/government_rfp_bid_1927/`). For local development, you may need to adjust paths in component initialization or set environment variables.

## 🚀 Quick Start

### 1. Build the RAG Index

Before running the system, build the vector index from your processed RFP data:

```bash
# Make sure virtual environment is activated
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

python build_and_test_rag.py
```

This will:

- Load processed RFP datasets from `data/processed/`
- Generate embeddings using sentence transformers
- Build FAISS vector index
- Save artifacts to `data/embeddings/`

### 2. Run a Complete Pipeline Test

Test the entire system with sample RFPs:

```bash
python test_complete_system.py
```

### 3. Process a Single RFP

```python
from src.decision.go_nogo_engine import GoNoGoEngine
from src.compliance.compliance_matrix import ComplianceMatrixGenerator
from src.pricing.pricing_engine import PricingEngine
from src.bid_generation.document_generator import BidDocumentGenerator

# Initialize components
compliance_gen = ComplianceMatrixGenerator()
pricing_engine = PricingEngine()
doc_generator = BidDocumentGenerator(
    compliance_generator=compliance_gen,
    pricing_engine=pricing_engine
)
decision_engine = GoNoGoEngine(
    compliance_generator=compliance_gen,
    pricing_engine=pricing_engine,
    document_generator=doc_generator
)

# Process RFP
rfp_data = {...}  # Your RFP data
decision = decision_engine.analyze_rfp_opportunity(rfp_data)

# Generate bid if recommended
if decision.recommendation in ['go', 'review']:
    bid_document = doc_generator.generate_bid_document(rfp_data)
    doc_generator.export_bid_document(bid_document, "markdown")
```

## 📖 Usage

### Discovery Agent

Discover and triage RFPs from government sources:

```python
from src.agents.discovery_agent import RFPDiscoveryAgent

agent = RFPDiscoveryAgent(config_path="config.json")
discovered_rfps = agent.discover_rfps(sources=["SAM.gov"])
triaged_rfps = agent.triage_rfps(discovered_rfps)
```

### RAG Engine

Semantic search across historical RFP data:

```python
from src.rag.rag_engine import RAGEngine

rag = RAGEngine()
rag.build_index()  # One-time index build

# Retrieve similar RFPs
results = rag.retrieve("bottled water delivery services", k=5)
for result in results:
    print(f"Score: {result['score']:.3f}")
    print(f"Category: {result['metadata']['category']}")
    print(f"Title: {result['metadata']['title']}\n")
```

### Compliance Matrix Generation

Extract requirements and generate responses:

```python
from src.compliance.compliance_matrix import ComplianceMatrixGenerator

compliance = ComplianceMatrixGenerator()
matrix = compliance.generate_compliance_matrix(rfp_data)

# Export in multiple formats
compliance.export_matrix(matrix, "csv")
compliance.export_matrix(matrix, "html")
compliance.export_matrix(matrix, "json")
```

### Pricing Engine

Generate competitive pricing:

```python
from src.pricing.pricing_engine import PricingEngine

pricing = PricingEngine(target_margin=0.40)
pricing_result = pricing.calculate_price(rfp_data)

print(f"Total Price: ${pricing_result.total_price:,.2f}")
print(f"Margin: {pricing_result.margin_percentage:.1f}%")
print(f"Confidence: {pricing_result.confidence_score:.1%}")
```

## 🧪 Testing

The project uses standalone Python test scripts (not pytest):

### Run All Tests

```bash
# Complete system test
python test_complete_system.py

# Integrated pipeline test
python test_complete_pipeline.py

# Compliance with RAG
python test_compliance_with_rag.py

# Sector-specific queries
python test_sector_queries.py
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

### Debug Scripts

Located in `debug_scripts/` for development and troubleshooting:

```bash
# Test LLM configuration
python debug_scripts/demo_llm_usage.py

# Test pricing calculations
python debug_scripts/demo_pricing_samples.py

# Validate RAG system
python debug_scripts/comprehensive_rag_validation.py

# Check RAG index health
python debug_scripts/check_rag_index_health.py
```

## 💾 Data Management

### Directory Structure

```
data/
├── raw/                           # Raw RFP data (3.6GB+)
│   ├── ContractOpportunitiesFullCSV.csv (189MB)
│   ├── FY2023_archived_opportunities.csv (1.3GB)
│   ├── FY2024_archived_opportunities.csv (1.1GB)
│   └── FY2025_archived_opportunities.csv (1.1GB)
├── processed/                     # Processed parquet files
│   ├── rfp_master_dataset.parquet (110MB)
│   ├── bottled_water_rfps.parquet (11MB)
│   ├── construction_rfps.parquet (81MB)
│   └── delivery_rfps.parquet (17MB)
├── embeddings/                    # RAG vector index
│   ├── faiss_index.bin (431MB)
│   ├── embeddings.npy (431MB)
│   ├── documents.pkl (479MB)
│   ├── metadata.pkl (22MB)
│   └── config.json
├── bid_documents/                 # Generated bids
├── compliance/                    # Compliance matrices
├── pricing/                       # Pricing calculations
├── templates/                     # Response templates
└── content_library/               # Company data
    ├── company_profile.json
    └── standard_clauses.json
```

### Data Schema

Processed RFP datasets include:

| Field               | Type     | Description                                                   |
| ------------------- | -------- | ------------------------------------------------------------- |
| `title`             | string   | RFP title                                                     |
| `description`       | string   | Full RFP description                                          |
| `agency`            | string   | Issuing government agency                                     |
| `office`            | string   | Specific office/department                                    |
| `naics_code`        | string   | Industry classification code                                  |
| `award_amount`      | float    | Contract award amount                                         |
| `award_date`        | datetime | Award date                                                    |
| `response_deadline` | datetime | Submission deadline                                           |
| `category`          | string   | RFP category (bottled_water, construction, delivery, general) |

## 📚 API Documentation

### RAGEngine

```python
class RAGEngine:
    """Retrieval-Augmented Generation engine for RFP datasets."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        """Initialize RAG engine with embedding model and chunking parameters."""

    def build_index(self, force_rebuild: bool = False) -> None:
        """Build or load FAISS index from processed RFP data."""

    def retrieve(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """Retrieve top-k most similar documents for a query."""

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG system."""
```

### PricingEngine

```python
class PricingEngine:
    """AI-powered pricing engine for government RFP bids."""

    def __init__(
        self,
        target_margin: float = 0.40,
        minimum_margin: float = 0.15
    ):
        """Initialize pricing engine with margin parameters."""

    def calculate_price(self, rfp_data: Dict) -> PricingResult:
        """Generate competitive pricing for an RFP."""

    def get_cost_baseline(self, category: str) -> CostBaseline:
        """Retrieve cost baseline for a category."""
```

### ComplianceMatrixGenerator

```python
class ComplianceMatrixGenerator:
    """Generate compliance matrices mapping RFP requirements to responses."""

    def generate_compliance_matrix(
        self,
        rfp_data: Dict,
        use_rag: bool = True
    ) -> Dict:
        """Extract requirements and generate compliance responses."""

    def export_matrix(
        self,
        matrix: Dict,
        format: str = "csv"
    ) -> str:
        """Export compliance matrix in specified format."""
```

## 🛠️ Development

### Project Structure

```
rfp_ml/
├── src/                          # Source code
│   ├── agents/                   # Discovery agents
│   ├── rag/                      # RAG engine
│   ├── compliance/               # Compliance generation
│   ├── pricing/                  # Pricing engine
│   ├── decision/                 # Go/No-Go decisions
│   ├── bid_generation/           # Document generation
│   └── config/                   # Configuration & LLM adapters
├── tests/                        # Test suite
├── debug_scripts/                # Debug utilities
├── data/                         # Data directories
├── docs/                         # Documentation
├── analysis/                     # Analysis reports
├── requirements.txt        # Core ML dependencies
├── requirements_llm.txt          # LLM dependencies
├── CLAUDE.md                     # AI assistant guidance
└── README.md                     # This file
```

### Adding New Components

1. **Create component module** in appropriate `src/` subdirectory
2. **Follow dataclass patterns** for structured data
3. **Support optional dependencies** (RAG, LLM, etc.)
4. **Add component tests** in `tests/`
5. **Update CLAUDE.md** with component details

### Code Style

- Use type hints for function signatures
- Document classes and methods with docstrings
- Follow PEP 8 naming conventions
- Use dataclasses for structured data models
- Prefer composition over inheritance

### Running Development Commands

```bash
# Check for outdated dependencies
ncu

# List all files recursively
fd . -t f

# Search for content in files
rg "search_term"

# Find files by name
fd "filename"
```

## 🔧 Troubleshooting

### Common Issues

**Issue**: RAG index not found

```bash
# Solution: Build the index
python build_and_test_rag.py
```

**Issue**: LLM API errors

```bash
# Solution: Check your .env configuration
cat .env | grep API_KEY

# Verify LLM config
python debug_scripts/demo_llm_usage.py
```

**Issue**: Out of memory during embedding generation

```bash
# Solution: Process in smaller batches (edit chunk_size in RAGEngine)
# Or use a smaller embedding model
```

**Issue**: Package installation is slow

```bash
# Solution: Use uv for faster package installation
uv pip install -r requirements.txt
uv pip install -r requirements_llm.txt
```

**Issue**: Path errors in Docker vs. local

```python
# Solution: Override paths when initializing components
rag = RAGEngine(
    embeddings_dir="./data/embeddings",
    processed_data_dir="./data/processed"
)
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

```bash
# Check RAG index health
python debug_scripts/check_rag_index_health.py

# Validate LLM infrastructure
python debug_scripts/final_llm_validation.py

# Examine processed data
python debug_scripts/examine_processed_data.py
```

## 📊 Performance

### System Benchmarks

- **RAG Index Build Time**: ~2-5 minutes (depending on dataset size)
- **Average Retrieval Time**: <1 second
- **Embedding Dimension**: 384 (all-MiniLM-L6-v2)
- **Index Size**: 431MB (FAISS)
- **Total Documents**: 1,000+ chunks

### Optimization Tips

1. **Use GPU acceleration** for embedding generation (change `use_gpu=True`)
2. **Cache embeddings** to avoid regeneration
3. **Batch process** large datasets
4. **Use IVF index** for very large datasets (>1M vectors)

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Update documentation
6. Submit a pull request

## 📄 License

[Add your license information here]

## 🙏 Acknowledgments

- Built with [LangChain](https://langchain.com/), [FAISS](https://faiss.ai/), and [Sentence Transformers](https://www.sbert.net/)
- Uses government RFP data from [SAM.gov](https://sam.gov/)

## 📞 Support

For issues, questions, or feature requests, please open an issue on GitHub or contact [your contact information].

---

**Version**: 1.0.0
**Last Updated**: November 14, 2025
