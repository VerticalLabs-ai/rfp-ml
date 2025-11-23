# Project Context: RFP Bid Generation System

## Overview
This project is an **AI-Powered Government RFP Bid Generation System**. It autonomously discovers, analyzes, and generates competitive bids for government Request for Proposals (RFPs). It features a **FastAPI** backend, a **React** frontend, and a complex **Python** core leveraging RAG (Retrieval-Augmented Generation), Vector Search (FAISS), and LLMs.

## 🚀 Quick Start

### Prerequisites
*   **Python 3.8+**
*   **uv** (Python package manager)
*   **Node.js & npm** (Frontend)

### Running the Application
The project uses helper scripts in the `scripts/` directory, or you can use Docker.

#### Option 1: Docker (Recommended)
```bash
docker-compose up -d --build
```
- **Frontend**: http://localhost:80
- **Backend**: http://localhost:8000

#### Option 2: Manual Scripts

1.  **Start Backend:**
    ```bash
    ./scripts/start_backend.sh
    # Runs FastAPI on http://localhost:8000
    ```
2.  **Start Frontend:**
    ```bash
    ./scripts/start_frontend.sh
    # Runs React App on http://localhost:3000
    ```

## 📂 Directory Structure

### Core Logic (`src/`)
*   **`src/agents/`**: Autonomous agents.
    *   `discovery_agent.py`: Main discovery logic (refactored to use plugins).
    *   `submission_agent.py`: Automated submission.
    *   `forecasting_service.py`: **NEW** Predictive analytics for future RFPs.
    *   **`plugins/`**: **NEW** Data source plugins (`sam_gov_plugin.py`, `local_csv_plugin.py`).
*   **`src/rag/`**: RAG Engine using FAISS and Sentence Transformers (`rag_engine.py`).
*   **`src/compliance/`**: Logic for extracting requirements and generating compliance matrices.
*   **`src/pricing/`**: AI-powered pricing engine.
*   **`src/bid_generation/`**: Document generation (PDF, Markdown, JSON).
    *   `document_generator.py`: Main generation logic.
    *   `style_manager.py`: **NEW** Voice of the Customer style tuning.
    *   `visualizer.py`: **NEW** Automated chart generation (Gantt, Org charts).

### Web Application
*   **`api/`**: FastAPI backend.
    *   `app/main.py`: Entry point.
    *   `app/routes/`: API endpoints (RFPs, Pipeline, Submissions).
    *   `app/models/`: SQLAlchemy database models.
*   **`frontend/`**: React + TypeScript frontend.
    *   `src/pages/`: Dashboard, Discovery, Pipeline, etc.
    *   `src/services/api.ts`: Axios API client.

### Data Management (`data/`)
*   **`data/raw/`**: Raw RFP datasets (CSV).
*   **`data/processed/`**: Cleaned Parquet files.
*   **`data/embeddings/`**: FAISS vector indices and metadata.
*   **`data/config/`**: System configuration JSONs.

## 🛠 Development Conventions

### Python (Backend & Core)
*   **Dependency Management:** Uses `uv`.
    *   Install: `uv pip install -r requirements.txt`
*   **Style:**
    *   Use **Type Hints** for all function signatures.
    *   Use **Dataclasses** or Pydantic models for structured data.
    *   Modular architecture: Composition over inheritance.
*   **Testing:**
    *   **Standalone Scripts:** The project relies heavily on specific test scripts in `tests/` and root directory (e.g., `test_complete_system.py`), rather than a standard `pytest` discovery suite.
    *   **Debug Scripts:** Use `debug_scripts/` for isolated component testing (e.g., `demo_llm_usage.py`).

### TypeScript (Frontend)
*   **Framework:** React with Vite.
*   **Styling:** Tailwind CSS (v4.1).
*   **State Management:** Zustand + TanStack Query.
*   **Components:** Radix UI primitives.

## 🧪 Key Test Commands

*   **Full System Test:** `python test_complete_system.py`
*   **Pipeline Integration:** `python test_complete_pipeline.py`
*   **Submission Agent:** `python scripts/test_submission_agent.py`
*   **RAG Validation:** `python debug_scripts/comprehensive_rag_validation.py`

## 📝 Configuration
*   **Environment:** Managed via `.env` (template: `.env.example`).
*   **LLM:** Configured in `.env` (OpenAI, HuggingFace, or Local).
*   **Paths:** Docker-style paths are default; override in code or env for local dev.
