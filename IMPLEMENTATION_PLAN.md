# Agora Virtual Debate Panel - Implementation Plan

## Overview

This document outlines the complete implementation plan for building and deploying the Agora Virtual Debate Panel application. The plan is organized into 6 phases, from data acquisition to production deployment.

**Timeline:** 4-6 weeks (part-time) | 2-3 weeks (full-time)

**Goal:** A fully functional multi-author debate panel with Marx, Whitman, and Manson responding to user queries using RAG.

**Note:** This implementation plan is now largely complete. Most phases have been finished. See project status below.

---

## 📊 Project Status

### ✅ Completed (All Core Features)
- [x] CI/CD pipeline configuration (Cloud Build)
- [x] Dockerfile and docker-compose setup
- [x] Google Cloud infrastructure scripts
- [x] Service account configuration
- [x] Deployment documentation
- [x] Backend API implementation (FastAPI)
- [x] RAG pipeline implementation
- [x] Semantic router implementation (0.60 threshold)
- [x] Vector database integration (ChromaDB/Pinecone)
- [x] Multi-LLM support (Gemini/OpenAI/Anthropic)
- [x] Frontend UI implementation (HTML/JS/CSS)
- [x] Streaming support (Server-Sent Events)
- [x] Response caching system
- [x] Telemetry and analytics
- [x] Production deployment (automated)
- [x] Full-stack automated deployment pipeline

### ⚠️ Data Ingestion (Manual Step)
- [ ] Acquire and ingest author texts (requires manual data collection)
- [ ] Generate author expertise profiles

**Note:** The application infrastructure is complete. Data ingestion is the only remaining manual step that requires source texts to be obtained and processed.

---

## Phase 1: Data Acquisition & Ingestion (Week 1)

**Goal:** Acquire source texts and ingest them into the vector database

### 1.1 Acquire Author Texts

**Tasks:**

#### Marx Texts (Public Domain - Free)
- [ ] Download from Project Gutenberg
  - Capital Vol. 1: https://www.gutenberg.org/ebooks/61
  - Communist Manifesto: https://www.gutenberg.org/ebooks/61
  - Wage Labour and Capital: https://www.gutenberg.org/ebooks/8002
  - Theses on Feuerbach: https://www.marxists.org/archive/marx/works/1845/theses/
- [ ] Convert to plain text (.txt format)
- [ ] Save to `data/raw/marx/`

**Commands:**
```bash
mkdir -p data/raw/marx

# Capital Vol. 1
wget https://www.gutenberg.org/files/61/61-0.txt -O data/raw/marx/capital_vol1.txt

# Communist Manifesto
wget https://www.gutenberg.org/cache/epub/61/pg61.txt -O data/raw/marx/communist_manifesto.txt

# Clean up Project Gutenberg headers/footers (manual step)
# Remove "*** START/END OF THE PROJECT GUTENBERG EBOOK ***" sections
```

#### Whitman Texts (Public Domain - Free)
- [ ] Download from Project Gutenberg
  - Leaves of Grass: https://www.gutenberg.org/ebooks/1322
  - Democratic Vistas: https://www.gutenberg.org/ebooks/8813
  - Specimen Days: https://www.gutenberg.org/ebooks/8892
- [ ] Convert to plain text
- [ ] Save to `data/raw/whitman/`

**Commands:**
```bash
mkdir -p data/raw/whitman

# Leaves of Grass (complete edition)
wget https://www.gutenberg.org/files/1322/1322-0.txt -O data/raw/whitman/leaves_of_grass.txt

# Democratic Vistas
wget https://www.gutenberg.org/files/8813/8813-0.txt -O data/raw/whitman/democratic_vistas.txt

# Specimen Days
wget https://www.gutenberg.org/files/8892/8892-0.txt -O data/raw/whitman/specimen_days.txt
```

#### Mark Manson Texts (Copyrighted - Requires Purchase)
- [ ] Obtain legally (purchase books or use authorized sources)
  - The Subtle Art of Not Giving a F*ck
  - Everything Is F*cked: A Book About Hope
  - Models: Attract Women Through Honesty
- [ ] Convert to plain text (ensure compliance with copyright)
- [ ] Save to `data/raw/manson/`

**Note:** Mark Manson's works are under copyright. You must own or have legal access to these texts.

**Commands:**
```bash
mkdir -p data/raw/manson

# After legally obtaining texts, place them in data/raw/manson/
# Example filenames:
# - data/raw/manson/subtle_art.txt
# - data/raw/manson/everything_is_fucked.txt
# - data/raw/manson/models.txt
```

