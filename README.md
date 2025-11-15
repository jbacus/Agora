# 📚 Virtual Debate Panel

A multi-perspective chat application that enables users to query multiple authors concurrently, with each author responding in their unique voice and highlighting intellectual disagreements.

## 🎯 Project Overview

The Virtual Debate Panel uses a Retrieval-Augmented Generation (RAG) pipeline with semantic routing to automatically select 2-5 relevant authors to respond to user queries. Each author maintains their distinct voice, tone, and philosophical stance, creating a dynamic intellectual debate.

## ✨ Key Features

- **Intelligent Author Selection**: Semantic router automatically selects relevant authors based on query content
- **Concurrent Multi-Author Responses**: Parallel RAG pipeline for simultaneous author responses
- **Multi-Round Debates**: NEW! Make authors "fight" - authors respond to and critique each other's perspectives across multiple rounds
- **Distinct Author Voices**: Each author maintains unique tone, vocabulary, and philosophical stance
- **Comparative Formatting**: Clear presentation of contrasting viewpoints
- **Brief Responses**: Max 3 paragraphs per author for concise, focused debate

## 🏗️ Architecture

### Three-Layer System

```
┌─────────────────────────────────────────────────────┐
│               API Layer (FastAPI)                   │
│  • REST endpoints for queries                       │
│  • WebSocket support for streaming                  │
│  • Authentication & rate limiting                   │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────┴─────────────────────────────────┐
│          Logic Layer (Semantic Router)              │
│  • Query vectorization                              │
│  • Cosine similarity calculation                    │
│  • Author panel selection (threshold-based)         │
│  • Response aggregation & formatting                │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────┴─────────────────────────────────┐
│       Processing Layer (RAG Pipeline)               │
│  • Vector database queries (ChromaDB/Pinecone)      │
│  • LLM integration (Gemini 2.5 Pro / OpenAI)        │
│  • Parallel concurrent processing                   │
│  • System prompt enforcement                        │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────┴─────────────────────────────────┐
│           Data Layer (The Library)                  │
│  • Vector database (embeddings)                     │
│  • Author expertise profiles                        │
│  • Book chunks & metadata                           │
│  • System prompts repository                        │
└─────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Poetry (recommended) or pip
- API keys for:
  - LLM provider (Google Gemini, OpenAI, or Anthropic)
  - Vector database (ChromaDB local or Pinecone cloud - ChromaDB is default)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd virtual-debate-panel

# Install dependencies using Poetry
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Initialize the vector database
poetry run python scripts/init_database.py

# Run data ingestion (Phase 1: Marx only)
poetry run python scripts/ingest_author.py --author marx --input data/raw/marx/
```

**Alternative: Using pip**
```bash
pip install -r requirements.txt
python scripts/init_database.py
```

### Running the Application

```bash
# Start the API server using Poetry
poetry run uvicorn src.api.main:app --reload --port 8000

# In a separate terminal, start the UI dev server
cd src/ui
python -m http.server 3000
```

Visit `http://localhost:3000` to access the chat interface.

## 📁 Project Structure

```
virtual-debate-panel/
├── src/
│   ├── data/                    # Data layer
│   │   ├── __init__.py
│   │   ├── vector_db.py        # Vector database interface
│   │   ├── models.py           # Data models (Author, Query, Response)
│   │   └── embeddings.py       # Embedding generation
│   ├── processing/              # Processing layer
│   │   ├── __init__.py
│   │   ├── llm_client.py       # LLM API integration
│   │   ├── rag_pipeline.py     # RAG retrieval & generation
│   │   ├── debate_orchestrator.py  # Multi-round debate orchestration
│   │   └── prompts.py          # System prompt management
│   ├── routing/                 # Logic layer
│   │   ├── __init__.py
│   │   ├── semantic_router.py  # Author selection logic
│   │   └── response_aggregator.py  # Response formatting
│   ├── api/                     # API server
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI application
│   │   ├── routes.py           # API endpoints
│   │   └── schemas.py          # Pydantic models
│   └── ui/                      # Web interface
│       ├── index.html
│       ├── app.js
│       └── styles.css
├── config/
│   ├── authors/                 # Author profiles & prompts
│   │   ├── marx.yaml
│   │   ├── whitman.yaml
│   │   └── baudelaire.yaml
│   └── settings.py             # Application configuration
├── scripts/
│   ├── init_database.py        # Database initialization
│   ├── ingest_author.py        # Data ingestion pipeline
│   └── create_expertise_profiles.py  # Generate author profiles
├── tests/
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── docs/
│   ├── ARCHITECTURE.md         # Detailed architecture
│   ├── API.md                  # API documentation
│   └── DEPLOYMENT.md           # Deployment guide
├── data/
│   ├── raw/                    # Source texts (not in git)
│   ├── processed/              # Cleaned & chunked texts
│   └── embeddings/             # Pre-computed embeddings
├── .env.example                # Environment template
├── .gitignore
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Poetry configuration
└── README.md                   # This file
```

## 🛠️ Development Phases

### Phase 1: MVP - Single-Author & Data Pipeline ✅

