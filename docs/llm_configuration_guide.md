# LLM Configuration Module Documentation
## Overview
The LLM Configuration Module (`src/config/llm_config.py`) provides a unified interface for managing Language Model backends in the Government RFP Bid Generation System. It supports multiple LLM providers with automatic fallback mechanisms.
## Features
### Supported Backends
- **OpenAI GPT-5.1** (Primary)
- **Local HuggingFace Models** (Fallback)
- **Automatic backend selection and fallback**
### Configuration Management
- Environment variable loading
- Parameter customization for different use cases
- Device detection (CPU/GPU)
- Timeout and error handling
### Use Case Optimization
- **Bid Generation**: `temperature=0.7, max_tokens=2000`
- **Structured Extraction**: `temperature=0.3, max_tokens=1000`
- **Pricing**: `temperature=0.5, max_tokens=800`
## Installation