**Deliverables:**
- `data/raw/marx/` contains 3 text files (~500KB total)
- `data/raw/whitman/` contains 3 text files (~400KB total)
- `data/raw/baudelaire/` contains 2 text files (~300KB total)

**Time:** 2-3 hours

---

### 1.2 Clean and Prepare Text Data

**Tasks:**

- [ ] Create preprocessing script
- [ ] Remove Project Gutenberg headers/footers
- [ ] Fix encoding issues (UTF-8)
- [ ] Split very large files into chapters
- [ ] Verify text quality

**Script to Create:**
```python
# scripts/clean_texts.py
import re
from pathlib import Path

def clean_gutenberg_text(text: str) -> str:
    """Remove Project Gutenberg boilerplate."""
    # Remove header
    text = re.sub(r'\*\*\* START OF.*?\*\*\*', '', text, flags=re.DOTALL)
    # Remove footer
    text = re.sub(r'\*\*\* END OF.*?\*\*\*', '', text, flags=re.DOTALL)
    # Remove multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def clean_author_texts(author_dir: Path):
    """Clean all texts for an author."""
    for txt_file in author_dir.glob('*.txt'):
        print(f"Cleaning {txt_file.name}...")
        text = txt_file.read_text(encoding='utf-8')
        cleaned = clean_gutenberg_text(text)
        txt_file.write_text(cleaned, encoding='utf-8')

if __name__ == '__main__':
    for author in ['marx', 'whitman', 'baudelaire']:
        author_dir = Path(f'data/raw/{author}')
        if author_dir.exists():
            clean_author_texts(author_dir)
```

**Commands:**
```bash
python scripts/clean_texts.py
```

**Deliverables:**
- Cleaned text files in `data/raw/`
- No encoding errors
- No boilerplate text

**Time:** 1 hour

---

### 1.3 Ingest Texts into Vector Database

**Tasks:**

- [ ] Set up environment variables (.env file)
- [ ] Initialize vector database
- [ ] Run ingestion for each author
- [ ] Generate author expertise profiles
- [ ] Verify ingestion success

**Commands:**
```bash
# 1. Create .env file
cp .env.example .env
nano .env  # Add GEMINI_API_KEY

# 2. Initialize database
python scripts/init_database.py

# 3. Ingest each author
python scripts/ingest_author.py --author marx
python scripts/ingest_author.py --author whitman
python scripts/ingest_author.py --author baudelaire

# 4. Generate expertise profiles
python scripts/create_expertise_profiles.py

# 5. Verify
python -c "
from src.data import get_vector_db
from config.settings import settings

db = get_vector_db(**settings.get_vector_db_config())
db.initialize()

# Check chunk counts
for author in ['marx', 'whitman', 'baudelaire']:
    collection = db.client.get_collection(f'author_{author}')
    count = collection.count()
    print(f'{author}: {count} chunks')
"
```

**Expected Output:**
```
marx: ~1200 chunks
whitman: ~900 chunks
baudelaire: ~500 chunks (or more if using blog posts)
```

**Deliverables:**
- Vector database populated with ~2500+ text chunks
- Author expertise profiles created
- All three authors queryable

**Time:** 2-3 hours (including API calls for embeddings)

**Cost Estimate:**
- Gemini embeddings: ~$0.01-0.05 (text-embedding-004 is cheap)

---

### 1.4 Test RAG Pipeline

**Tasks:**

- [ ] Test single-author queries
- [ ] Test multi-author selection
- [ ] Verify response quality
- [ ] Test semantic routing

**Test Script:**
```python
# scripts/test_rag.py
import asyncio
from src.api.main import services

async def test_queries():
    """Test RAG pipeline with various queries."""

    test_queries = [
        # Should route to Marx
        "What is the relationship between labor and capital?",
        "Explain class struggle",

        # Should route to Whitman
        "What is the meaning of democracy?",
        "How should we celebrate the individual?",

        # Should route to Baudelaire
        "How do I stop caring what others think?",
        "What makes a good life?",

        # Should route to multiple authors
        "What is freedom?",
        "How should we live our lives?"
    ]

    semantic_router = services['semantic_router']
    rag_pipeline = services['rag_pipeline']

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)

        # Get selected authors
        selected = await semantic_router.select_authors(query)
        print(f"Selected: {[a.name for a in selected]}")

        # Get responses
        for author in selected[:1]:  # Just test first author
            response = await rag_pipeline.generate_response(author, query)
            print(f"\n{author.name}:")
            print(response.response[:200] + "...")

if __name__ == '__main__':
    asyncio.run(test_queries())
```