- [x] P1.1: Project setup & configuration
- [x] P1.2: Data ingestion pipeline
- [x] P1.3: RAG pipeline (single and multi-author)
- [x] P1.4: Basic UI

**Goal**: Working chat interface with authors responding using RAG. ✅

### Phase 2: Multi-Author Router ✅

- [x] P2.1: Create expertise profiles (Marx, Whitman, Manson, and more)
- [x] P2.2: Implement semantic router with threshold-based selection
- [x] P2.3: Update UI for automatic author selection

**Goal**: System automatically selects relevant authors based on query. ✅

### Phase 3: Virtual Debate Panel ✅

- [x] P3.1: Parallel processing for concurrent responses
- [x] P3.2: System prompt enforcement (3-paragraph limit)
- [x] P3.3: Response aggregation & comparative formatting
- [x] P3.4: Streaming support via Server-Sent Events
- [x] P3.5: Response caching and telemetry

**Goal**: Full multi-author debate with clear contrasting viewpoints. ✅

## 🔧 Configuration

### Environment Variables

```bash
# LLM Configuration
LLM_PROVIDER=gemini  # or 'openai', 'anthropic'
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash-exp  # Current default
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Vector Database
VECTOR_DB=chromadb  # or 'pinecone'
CHROMA_PERSIST_DIR=./data/chroma_db
PINECONE_API_KEY=your_key_here
PINECONE_ENVIRONMENT=us-west1-gcp

# Embedding Model
EMBEDDING_MODEL=text-embedding-004  # or 'text-embedding-ada-002'

# Semantic Router
RELEVANCE_THRESHOLD=0.60  # Empirically tested optimal value
MIN_AUTHORS=2
MAX_AUTHORS=5

# API Server
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
```

### Author Configuration

Author profiles are defined in `config/authors/` as YAML files. Currently available authors:

- **Karl Marx** - Political economy, capitalism, class struggle
- **Walt Whitman** - Poetry, democracy, transcendentalism, American identity
- **Mark Manson** - Psychology, self-help, personal development, modern culture

Example configuration:

```yaml
# config/authors/marx.yaml
name: Karl Marx
expertise_domains:
  - political economy
  - capitalism
  - class struggle
  - labor theory of value
voice_characteristics:
  tone: analytical, critical, revolutionary
  vocabulary: dialectical, materialist, proletarian
  perspective: class-based analysis
system_prompt: |
  You are Karl Marx, the 19th-century philosopher and economist...
  [Full system prompt]
```

## 📊 Data Requirements

### Input Format

Place source texts in `data/raw/<author>/`:

```
data/raw/
├── marx/
│   ├── capital_vol1.txt
│   ├── communist_manifesto.txt
│   └── grundrisse.txt
├── whitman/
│   └── leaves_of_grass.txt
└── manson/
    ├── subtle_art.txt
    └── everything_is_fucked.txt
```

### Processing Pipeline

1. **Chunking**: Split texts into ~500-token segments with 50-token overlap
2. **Embedding**: Generate vectors using text-embedding-004 or equivalent
3. **Storage**: Store in vector DB with metadata (author, book, page)
4. **Profiling**: Create single expertise vector per author for routing

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test suite
pytest tests/unit/test_semantic_router.py
pytest tests/integration/test_rag_pipeline.py
```

## 📈 Performance Targets

- **Query Latency**: <3s for single author, <5s for panel (achieved)
- **Concurrent Authors**: 5 simultaneous RAG pipelines (implemented)
- **Vector Search**: <200ms per author (achieved)
- **LLM Generation**: <2s per author with streaming (implemented)
- **Cache Hit Rate**: >70% for repeated queries (implemented)

## 🚢 Deployment

**Fully Automated Deployment** via Google Cloud Build:
```bash
git push origin main  # Automatically deploys backend + frontend!
```

The deployment pipeline automatically:
- ✅ Builds and deploys backend to Cloud Run
- ✅ Deploys frontend to Cloud Storage
- ✅ Configures API endpoints
- ✅ Sets up public access
- ✅ Total time: ~6-9 minutes

### Documentation
- **[Automated Deployment Guide](docs/AUTOMATED_DEPLOYMENT.md)** - Full automation setup
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Infrastructure setup
- **[API Documentation](docs/API.md)** - Complete API reference
- **[Architecture](docs/ARCHITECTURE.md)** - System architecture overview
- **[Service Accounts](docs/SERVICE_ACCOUNTS_GUIDE.md)** - Permissions setup
- **[Usage Guide](USAGE.md)** - Detailed usage instructions

## 🤝 Contributing

1. Follow PEP 8 style guidelines
2. Add tests for new features
3. Update documentation
4. Submit PR with clear description

## 📝 License

MIT License - See LICENSE file for details.

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Status**: All 6 implementation phases complete! ✅
- ✅ Phase 1-2: Data acquisition & frontend
- ✅ Phase 3-4: Streaming, caching, telemetry
- ✅ Phase 5-6: Automated deployment & docs
# Production deployment
# Deployment fix
