# API Reference

Complete API documentation for the Virtual Debate Panel REST API.

## Base URL

```
http://localhost:8000
```

## Authentication

API authentication is optional and controlled via environment variables:

```bash
ENABLE_AUTH=true
API_KEY=your_secret_key
```

When enabled, include API key in headers:

```
Authorization: Bearer your_secret_key
```

## Endpoints

### Root Endpoint

Get API information and available endpoints.

**Request**:
```
GET /
```

**Response**:
```json
{
  "name": "Virtual Debate Panel API",
  "version": "0.1.0",
  "description": "Multi-perspective chat application with RAG-based author responses",
  "endpoints": {
    "query": "/api/query",
    "authors": "/api/authors",
    "health": "/api/health",
    "docs": "/docs"
  }
}
```

---

### Query Debate Panel

Submit a query to the Virtual Debate Panel and receive responses from multiple authors.

**Request**:
```
POST /api/query
Content-Type: application/json

{
  "text": "What is the meaning of life?",
  "specified_authors": null,
  "max_authors": 5,
  "min_authors": 2,
  "relevance_threshold": 0.7
}
```

**Parameters**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | Yes | - | The user's question (1-5000 characters) |
| `specified_authors` | string[] | No | null | Specific author IDs to query. If null, uses semantic routing. |
| `max_authors` | integer | No | 5 | Maximum number of authors to include (2-10) |
| `min_authors` | integer | No | 2 | Minimum number of authors to include (1-5) |
| `relevance_threshold` | float | No | 0.7 | Minimum similarity score for author selection (0.0-1.0) |

**Response** (200 OK):
```json
{
  "query_text": "What is the meaning of life?",
  "authors": [
    {
      "author_id": "whitman",
      "author_name": "Walt Whitman",
      "response_text": "The meaning of life, my friend, lies not in some distant abstraction but in the very grass beneath your feet...\n\nI see life as a grand cosmic song, where each individual voice contributes to the democratic chorus of existence...\n\nEmbrace your contradictions! Contain multitudes! For the meaning emerges through lived experience...",
      "relevance_score": 0.82,
      "generation_time_ms": 2341.5
    },
    {
      "author_id": "baudelaire",
      "author_name": "Mark Baudelaire",
      "response_text": "Look, the whole 'meaning of life' question is kind of bullshit. You're asking the wrong question...\n\nThe meaning of life is whatever values you choose to give a fuck about. That's it. No cosmic purpose handed down from above...\n\nStop seeking some universal answer and start taking responsibility for creating your own meaning through the struggles you choose to endure.",
      "relevance_score": 0.78,
      "generation_time_ms": 2156.3
    }
  ],
  "total_time_ms": 3789.2,
  "selection_method": "threshold",
  "author_count": 2
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `query_text` | string | Original query text |
| `authors` | AuthorResponse[] | Array of author responses |
| `total_time_ms` | float | Total processing time in milliseconds |
| `selection_method` | string | How authors were selected ("threshold", "fallback_top_k", "specified") |
| `author_count` | integer | Number of authors in response |

**AuthorResponse Object**:

| Field | Type | Description |
|-------|------|-------------|
| `author_id` | string | Author identifier (e.g., "marx", "whitman") |
| `author_name` | string | Full name of author |
| `response_text` | string | Generated response (max 3 paragraphs) |
| `relevance_score` | float | Semantic similarity to query (0.0-1.0) |
| `generation_time_ms` | float | Time taken to generate this response |

**Error Responses**:

```json
// 400 Bad Request - Invalid input
{
  "error": "Validation error",
  "detail": "Query text cannot be empty",
  "code": "VALIDATION_ERROR"
}

// 404 Not Found - No relevant authors
{
  "error": "No authors found",
  "detail": "No relevant authors found for query",
  "code": "NO_AUTHORS"
}