**Commands:**
```bash
# Start API server
uvicorn src.api.main:app --reload

# In another terminal, test queries
python scripts/test_rag.py
```

**Success Criteria:**
- Marx responds to questions about capitalism, class struggle
- Whitman responds to questions about democracy, individualism
- Baudelaire responds to questions about personal growth, psychology
- Multi-author queries select relevant authors (threshold-based)
- Responses are coherent and relevant (3 paragraphs max)

**Deliverables:**
- Working RAG pipeline
- Verified author selection
- Quality responses

**Time:** 2 hours

---

## Phase 2: Frontend Development (Week 2)

**Goal:** Build a functional web UI for the debate panel

### 2.1 Basic UI Structure

**Tasks:**

- [ ] Create HTML structure
- [ ] Add Tailwind CSS styling
- [ ] Implement responsive layout
- [ ] Add dark mode toggle

**Files to Create:**

#### `src/ui/index.html`
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agora - Virtual Debate Panel</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="styles.css">
</head>
<body class="bg-gray-50 dark:bg-gray-900">
    <div id="app" class="container mx-auto px-4 py-8 max-w-6xl">
        <!-- Header -->
        <header class="mb-8">
            <h1 class="text-4xl font-bold text-gray-900 dark:text-white">
                Agora Virtual Debate Panel
            </h1>
            <p class="text-gray-600 dark:text-gray-400 mt-2">
                Ask a question and hear from great thinkers
            </p>
        </header>

        <!-- Query Input -->
        <div id="query-section" class="mb-8">
            <textarea
                id="query-input"
                placeholder="Ask a question..."
                class="w-full p-4 border rounded-lg resize-none"
                rows="3"
            ></textarea>

            <div class="flex gap-4 mt-4">
                <button id="submit-btn" class="btn-primary">
                    Ask the Panel
                </button>
                <button id="clear-btn" class="btn-secondary">
                    Clear
                </button>
            </div>
        </div>

        <!-- Selected Authors -->
        <div id="selected-authors" class="mb-8 hidden">
            <h3 class="text-lg font-semibold mb-2">Responding Authors:</h3>
            <div id="authors-list" class="flex gap-2"></div>
        </div>

        <!-- Responses -->
        <div id="responses" class="space-y-6">
            <!-- Author responses will appear here -->
        </div>

        <!-- Loading State -->
        <div id="loading" class="hidden text-center py-8">
            <div class="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
            <p class="mt-4 text-gray-600">Consulting the panel...</p>
        </div>
    </div>

    <script src="app.js"></script>
</body>
</html>
```

#### `src/ui/styles.css`
```css
:root {
    --color-primary: #3B82F6;
    --color-secondary: #6B7280;
}

.btn-primary {
    @apply bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition;
}

.btn-secondary {
    @apply bg-gray-200 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-300 transition;
}

.author-card {
    @apply bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border-l-4;
}

.author-card.marx {
    @apply border-red-500;
}

.author-card.whitman {
    @apply border-blue-500;
}

.author-card.baudelaire {
    @apply border-purple-500;
}
```

**Deliverables:**
- Basic HTML structure
- Styled with Tailwind CSS
- Responsive design
- Dark mode support

**Time:** 3-4 hours

---

### 2.2 JavaScript Application Logic

**Tasks:**

- [ ] Implement API client
- [ ] Handle form submission
- [ ] Display author selection
- [ ] Render responses
- [ ] Add loading states
- [ ] Error handling

**File to Create:**

#### `src/ui/app.js`
```javascript
// API Configuration
const API_URL = 'http://localhost:8000';

// DOM Elements
const queryInput = document.getElementById('query-input');
const submitBtn = document.getElementById('submit-btn');
const clearBtn = document.getElementById('clear-btn');
const selectedAuthorsDiv = document.getElementById('selected-authors');
const authorsListDiv = document.getElementById('authors-list');
const responsesDiv = document.getElementById('responses');
const loadingDiv = document.getElementById('loading');

// State
let currentQuery = '';

// Event Listeners
submitBtn.addEventListener('click', handleSubmit);
clearBtn.addEventListener('click', handleClear);
queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) handleSubmit();
});

