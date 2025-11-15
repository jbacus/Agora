## Architecture Overview

The Virtual Debate Panel is built as a three-layer system that implements Retrieval-Augmented Generation (RAG) with semantic routing for intelligent author selection.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer (Web UI)                    │
│  • HTML/CSS/JavaScript interface                            │
│  • Real-time query submission                               │
│  • Response visualization                                   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/JSON
┌────────────────────────┴────────────────────────────────────┐
│                    API Layer (FastAPI)                      │
│  • REST endpoints (/api/query, /api/authors)               │
│  • Request validation                                       │
│  • Error handling                                           │
│  • CORS & authentication                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│              Logic Layer (Semantic Router)                  │
│  • Query vectorization                                      │
│  • Cosine similarity calculation                            │
│  • Author panel selection                                   │
│  • Response aggregation                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│           Processing Layer (RAG Pipeline)                   │
│  • Chunk retrieval from vector DB                          │
│  • Context construction                                     │
│  • LLM prompt generation                                    │
│  • Concurrent author response generation                    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                 Data Layer (Storage)                        │
│  • Vector database (ChromaDB/Pinecone)                     │
│  • Text chunk embeddings                                    │
│  • Author expertise profiles                                │
│  • Metadata & source attribution                            │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Data Layer

**Purpose**: Store and retrieve embeddings efficiently

**Components**:
- `vector_db.py`: Abstract interface with ChromaDB and Pinecone implementations
- `embeddings.py`: Embedding generation using Gemini, OpenAI, or local models
- `models.py`: Pydantic data models for type safety

**Key Operations**:
- Insert text chunks with embeddings
- Store author expertise profiles
- Perform similarity search (cosine distance)
- Filter by author for targeted retrieval

**Vector Database Schema**:

```
text_chunks collection:
  - id: string (unique chunk identifier)
  - embedding: float[] (768-3072 dimensions)
  - author_id: string
  - text: string (original text)
  - metadata: dict (book, chapter, page, etc.)

author_profiles collection:
  - id: string (author identifier)
  - embedding: float[] (expertise representation)
  - metadata: dict (name, domains, bio)
```

### 2. Processing Layer

**Purpose**: Generate contextual responses using RAG

**Components**:
- `llm_client.py`: Unified interface for multiple LLM providers
- `rag_pipeline.py`: Retrieval and generation orchestration
- `prompts.py`: System prompt management with author voices

**RAG Pipeline Flow**:

```
1. Query Embedding
   ├─ Input: User query text
   └─ Output: Query vector (768-3072 dimensions)

2. Chunk Retrieval (per author)
   ├─ Input: Query vector + author_id
   ├─ Operation: Cosine similarity search
   └─ Output: Top-K chunks (default: 5)

3. Context Construction
   ├─ Input: Retrieved chunks
   ├─ Operation: Format with metadata
   └─ Output: Contextual prompt

4. LLM Generation
   ├─ Input: System prompt + User prompt + Context
   ├─ Operation: LLM inference
   └─ Output: Author response (max 3 paragraphs)
```

**Prompt Structure**:

```
System Prompt:
  - Author identity and role
  - Voice characteristics
  - Key vocabulary and tone
  - 3-paragraph constraint

User Prompt:
  - Retrieved context from author's works
  - User's original question
  - Instructions for response format
```

### 3. Logic Layer

**Purpose**: Intelligent author selection and response coordination

**Components**:
- `semantic_router.py`: Query-to-author matching
- `response_aggregator.py`: Multi-author response formatting

**Semantic Routing Algorithm**:

```python
def select_authors(query: Query) -> AuthorSelectionResult:
    # 1. Embed query
    query_vector = embed(query.text)

    # 2. Calculate similarities with all author profiles
    similarities = {
        author_id: cosine_similarity(query_vector, author_profile)
        for author_id, author_profile in author_profiles.items()
    }

    # 3. Apply threshold filtering
    above_threshold = {
        author_id: score
        for author_id, score in similarities.items()
        if score >= threshold
    }

    # 4. Apply constraints
    if len(above_threshold) >= min_authors:
        selected = top_k(above_threshold, max_authors)
        method = "threshold"
    else:
        # Fallback to top-K
        selected = top_k(similarities, min_authors)
        method = "fallback"

    return AuthorSelectionResult(
        selected_authors=list(selected.keys()),
        similarity_scores=similarities,
        selection_method=method
    )
```

**Selection Methods**:
- **threshold**: All authors above relevance threshold (0.60 default, empirically tested)
- **fallback_top_k**: Top-K authors if threshold not met
- **specified**: User-specified authors (bypasses routing)

### 4. API Layer

**Purpose**: HTTP interface for client applications

**Endpoints**:

```
POST /api/query
  Request:
    {
      "text": "What is the meaning of life?",
      "max_authors": 5,
      "min_authors": 2,
      "relevance_threshold": 0.7,
      "specified_authors": ["marx", "whitman"]  // optional
    }

  Response:
    {
      "query_text": "What is the meaning of life?",
      "authors": [
        {
          "author_id": "marx",
          "author_name": "Karl Marx",
          "response_text": "...",
          "relevance_score": 0.85,
          "generation_time_ms": 1234.5
        }
      ],
      "total_time_ms": 3500.0,
      "selection_method": "threshold",
      "author_count": 3
    }

GET /api/authors
  Response:
    {
      "authors": [
        {
          "id": "marx",
          "name": "Karl Marx",
          "expertise_domains": ["political_economy", "capitalism"],
          "bio": "...",
          "major_works": ["Capital", "The Communist Manifesto"]
        }
      ],
      "total": 3
    }

GET /api/authors/{author_id}
  Response: Detailed author profile

GET /api/rankings?query=...
  Response: All authors ranked by relevance
```