// 500 Internal Server Error
{
  "error": "Internal server error",
  "detail": "Failed to generate responses",
  "code": "GENERATION_ERROR"
}
```

---

### List Authors

Get all available authors with their profiles.

**Request**:
```
GET /api/authors
```

**Response** (200 OK):
```json
{
  "authors": [
    {
      "id": "marx",
      "name": "Karl Marx",
      "expertise_domains": [
        "political_economy",
        "capitalism",
        "class_struggle",
        "labor_theory_of_value"
      ],
      "bio": "Karl Marx (1818-1883) was a German philosopher, economist, historian, and revolutionary socialist...",
      "major_works": [
        "Das Kapital (1867)",
        "The Communist Manifesto (1848)",
        "The German Ideology (1846)"
      ]
    },
    {
      "id": "whitman",
      "name": "Walt Whitman",
      "expertise_domains": [
        "poetry",
        "democracy",
        "transcendentalism",
        "american_identity"
      ],
      "bio": "Walt Whitman (1819-1892) was an American poet, essayist, and journalist...",
      "major_works": [
        "Leaves of Grass (1855)",
        "Democratic Vistas (1871)"
      ]
    },
    {
      "id": "baudelaire",
      "name": "Mark Baudelaire",
      "expertise_domains": [
        "psychology",
        "self_help",
        "personal_development",
        "values"
      ],
      "bio": "Mark Baudelaire is a contemporary American author and blogger...",
      "major_works": [
        "The Subtle Art of Not Giving a F*ck (2016)",
        "Everything Is F*cked (2019)"
      ]
    }
  ],
  "total": 3
}
```

---

### Get Author Details

Get detailed information about a specific author.

**Request**:
```
GET /api/authors/{author_id}
```

**Path Parameters**:
- `author_id`: Author identifier (e.g., "marx", "whitman", "baudelaire")

**Response** (200 OK):
```json
{
  "id": "marx",
  "name": "Karl Marx",
  "expertise_domains": [
    "political_economy",
    "capitalism",
    "class_struggle"
  ],
  "voice_characteristics": {
    "tone": "analytical, critical, revolutionary",
    "vocabulary": "dialectical, materialist, proletarian",
    "perspective": "class-based economic analysis",
    "style_notes": "Rigorous theoretical analysis grounded in material conditions"
  },
  "bio": "Karl Marx (1818-1883) was a German philosopher, economist...",
  "major_works": [
    "Das Kapital (1867)",
    "The Communist Manifesto (1848)"
  ]
}
```

**Error Response** (404 Not Found):
```json
{
  "error": "Author not found",
  "detail": "Author not found: invalid_id",
  "code": "AUTHOR_NOT_FOUND"
}
```

---

### Get Author Rankings

Get all authors ranked by relevance to a specific query (useful for debugging semantic routing).

**Request**:
```
GET /api/rankings?query=What%20is%20capitalism
```

**Query Parameters**:
- `query`: The query text to rank authors against

**Response** (200 OK):
```json
{
  "query": "What is capitalism?",
  "rankings": [
    {
      "author_id": "marx",
      "similarity_score": 0.89
    },
    {
      "author_id": "baudelaire",
      "similarity_score": 0.42
    },
    {
      "author_id": "whitman",
      "similarity_score": 0.31
    }
  ]
}
```

---

### Health Check

Check API and component health status.

**Request**:
```
GET /api/health
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "components": {
    "vector_db": "connected",
    "llm": "connected",
    "embeddings": "connected"
  }
}
```

**Response** (degraded):
```json
{
  "status": "degraded",
  "version": "0.1.0",
  "components": {
    "vector_db": "connected",
    "llm": "error: timeout",
    "embeddings": "connected"
  }
}
```

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `NO_AUTHORS` | 400 | No relevant authors found |
| `AUTHOR_NOT_FOUND` | 404 | Requested author does not exist |
| `GENERATION_ERROR` | 500 | Failed to generate responses |
| `DATABASE_ERROR` | 500 | Vector database error |
| `LLM_ERROR` | 500 | LLM provider error |

---

## Rate Limiting

Rate limiting is configured via environment variables:

```bash
RATE_LIMIT_PER_MINUTE=30
```

When rate limit is exceeded:

**Response** (429 Too Many Requests):
```json
{
  "error": "Rate limit exceeded",
  "detail": "Maximum 30 requests per minute",
  "code": "RATE_LIMIT"
}
```

---

## Example cURL Requests

### Query with automatic author selection

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is the meaning of life?",
    "max_authors": 3,
    "relevance_threshold": 0.7
  }'
```

### Query specific authors

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is democracy?",
    "specified_authors": ["marx", "whitman"]
  }'
```

### List all authors

```bash
curl http://localhost:8000/api/authors
```

### Get author rankings

```bash
curl "http://localhost:8000/api/rankings?query=What+is+capitalism"
```

---

## JavaScript/TypeScript Example

```typescript
const API_BASE_URL = 'http://localhost:8000/api';

interface QueryRequest {
  text: string;
  specified_authors?: string[];
  max_authors?: number;
  min_authors?: number;
  relevance_threshold?: number;
}

interface AuthorResponse {
  author_id: string;
  author_name: string;
  response_text: string;
  relevance_score: number;
  generation_time_ms: number;
}

interface DebatePanelResponse {
  query_text: string;
  authors: AuthorResponse[];
  total_time_ms: number;
  selection_method: string;
  author_count: number;
}

async function queryDebatePanel(
  query: QueryRequest
): Promise<DebatePanelResponse> {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(query),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Request failed');
  }

  return await response.json();
}

// Usage
const result = await queryDebatePanel({
  text: 'What is the meaning of life?',
  max_authors: 3,
  relevance_threshold: 0.7,
});

console.log(`Got ${result.author_count} responses`);
result.authors.forEach(author => {
  console.log(`${author.author_name}: ${author.response_text}`);
});
```

---

## Python Example

```python
import requests
from typing import List, Optional

API_BASE_URL = "http://localhost:8000/api"

def query_debate_panel(
    text: str,
    specified_authors: Optional[List[str]] = None,
    max_authors: int = 5,
    min_authors: int = 2,
    relevance_threshold: float = 0.7
) -> dict:
    """Query the Virtual Debate Panel."""
    payload = {
        "text": text,
        "max_authors": max_authors,
        "min_authors": min_authors,
        "relevance_threshold": relevance_threshold
    }

    if specified_authors:
        payload["specified_authors"] = specified_authors

    response = requests.post(
        f"{API_BASE_URL}/query",
        json=payload
    )

    response.raise_for_status()
    return response.json()

# Usage
result = query_debate_panel(
    text="What is the meaning of life?",
    max_authors=3
)

print(f"Got {result['author_count']} responses")
for author in result['authors']:
    print(f"\n{author['author_name']}:")
    print(author['response_text'])
```

---

## Interactive API Documentation

FastAPI provides interactive API documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to:
- Explore all endpoints
- Test API calls directly from the browser
- View request/response schemas
- See example payloads