// API Functions
async function submitQuery(query) {
    const response = await fetch(`${API_URL}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            query,
            max_authors: 5,
            relevance_threshold: 0.7
        })
    });

    if (!response.ok) throw new Error('Query failed');
    return response.json();
}

// UI Functions
function showLoading() {
    loadingDiv.classList.remove('hidden');
    responsesDiv.innerHTML = '';
    selectedAuthorsDiv.classList.add('hidden');
}

function hideLoading() {
    loadingDiv.classList.add('hidden');
}

function displayAuthors(authors) {
    authorsListDiv.innerHTML = authors.map(author => `
        <span class="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
            ${author.name}
        </span>
    `).join('');
    selectedAuthorsDiv.classList.remove('hidden');
}

function displayResponses(responses) {
    responsesDiv.innerHTML = responses.map(response => `
        <div class="author-card ${response.author_id}">
            <div class="flex items-center gap-3 mb-4">
                <div class="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center">
                    <span class="text-xl">${getAuthorEmoji(response.author_id)}</span>
                </div>
                <div>
                    <h3 class="font-bold text-lg">${response.author_name}</h3>
                    <p class="text-sm text-gray-500">
                        Relevance: ${(response.relevance_score * 100).toFixed(0)}%
                    </p>
                </div>
            </div>
            <div class="prose dark:prose-invert">
                ${formatResponse(response.response)}
            </div>
            ${response.sources.length > 0 ? `
                <details class="mt-4">
                    <summary class="cursor-pointer text-sm text-gray-500">
                        View sources (${response.sources.length})
                    </summary>
                    <ul class="mt-2 text-sm text-gray-600 space-y-1">
                        ${response.sources.map(s => `
                            <li>• ${s.source} (p. ${s.metadata.page || 'N/A'})</li>
                        `).join('')}
                    </ul>
                </details>
            ` : ''}
        </div>
    `).join('');
}

function getAuthorEmoji(authorId) {
    const emojis = {
        'marx': '🔨',
        'whitman': '🌿',
        'baudelaire': '💪'
    };
    return emojis[authorId] || '📚';
}

function formatResponse(text) {
    // Convert paragraphs to HTML
    return text.split('\n\n').map(p => `<p>${p}</p>`).join('');
}

// Event Handlers
async function handleSubmit() {
    const query = queryInput.value.trim();
    if (!query) return;

    currentQuery = query;
    submitBtn.disabled = true;
    showLoading();

    try {
        const data = await submitQuery(query);
        hideLoading();
        displayAuthors(data.selected_authors);
        displayResponses(data.responses);
    } catch (error) {
        hideLoading();
        responsesDiv.innerHTML = `
            <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                <p class="text-red-800">Error: ${error.message}</p>
            </div>
        `;
    } finally {
        submitBtn.disabled = false;
    }
}

function handleClear() {
    queryInput.value = '';
    responsesDiv.innerHTML = '';
    selectedAuthorsDiv.classList.add('hidden');
    currentQuery = '';
}

// Initialize
console.log('Agora Virtual Debate Panel loaded');
```

**Deliverables:**
- Functional query submission
- Author selection display
- Response rendering with formatting
- Loading states
- Error handling

**Time:** 4-5 hours

---

### 2.3 Deploy Frontend to Cloud Storage

**Tasks:**

- [ ] Create Cloud Storage bucket (already done in infra setup)
- [ ] Upload frontend files
- [ ] Configure CORS for API access
- [ ] Test frontend → backend communication

**Commands:**
```bash
# Upload frontend files
gsutil -m rsync -r -d src/ui/ gs://YOUR_PROJECT_ID-agora-frontend/

# Set CORS on backend Cloud Run service
gcloud run services update agora-backend \
  --region=us-central1 \
  --set-env-vars="CORS_ORIGINS=https://storage.googleapis.com,http://YOUR_PROJECT_ID-agora-frontend.storage.googleapis.com"

# Get frontend URL
echo "Frontend URL: http://YOUR_PROJECT_ID-agora-frontend.storage.googleapis.com/index.html"
```

**Update `src/ui/app.js`:**
```javascript
// Change API_URL based on environment
const API_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://agora-backend-XXX.run.app';  // Your Cloud Run URL
```

**Deliverables:**
- Frontend deployed to Cloud Storage
- CORS configured correctly
- Frontend can communicate with backend

**Time:** 1-2 hours

---

## Phase 3: Enhanced Features (Week 3)

**Goal:** Add streaming responses, caching, and multi-panel support

### 3.1 Streaming Responses (SSE)

**Tasks:**

- [ ] Add streaming endpoint to backend
- [ ] Implement Server-Sent Events in frontend
- [ ] Display responses as they arrive
- [ ] Handle connection errors

**Backend Update:**
```python
# src/api/routes.py - Add streaming endpoint

from fastapi.responses import StreamingResponse

@router.post("/api/query/stream")
async def query_stream(request: QueryRequest):
    """Stream author responses as they complete."""

    async def generate():
        # 1. Select authors
        selected = await semantic_router.select_authors(request.query)

        yield f"data: {json.dumps({'type': 'authors', 'authors': [a.dict() for a in selected]})}\n\n"

        # 2. Generate responses concurrently
        tasks = [
            rag_pipeline.generate_response(author, request.query)
            for author in selected
        ]

        for coro in asyncio.as_completed(tasks):
            response = await coro
            yield f"data: {json.dumps({'type': 'response', 'data': response.dict()})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Frontend Update:**
```javascript
// src/ui/app.js - Add SSE support

async function submitQueryStreaming(query) {
    const eventSource = new EventSource(
        `${API_URL}/api/query/stream?query=${encodeURIComponent(query)}`
    );

    eventSource.addEventListener('message', (e) => {
        const data = JSON.parse(e.data);

        if (data.type === 'authors') {
            displayAuthors(data.authors);
        } else if (data.type === 'response') {
            appendResponse(data.data);  // Add to page incrementally
        } else if (data.type === 'done') {
            eventSource.close();
        }
    });

    eventSource.addEventListener('error', () => {
        eventSource.close();
        showError('Connection lost');
    });
}
```

**Deliverables:**
- Streaming responses working
- Authors appear as selected
- Responses appear incrementally
- Better perceived performance

**Time:** 4-5 hours

---

### 3.2 Response Caching

**Tasks:**

- [ ] Implement semantic similarity cache
- [ ] Cache responses for identical/similar queries
- [ ] Add cache hit/miss indicators in UI
- [ ] Monitor cache performance

**Implementation:**
```python
# src/utils/response_cache.py

import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from src.data.embeddings import cosine_similarity

class ResponseCache:
    """Cache responses with semantic similarity matching."""

    def __init__(self, ttl_hours: int = 24, similarity_threshold: float = 0.95):
        self.cache = {}  # In-memory cache (use Redis for production)
        self.ttl = timedelta(hours=ttl_hours)
        self.threshold = similarity_threshold

    def get(self, query: str, query_embedding: List[float]) -> Optional[dict]:
        """Get cached response if similar query exists."""

        # Check exact match first
        query_hash = self._hash_query(query)
        if query_hash in self.cache:
            entry = self.cache[query_hash]
            if not self._is_expired(entry):
                return entry['response']

        # Check semantic similarity
        for entry in self.cache.values():
            if self._is_expired(entry):
                continue

            similarity = cosine_similarity(query_embedding, entry['embedding'])
            if similarity >= self.threshold:
                entry['hits'] += 1
                return entry['response']

        return None

    def set(self, query: str, query_embedding: List[float], response: dict):
        """Cache a response."""
        query_hash = self._hash_query(query)
        self.cache[query_hash] = {
            'query': query,
            'embedding': query_embedding,
            'response': response,
            'timestamp': datetime.now(),
            'hits': 0
        }

    def _hash_query(self, query: str) -> str:
        return hashlib.md5(query.lower().encode()).hexdigest()

    def _is_expired(self, entry: dict) -> bool:
        return datetime.now() - entry['timestamp'] > self.ttl
```

**Update Routes:**
```python
# src/api/routes.py

response_cache = ResponseCache()

@router.post("/api/query")
async def query(request: QueryRequest):
    # Generate query embedding
    query_embedding = embedding_provider.embed_query(request.query)

    # Check cache
    cached = response_cache.get(request.query, query_embedding)
    if cached:
        cached['cache_hit'] = True
        return cached

    # Generate new response
    result = await generate_multi_author_response(request)

    # Cache result
    response_cache.set(request.query, query_embedding, result)
    result['cache_hit'] = False

    return result
```

**Deliverables:**
- Response caching working
- 80%+ cache hit rate for repeated queries
- Significant cost reduction

**Time:** 3-4 hours

---

### 3.3 Multi-Panel Support

**Goal:** Support different themed panels (philosophy, politics, self-help)

**Tasks:**

- [ ] Create panel configuration system
- [ ] Add `/api/config` endpoint
- [ ] Dynamic frontend based on panel
- [ ] Panel selector in UI

**Panel Configs:**
```yaml
# config/panels/philosophy.yaml
panel:
  id: philosophy
  name: "Philosophy Panel"
  description: "Great philosophers debate life's questions"

authors:
  - marx
  - nietzsche  # Add later
  - plato      # Add later

ui:
  title: "Philosophy Debate Panel"
  theme:
    primary_color: "#8B4513"
    accent_color: "#D2691E"
```

```yaml
# config/panels/modern-thinkers.yaml
panel:
  id: modern-thinkers
  name: "Modern Thinkers"

authors:
  - marx
  - whitman
  - baudelaire

ui:
  title: "Modern Thinkers Panel"
  theme:
    primary_color: "#3B82F6"
```

**Backend Updates:**
```python
# src/config/panel_loader.py (create)
# src/api/main.py - Add PANEL_ID env var
# src/api/routes.py - Add /api/config endpoint
```

**Deliverables:**
- Multi-panel architecture
- Configuration-driven UI
- Easy to add new panels

**Time:** 4-5 hours

---

## Phase 4: Testing & Quality Assurance (Week 4)

**Goal:** Comprehensive testing and bug fixes

### 4.1 Integration Testing

**Tasks:**

- [ ] Create test suite for API endpoints
- [ ] Test RAG pipeline with various queries
- [ ] Test author selection logic
- [ ] Test edge cases

**Test File:**
```python
# tests/integration/test_full_pipeline.py

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_authors_endpoint():
    response = client.get("/api/authors")
    assert response.status_code == 200
    data = response.json()
    assert len(data["authors"]) >= 3
    assert any(a["id"] == "marx" for a in data["authors"])

def test_query_endpoint_marx():
    response = client.post("/api/query", json={
        "query": "What is class struggle?",
        "max_authors": 3
    })
    assert response.status_code == 200
    data = response.json()
    assert "responses" in data
    # Marx should be selected for this query
    assert any(r["author_id"] == "marx" for r in data["responses"])

def test_query_endpoint_whitman():
    response = client.post("/api/query", json={
        "query": "What is the meaning of democracy?",
        "max_authors": 3
    })
    assert response.status_code == 200
    data = response.json()
    # Whitman should be selected
    assert any(r["author_id"] == "whitman" for r in data["responses"])

def test_query_endpoint_multi_author():
    response = client.post("/api/query", json={
        "query": "What makes a good life?",
        "max_authors": 5
    })
    assert response.status_code == 200
    data = response.json()
    # Should select multiple authors
    assert len(data["responses"]) >= 2

def test_invalid_query():
    response = client.post("/api/query", json={
        "query": "",  # Empty query
        "max_authors": 3
    })
    assert response.status_code == 422  # Validation error
```

**Commands:**
```bash
# Run tests
pytest tests/integration/ -v

# With coverage
pytest tests/integration/ --cov=src --cov-report=html
```

**Deliverables:**
- 20+ integration tests
- 80%+ code coverage
- All tests passing

**Time:** 6-8 hours

---

### 4.2 Performance Testing

**Tasks:**

- [ ] Load testing (100 concurrent requests)
- [ ] Response time benchmarking
- [ ] Memory usage profiling
- [ ] Cost analysis

**Load Test:**
```python
# tests/performance/load_test.py

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import requests

API_URL = "http://localhost:8000"

def send_query():
    start = time.time()
    response = requests.post(f"{API_URL}/api/query", json={
        "query": "What is freedom?",
        "max_authors": 3
    })
    duration = time.time() - start
    return response.status_code, duration

def load_test(concurrent_requests=100):
    with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
        futures = [executor.submit(send_query) for _ in range(concurrent_requests)]
        results = [f.result() for f in futures]

    successful = sum(1 for status, _ in results if status == 200)
    avg_time = sum(duration for _, duration in results) / len(results)

    print(f"Successful: {successful}/{concurrent_requests}")
    print(f"Average time: {avg_time:.2f}s")
    print(f"Max time: {max(duration for _, duration in results):.2f}s")

if __name__ == '__main__':
    load_test(100)
```

**Success Criteria:**
- Handle 100 concurrent requests
- Average response time < 3 seconds
- No out-of-memory errors
- Cache hit rate > 80% for repeated queries

**Time:** 4-5 hours

---

### 4.3 User Acceptance Testing

**Tasks:**

- [ ] Manual testing with real users
- [ ] Collect feedback on response quality
- [ ] Test on different devices/browsers
- [ ] Fix UI/UX issues

**Test Queries:**
```
Philosophy:
- "What is the nature of reality?"
- "How should we live our lives?"
- "What is the meaning of freedom?"

Politics/Economics:
- "Is capitalism just?"
- "What is the role of the state?"
- "How should wealth be distributed?"

Personal Development:
- "How do I find meaning in life?"
- "How do I deal with anxiety?"
- "What makes someone successful?"

Cross-domain:
- "What is happiness?"
- "Is progress possible?"
- "What is human nature?"
```

**Deliverables:**
- 50+ test queries executed
- Feedback collected and addressed
- Major bugs fixed

**Time:** 4-6 hours

---

## Phase 5: Production Deployment (Week 5)

**Goal:** Deploy to production and verify everything works

### 5.1 Pre-Deployment Checklist

**Tasks:**

- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Secrets stored in Secret Manager
- [ ] Cloud Build trigger created
- [ ] Service account permissions verified
- [ ] Data ingested and verified
- [ ] Frontend deployed to Cloud Storage
- [ ] CORS configured
- [ ] Cost limits set (optional)

**Commands:**
```bash
# Run full test suite
./scripts/test_cicd.sh

# Verify all infrastructure
./scripts/setup_gcloud_infrastructure.sh --verify-only

# Check data ingestion
python -c "
from src.data import get_vector_db
from config.settings import settings
db = get_vector_db(**settings.get_vector_db_config())
db.initialize()
print(f'Total chunks: {db.client.count()}')
"
```

**Time:** 2-3 hours

---

### 5.2 Deploy to Production

**Tasks:**

- [ ] Merge feature branch to main
- [ ] Push to trigger Cloud Build
- [ ] Monitor deployment
- [ ] Verify service health
- [ ] Test production endpoints

**Commands:**
```bash
# 1. Merge to main
git checkout main
git merge claude/codebase-review-planning-01KZvbAHm9bPRseQebPY67Gz
git push origin main

# 2. Monitor build
gcloud builds list --ongoing

# 3. View logs
gcloud builds log $(gcloud builds list --limit=1 --format='value(ID)') --stream

# 4. Get service URL
SERVICE_URL=$(gcloud run services describe agora-backend \
  --region=us-central1 \
  --format='value(status.url)')

echo "Service: $SERVICE_URL"

# 5. Test production
curl $SERVICE_URL/api/health | jq '.'
curl $SERVICE_URL/api/authors | jq '.'

# 6. Test query
curl -X POST $SERVICE_URL/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is class struggle?", "max_authors": 3}' \
  | jq '.responses[].author_name'
```

**Expected:**
- Build completes in ~5-10 minutes
- Service deploys successfully
- All endpoints return 200 OK
- Queries return relevant responses

**Time:** 1-2 hours (mostly waiting)

---

### 5.3 Configure Custom Domain (Optional)

**Tasks:**

- [ ] Register domain (or use existing)
- [ ] Map domain to Cloud Run
- [ ] Configure SSL certificate
- [ ] Update CORS settings

**Commands:**
```bash
# Map custom domain
gcloud run domain-mappings create \
  --service=agora-backend \
  --domain=api.yourdomain.com \
  --region=us-central1

# Update DNS records (follow instructions from command output)

# Update CORS
gcloud run services update agora-backend \
  --region=us-central1 \
  --set-env-vars="CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com"
```

**Time:** 1-2 hours

---

## Phase 6: Monitoring & Analytics (Week 6)

**Goal:** Set up monitoring and usage analytics

### 6.1 Set Up Logging

**Tasks:**

- [ ] Configure structured logging
- [ ] Set up log-based metrics
- [ ] Create custom dashboards
- [ ] Set up error alerting

**Commands:**
```bash
# View logs
gcloud run services logs read agora-backend \
  --region=us-central1 \
  --limit=100

# Create log-based metric for errors
gcloud logging metrics create query_errors \
  --description="Count of query errors" \
  --log-filter='resource.type="cloud_run_revision" AND severity>=ERROR'

# Create alert policy
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Agora Error Rate Alert" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=60s
```

**Deliverables:**
- Centralized logging
- Error alerts configured
- Custom dashboards

**Time:** 3-4 hours

---

### 6.2 Usage Analytics

**Tasks:**

- [ ] Track query patterns
- [ ] Monitor author selection frequency
- [ ] Track response times
- [ ] Cost analysis

**Implementation:**
```python
# src/analytics/telemetry.py (create)

import json
from datetime import datetime
from pathlib import Path

class Telemetry:
    """Simple telemetry for tracking usage."""

    def __init__(self, log_file: str = "logs/telemetry.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)

    def log_query(self, query: str, selected_authors: list, response_time: float):
        """Log a query event."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event': 'query',
            'query': query,
            'authors_selected': [a.id for a in selected_authors],
            'response_time_seconds': response_time,
        }
        self._write_event(event)

    def log_author_selection(self, author_id: str, relevance_score: float):
        """Log author selection."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event': 'author_selection',
            'author_id': author_id,
            'relevance_score': relevance_score,
        }
        self._write_event(event)

    def _write_event(self, event: dict):
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(event) + '\n')
```

**Analysis Script:**
```python
# scripts/analyze_usage.py

import json
from collections import Counter
from pathlib import Path

def analyze_telemetry(log_file='logs/telemetry.jsonl'):
    events = []
    with open(log_file) as f:
        events = [json.loads(line) for line in f]

    # Query count
    queries = [e for e in events if e['event'] == 'query']
    print(f"Total queries: {len(queries)}")

    # Author selection frequency
    selections = [e for e in events if e['event'] == 'author_selection']
    author_counts = Counter(s['author_id'] for s in selections)
    print("\nAuthor selection frequency:")
    for author, count in author_counts.most_common():
        print(f"  {author}: {count}")

    # Average response time
    avg_time = sum(q['response_time_seconds'] for q in queries) / len(queries)
    print(f"\nAverage response time: {avg_time:.2f}s")

if __name__ == '__main__':
    analyze_usage()
```

**Deliverables:**
- Usage tracking implemented
- Analytics dashboard
- Cost insights

**Time:** 4-5 hours

---

## Summary Checklist

### Phase 1: Data (Week 1)
- [x] Infrastructure setup
- [ ] Acquire texts (Marx, Whitman, Baudelaire)
- [ ] Clean and prepare data
- [ ] Ingest into vector database
- [ ] Test RAG pipeline

### Phase 2: Frontend (Week 2)
- [ ] Build HTML/CSS UI
- [ ] Implement JavaScript logic
- [ ] Deploy to Cloud Storage
- [ ] Test frontend ↔ backend

### Phase 3: Features (Week 3)
- [ ] Add streaming responses
- [ ] Implement caching
- [ ] Multi-panel support

### Phase 4: Testing (Week 4)
- [ ] Integration tests
- [ ] Performance testing
- [ ] User acceptance testing

### Phase 5: Deployment (Week 5)
- [ ] Pre-deployment checks
- [ ] Deploy to production
- [ ] Verify and test
- [ ] Optional: Custom domain

### Phase 6: Operations (Week 6)
- [ ] Set up logging
- [ ] Configure monitoring
- [ ] Usage analytics
- [ ] Cost optimization

---

## Success Metrics

### Technical
- ✅ API response time < 3s (p95)
- ✅ 99.9% uptime
- ✅ Cache hit rate > 80%
- ✅ Cost < $20/month for light usage

### Quality
- ✅ Relevant author selection (>90% accuracy)
- ✅ Coherent responses (3 paragraphs max)
- ✅ Factually grounded (cites sources)
- ✅ Distinct author voices

### User Experience
- ✅ Intuitive UI
- ✅ Fast perceived performance (streaming)
- ✅ Works on mobile and desktop
- ✅ Accessible (WCAG 2.1 AA)

---

## Cost Estimate

### Monthly Operating Costs (Light Usage)
- Cloud Run: $5-15
- Cloud Storage: $0.50
- Artifact Registry: $0.10
- Secret Manager: $0.06
- LLM API calls (Gemini): $2-10
- **Total: ~$8-26/month**

### One-Time Costs
- Domain (optional): $12/year
- Text acquisition: $0-30 (Baudelaire books)

---

## Next Steps

**Start with Phase 1:**
```bash
# 1. Acquire texts
mkdir -p data/raw/{marx,whitman,baudelaire}
wget https://www.gutenberg.org/files/61/61-0.txt -O data/raw/marx/capital_vol1.txt

# 2. Set up environment
cp .env.example .env
nano .env  # Add GEMINI_API_KEY

# 3. Ingest data
python scripts/init_database.py
python scripts/ingest_author.py --author marx

# 4. Test
uvicorn src.api.main:app --reload
```

Then proceed through phases 2-6 sequentially.

**Questions?** See:
- `docs/DEPLOYMENT.md` for deployment details
- `docs/ARCHITECTURE.md` for system architecture
- `TEST_CICD.md` for testing guide