## Concurrency Model

The system uses Python's `asyncio` for concurrent author response generation:

```python
async def generate_responses_concurrent(
    query: Query,
    authors: List[Author],
    query_embedding: List[float]
) -> List[AuthorResponse]:
    # Create tasks for each author
    tasks = [
        generate_response_async(query, author, query_embedding)
        for author in authors
    ]

    # Execute concurrently
    responses = await asyncio.gather(*tasks)

    return responses
```

**Benefits**:
- 5 authors process in parallel (~2s total vs ~10s sequential)
- Better resource utilization
- Lower latency for user

## Data Flow Example

**Query**: "What is the meaning of life?"

```
1. User submits query via web UI
   └─> POST /api/query {"text": "What is the meaning of life?"}

2. API validates request and calls SemanticRouter
   └─> SemanticRouter.select_authors(query)

3. SemanticRouter embeds query and calculates similarities
   ├─ Query vector: [0.23, -0.15, 0.42, ...]
   ├─ Marx similarity: 0.45 (below 0.60 threshold)
   ├─ Whitman similarity: 0.78 (above threshold)
   └─ Manson similarity: 0.82 (above threshold)

   Selected: [Whitman, Manson] (threshold method)

4. RAG Pipeline generates responses concurrently

   For Whitman:
   ├─ Retrieve top-5 chunks from "Leaves of Grass"
   ├─ Construct context
   ├─ Call LLM with Whitman system prompt
   └─ Response: "Life is the grand song of existence..."

   For Manson:
   ├─ Retrieve top-5 chunks from "Subtle Art"
   ├─ Construct context
   ├─ Call LLM with Manson system prompt
   └─ Response: "Look, the meaning of life is whatever..."

5. ResponseAggregator formats results
   └─> Sorted by relevance, formatted for UI

6. API returns JSON response
   └─> Client displays debate panel
```

## Scalability Considerations

### Current Implementations & Optimizations
- ✅ Concurrent LLM calls for multiple authors (asyncio)
- ✅ Response caching with configurable TTL (default 3600s)
- ✅ Telemetry tracking for performance metrics
- ✅ Streaming support via Server-Sent Events
- Local vector database (ChromaDB) - single machine deployment
- Async/await for parallel processing

### Scaling Strategies

**Horizontal Scaling**:
- Deploy multiple API instances behind load balancer
- Use Pinecone (cloud vector DB) for distributed storage
- Implement Redis for response caching

**Performance Optimization (Implemented)**:
- ✅ Pre-computed author expertise profiles
- ✅ Response caching with semantic similarity
- ✅ Streaming responses via SSE (Server-Sent Events)
- ✅ Concurrent request processing with asyncio
- ✅ Telemetry and analytics tracking

**Future Enhancements**:
- WebSocket support for bi-directional streaming
- Advanced cache strategies (semantic similarity-based)
- Per-user rate limiting and quotas
- Real-time analytics dashboard
- Multi-region deployment
- Database connection pooling

## Security

**Current Implementation**:
- CORS configuration for allowed origins
- Input validation via Pydantic
- API key authentication (optional)

**Production Requirements**:
- HTTPS/TLS encryption
- API key rotation
- Rate limiting per IP/user
- Input sanitization for XSS
- Audit logging

## Monitoring

**Health Checks**:
```
GET /api/health
{
  "status": "healthy",
  "components": {
    "vector_db": "connected",
    "llm": "connected",
    "embeddings": "connected"
  }
}
```

**Metrics to Track**:
- Query latency (p50, p95, p99)
- LLM token usage
- Vector DB query time
- Error rates by endpoint
- Author selection distribution

## Technology Stack

**Backend**:
- Python 3.10+
- FastAPI (async web framework)
- Pydantic (data validation)
- ChromaDB / Pinecone (vector database)

**LLM Providers**:
- Google Gemini 2.0 Flash Exp (default, recommended)
- OpenAI GPT-4 Turbo
- Anthropic Claude 3 Opus

**Embeddings**:
- Google text-embedding-004 (768d)
- OpenAI text-embedding-3-large (3072d)
- Local SentenceTransformers (384d)

**Frontend**:
- Vanilla JavaScript (no framework)
- HTML5 / CSS3
- Fetch API for HTTP

## Configuration Management

All configuration via environment variables (`.env` file):

```bash
# LLM
LLM_PROVIDER=gemini
GEMINI_API_KEY=...

# Vector DB
VECTOR_DB=chromadb
CHROMA_PERSIST_DIR=./data/chroma_db

# Semantic Router
RELEVANCE_THRESHOLD=0.7
MIN_AUTHORS=2
MAX_AUTHORS=5

# RAG Pipeline
TOP_K_CHUNKS=5
MAX_RESPONSE_TOKENS=300
LLM_TEMPERATURE=0.7

# Cache Configuration
ENABLE_CACHE=true
CACHE_TTL_SECONDS=3600
```

See [README.md](../README.md) for full configuration reference.
