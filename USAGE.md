# Agora Usage Guide

Complete guide for using the Agora Virtual Debate Panel application.

## Quick Start

### 1. Set Up Environment (5 minutes)

```bash
# Create .env file
cp .env.example .env

# Edit .env and add your GEMINI_API_KEY
nano .env

# Set:
# GEMINI_API_KEY=your_actual_key_here
# LLM_PROVIDER=gemini
# VECTOR_DB=chromadb
```

### 2. Acquire and Ingest Data (20-30 minutes)

```bash
# Download texts from Project Gutenberg
./scripts/acquire_texts.sh

# Clean texts (remove boilerplate)
python scripts/clean_texts.py

# Initialize database
python scripts/init_database.py

# Ingest authors (will take a few minutes each)
python scripts/ingest_author.py --author marx
python scripts/ingest_author.py --author whitman

# If you have Baudelaire content:
python scripts/ingest_author.py --author baudelaire

# Generate expertise profiles
python scripts/create_expertise_profiles.py
```

### 3. Test the System (5-10 minutes)

```bash
# Test RAG pipeline
python scripts/test_rag.py

# Start API server
uvicorn src.api.main:app --reload

# In another terminal, test endpoints
curl http://localhost:8000/api/health
curl http://localhost:8000/api/authors

# Test a query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '"query": "What is class struggle?", "max_authors": 3}'
```

### 4. Use the Frontend (2 minutes)

```bash
# Serve frontend locally
cd src/ui
python -m http.server 3000

# Open in browser
open http://localhost:3000
```

---

## API Endpoints

### Health Check
```bash
GET /api/health

# Returns service status and component health
```

### List Authors
```bash
GET /api/authors

# Returns all available authors with their profiles
```

### Get Author Details
```bash
GET /api/authors/{author_id}

# Example: GET /api/authors/marx
```

### Query (Standard)
```bash
POST /api/query
Content-Type: application/json

{
  "query": "What is freedom?",
  "max_authors": 5,
  "relevance_threshold": 0.7
}

# Returns all responses at once
```

### Query (Streaming)
```bash
POST /api/query/stream
Content-Type: application/json

{
  "query": "What is freedom?",
  "max_authors": 5
}

# Returns Server-Sent Events stream
# Responses arrive incrementally as each author completes
```

### Author Rankings
```bash
GET /api/rankings?query=What+is+freedom

# Returns all authors ranked by relevance to query
# Useful for debugging semantic routing
```

---

## Testing

### Run Integration Tests
```bash
# All tests
pytest tests/integration/ -v

# Specific test class
pytest tests/integration/test_api.py::TestQueryEndpoint -v

# With coverage
pytest tests/integration/ --cov=src --cov-report=html
```

### Run Performance Tests
```bash
# Test with increasing concurrency (1, 5, 10, 20, 50 requests)
python scripts/test_performance.py

# Must have API running first:
# uvicorn src.api.main:app --reload
```

### Run RAG Pipeline Tests
```bash
# Test query routing and response generation
python scripts/test_rag.py

# Tests 16+ queries across all authors
# Measures accuracy and response times
```

---

## Deployment

### Deploy Backend to Cloud Run

```bash
# Option 1: Automatic (via CI/CD)
git push origin main
# Cloud Build triggers automatically

# Option 2: Manual
gcloud builds submit --config=cloudbuild.yaml .

# Monitor deployment
gcloud builds list --limit=5
gcloud builds log $(gcloud builds list --limit=1 --format='value(ID)')
```

### Deploy Frontend to Cloud Storage

```bash
# Run deployment script
./scripts/deploy_frontend.sh

# Or manually:
gsutil -m rsync -r src/ui/ gs://PROJECT_ID-agora-frontend/
```

### Update API URL in Frontend

After deploying backend, update frontend to point to production:

```javascript
// src/ui/app.js - Line 3
const API_URL = 'https://agora-backend-XXX-uc.a.run.app'; // Your Cloud Run URL
```

Then redeploy frontend:
```bash
./scripts/deploy_frontend.sh
```

---

## Monitoring & Analytics

### View Telemetry
```bash
# Telemetry logs to logs/telemetry.jsonl
tail -f logs/telemetry.jsonl

# Analyze with jq
cat logs/telemetry.jsonl | jq '.event' | sort | uniq -c

# Count queries
cat logs/telemetry.jsonl | jq 'select(.event=="query")' | wc -l

# Average response time
cat logs/telemetry.jsonl | jq -r 'select(.event=="query") | .response_time_seconds' | awk '{sum+=$1; count++} END {print sum/count}'
```

### Cache Statistics
```python
# In Python console or script
from src.utils import ResponseCache

cache = ResponseCache()
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
print(f"Total requests: {stats['total_requests']}")
```

### Cloud Run Metrics
```bash
# View logs
gcloud run services logs read agora-backend --region=us-central1 --limit=100

# View metrics in console
open https://console.cloud.google.com/run/detail/us-central1/agora-backend/metrics
```

---

## Troubleshooting

### "No data ingested yet"

**Problem**: API returns 400 or queries return no authors

**Solution**:
```bash
# Check if data is ingested
python -c "
from src.data import get_vector_db
from config.settings import settings
db = get_vector_db(**settings.get_vector_db_config())
db.initialize()
# Check collections exist
"

# Re-ingest if needed
python scripts/ingest_author.py --author marx
```

### "API key invalid"

**Problem**: GEMINI_API_KEY not working

**Solution**:
```bash
# Test API key
curl -H "x-goog-api-key: YOUR_KEY" \
  "https://generativelanguage.googleapis.com/v1beta/models"

# Should return list of models
# If not, get new key from https://aistudio.google.com/app/apikey
```

### "ChromaDB not found"

**Problem**: Vector database initialization fails

**Solution**:
```bash
# Reinstall chromadb
pip install --upgrade chromadb

# Delete and recreate database
rm -rf data/chroma_db
python scripts/init_database.py
```

### "Frontend can't connect to backend"

**Problem**: CORS or network error

**Solution**:
1. Check API is running: `curl http://localhost:8000/api/health`
2. Check CORS settings in .env:
   ```
   CORS_ORIGINS=http://localhost:3000,http://localhost:8000
   ```
3. Update API_URL in `src/ui/app.js`

### "Tests failing"

**Problem**: Integration tests return errors

**Solution**:
```bash
# Make sure API is running
uvicorn src.api.main:app --reload &

# Wait for startup
sleep 5

# Run tests
pytest tests/integration/ -v

# Check specific failures
pytest tests/integration/test_api.py::test_health_check -vv
```

---

## Configuration

### Adding a New Author

1. Create author config:
```yaml
# config/authors/nietzsche.yaml
name: Friedrich Nietzsche
expertise_domains:
  - nihilism
  - existentialism
  - morality
  - will to power
voice_characteristics:
  tone: provocative, aphoristic
  vocabulary: philosophical, poetic
  perspective: iconoclastic
system_prompt: |
  You are Friedrich Nietzsche...
```

2. Add text files:
```bash
mkdir -p data/raw/nietzsche
# Add .txt files to this directory
```

3. Ingest:
```bash
python scripts/ingest_author.py --author nietzsche
python scripts/create_expertise_profiles.py
```

### Adjusting Author Selection

Edit `.env`:
```bash
# More selective (fewer authors)
RELEVANCE_THRESHOLD=0.8
MIN_AUTHORS=1
MAX_AUTHORS=3

# More inclusive (more authors)
RELEVANCE_THRESHOLD=0.5
MIN_AUTHORS=2
MAX_AUTHORS=5
```

### Changing LLM Provider

Edit `.env`:
```bash
# Use OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4-turbo

# Use Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_key
ANTHROPIC_MODEL=claude-3-opus-20240229
```

---

## Cost Management

### Reduce LLM API Costs

1. **Enable caching** (already on by default):
   - 80%+ cost reduction for repeated queries
   - Semantic similarity matching

2. **Use cheaper models**:
   ```bash
   # .env
   GEMINI_MODEL=gemini-1.5-flash  # Cheaper than Pro
   ```

3. **Limit response length**:
   ```bash
   # .env
   MAX_RESPONSE_TOKENS=200  # Default is 300
   ```

4. **Reduce top-k chunks**:
   ```bash
   # .env
   TOP_K_CHUNKS=3  # Default is 5
   ```

### Monitor Costs

```bash
# Count total queries
cat logs/telemetry.jsonl | jq 'select(.event=="query")' | wc -l

# Count cache hits (saved money!)
cat logs/telemetry.jsonl | jq 'select(.event=="query" and .cache_hit==true)' | wc -l

# Estimated costs (Gemini Flash ~$0.0001/query without cache)
python -c "
queries = 1000  # Your total queries
cache_rate = 0.8  # 80% cache hit rate
cost_per_query = 0.0001
actual_queries = queries * (1 - cache_rate)
print(f'Estimated cost: \${actual_queries * cost_per_query:.2f}')
"
```

---

## Advanced Usage

### Custom System Prompts

Edit `config/authors/{author}.yaml`:
```yaml
system_prompt: |
  You are Karl Marx. When answering questions:
  - Focus on class analysis and material conditions
  - Reference your works (Capital, Manifesto, etc.)
  - Keep responses to 3 paragraphs maximum
  - Use accessible language while maintaining rigor
  - Highlight contradictions in capitalism
```

### Multi-Panel Configuration

Create panel configs in `config/panels/`:
```yaml
# config/panels/philosophy.yaml
panel:
  id: philosophy
  name: "Philosophy Panel"
authors:
  - marx
  - nietzsche
  - plato
settings:
  relevance_threshold: 0.6
```

---

## Tips & Best Practices

1. **Start with one author** (Marx) to verify everything works
2. **Test locally** before deploying to production
3. **Monitor cache hit rate** - should be >70% after initial queries
4. **Use streaming** for better UX with multiple authors
5. **Set reasonable limits** (max_authors=3-5) to control costs
6. **Regular testing** with `pytest` and `test_performance.py`
7. **Check telemetry** weekly to understand usage patterns

---

## Getting Help

- **Documentation**: See `docs/` folder
- **Architecture**: `docs/ARCHITECTURE.md`
- **Deployment**: `docs/DEPLOYMENT.md`
- **Implementation**: `IMPLEMENTATION_PLAN.md`
- **Testing**: `TEST_CICD.md`

---

## Next Steps

After getting the basic system running:

1. Add more authors (Nietzsche, Plato, etc.)
2. Implement multi-panel support
3. Set up custom domain
4. Add user authentication
5. Implement conversation history
6. Build analytics dashboard

