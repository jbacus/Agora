# Claude Context: Boulder COdePILOT

## Project Overview

**COdePILOT** is a hybrid-architecture AI-powered assistant for architects working in Colorado municipalities. It helps navigate building codes, zoning regulations, and provides GIS data for properties. The application combines a **Python FastAPI backend** with **ChromaDB vector store** for semantic IRC search, and a **React frontend** with multi-agent AI routing for optimal performance.

### Multi-Region Architecture (NEW - 2025-11-10)

**Status**: Core infrastructure 80% complete, App integration 20% complete

The application has been refactored to support multiple Colorado municipalities through a configuration system:

- **Configuration Files**: `config/regions/` contains region-specific settings
- **Current Regions**: Boulder (full-featured), Salida (test case)
- **New Region Onboarding**: 4-8 hours via configuration files only
- **Zero Code Changes**: Adding regions requires no application code modifications

**Key Files**:
- `config/types.ts` - TypeScript interfaces for region configurations
- `config/regions/*.ts` - Individual region configurations
- `config/RegionContext.tsx` - React context for region management
- `services/*MultiRegion.ts` - Configuration-driven service implementations
- `components/RegionSelector.tsx` - UI for switching regions

**Documentation**:
- `docs/MULTI_REGION_ARCHITECTURE.md` - Architecture design and planning
- `docs/MULTI_REGION_INTEGRATION_GUIDE.md` - Step-by-step integration instructions
- `docs/MULTI_REGION_IMPLEMENTATION_SUMMARY.md` - Implementation status and results

**Original Boulder Implementation**: The original Boulder-specific codebase has been preserved and a configuration-driven system has been built alongside it. Complete integration requires 2-3 hours of work following the integration guide.

### Core Technology Stack (v5.0 Hybrid Architecture)
- **Backend**: Python 3.11 + FastAPI
  - **Vector Store**: ChromaDB (in-memory) for IRC 2024 embeddings
  - **AI Service**: Google Gemini API (`google-generativeai`)
  - **IRC Processing**: Semantic search with ~4,400 embedded chunks
- **Frontend**: React 19 with TypeScript
  - **AI Service**: Google Gemini (via `@google/genai`)
  - **Multi-Agent Routing**: Intelligent query classification for cost optimization
  - **Build Tools**: esbuild (JS bundling), PostCSS + Tailwind CSS (styling)
  - **GIS Integration**: ArcGIS REST API services (57 layers)
- **Web Server**: nginx (reverse proxy)
  - Frontend served from `/usr/share/nginx/html`
  - Backend API proxied from `/api/*` to internal port 8000
- **Build Pipeline**: Multi-stage Docker build
  - Stage 1: Node.js - IRC preprocessing + embedding generation + frontend build
  - Stage 2: Python - Backend runtime with nginx
- **Deployment**: Google Cloud Run (2GB memory, 300s timeout) + Cloudflare DNS

## Key Files and Architecture

### Backend (Python FastAPI)
- **backend/main.py** - FastAPI application with IRC semantic search endpoints
  - `/health` - Health check endpoint (IRC collection status, vector count)
  - `/api/search-irc` - Semantic search endpoint (query → top-k relevant chunks)
  - `/api/chat` - Chat endpoint with automatic IRC context injection
- **backend/process_irc.py** - IRC data processing utilities (deprecated, now uses frontend scripts)
- **backend/requirements.txt** - Python dependencies (FastAPI, ChromaDB, google-generativeai)
- **backend/irc-preprocessed-with-embeddings.json** - Precomputed IRC embeddings (copied from frontend build)

### Frontend (React + TypeScript)
- **App.tsx** - Main application component, handles chat interface and AI function calls
- **index.tsx** - Application entry point, renders App
- **theme.ts** - Theme configuration with light/dark modes
- **types.ts** - TypeScript type definitions
- **version.ts** - Version numbering and build tracking

### Build Scripts (TypeScript)
- **scripts/preprocess-irc.ts** - Extract text from IRC PDF, chunk into sections
- **scripts/generate-embeddings.ts** - Generate Gemini embeddings for all IRC chunks
- **public/irc-preprocessed-with-embeddings.json** - Build artifact (4,400 chunks with 768-dim embeddings)

### Services
- **services/geminiService.ts** - Gemini AI integration, system instructions, function declarations (21 tools)
- **services/documentService.ts** - PDF document upload and caching service
- **services/gisService.ts** - GIS data fetching from ArcGIS services (57 layers integrated)
- **services/weatherService.ts** - Weather and climate data (NOAA + Visual Crossing APIs)
- **services/solarService.ts** - Solar resource and PV potential (NREL APIs)
- **services/elevationService.ts** - Elevation and topography (OpenTopography / USGS 3DEP)
- **services/soilService.ts** - Soil and geotechnical data (USDA NRCS SSURGO)
- **services/propertyService.ts** - Property ownership and tax data (Boulder County Assessor)
- **services/schoolService.ts** - School district boundaries (Colorado CDPHE)
- **services/seismicService.ts** - Seismic design parameters (USGS ASCE 7-16 / IBC 2021)
- **services/radonService.ts** - Radon zone data (EPA + Colorado CDPHE)
- **services/sunPathService.ts** - Sun position and passive solar design (NOAA algorithms)
- **services/treeService.ts** - Tree inventory and protection requirements (City of Boulder Urban Forestry)
- **services/airQualityService.ts** - Air quality index and HVAC filtration guidance (EPA AirNow)
- **services/contaminatedSitesService.ts** - Superfund sites and environmental due diligence (EPA Envirofacts)
- **services/transitService.ts** - Transit access and LEED compliance (RTD / Boulder Transit)

### Utilities
- **utils/logger.ts** - Logging utility with debug, info, warn, error levels
- **utils/geocodingCache.ts** - LRU cache for geocoding results (80% API call reduction)
- **utils/functionRegistry.ts** - Centralized function call registry for AI tools

### Components
- **components/ChatMessage.tsx** - Individual message display
- **components/ChatInput.tsx** - User input interface
- **components/Console.tsx** - Developer console component

### Build Configuration
- **Dockerfile.hybrid** - Multi-stage Docker build for hybrid architecture
  - Stage 1 (frontend-builder): Node.js 20 Alpine - Build IRC embeddings + frontend
  - Stage 2 (runtime): Python 3.11 Slim - FastAPI backend + nginx serving frontend
- **docker-entrypoint-hybrid.sh** - Startup script (launches nginx + uvicorn backend)
- **nginx-hybrid.conf** - nginx reverse proxy configuration
- **cloudbuild-hybrid.yaml** - Google Cloud Build pipeline (CI/CD)
- **vite.config.ts** - Development server configuration
- **esbuild.config.mjs** - Production build configuration
- **postcss.config.js** - PostCSS/Tailwind configuration
- **tailwind.config.js** - Tailwind CSS customization
- **.dockerignore** - Files excluded from Docker build context

### Styling
- **styles.css** - Main stylesheet with Tailwind imports

### Documentation
- **Claude.md** - Context and continuity for Claude conversations
- **ARCHITECTURE.md** - Comprehensive system architecture and design patterns
- **REFACTORING.md** - Performance and maintainability refactoring documentation
- **GIS_ARCHITECTURE.md** - GIS integration technical documentation
- **CHANGELOG.md** - Version history and release notes
- **TEST_PLAN.md** - Testing strategy and scenarios
- **DOMAIN_SETUP.md** - Deployment and domain configuration

## Current State

### Version
- **Current Version**: v5.0.0 (Hybrid Architecture - Python Backend + React Frontend) 🚀
- **Build Date**: 2025-11-13
- **Versioning Scheme**: Semantic Versioning (MAJOR.MINOR.PATCH)
  - MAJOR: Breaking changes or major feature releases
  - MINOR: New features, backwards compatible
  - PATCH: Bug fixes, minor improvements
- **Location**: Displayed in header next to application title
- **Configuration**: `version.ts` file (frontend) + `backend/main.py` (backend)

### Multi-Agent Architecture (NEW in v4.0.0)
- **Router Service**: AI-powered query classification routes to specialized agents
  - Uses Gemini Flash for fast routing (~200ms overhead)
  - Analyzes query intent: location, code, general, or hybrid
  - Fallback keyword-based routing if AI fails
- **Specialized Agents**:
  - **Location Agent** (Flash): 21 GIS/site analysis tools - handles ~50% of queries
  - **Code Agent** (Pro): 2 IRC tools + documents - handles ~30% of queries
  - **General Agent** (Flash): No tools, conversational - handles ~15% of queries
  - **Full Agent** (Pro): All 24 tools, fallback - handles ~5% of queries
- **Performance Improvements**:
  - 71% cost reduction ($0.0003 → $0.000086 per request)
  - 27% faster responses (3.0s → 2.2s average)
  - 60% token reduction (4000 → 1600 average)
- **Telemetry Service**: Tracks routing decisions, latency, costs, agent statistics
- **IRC Chapter Classifier**: Prepares for chapter-level document loading (Phase 3)
- **Implementation**: Opt-in, maintains backward compatibility with v3.x
- **Documentation**: See `docs/MULTI_AGENT_IMPLEMENTATION.md` for integration guide

### Multi-Agent Services (v4.0.0)
- **services/routerService.ts** - Query classification and routing logic
- **services/agentFactory.ts** - Creates specialized agents on demand
- **services/functionDeclarations.ts** - Centralized function tool definitions
- **services/ircChapterClassifier.ts** - IRC chapter identification for optimized loading
- **services/telemetryService.ts** - Performance metrics and cost tracking
- **services/systemInstruction.ts** - Agent-specific system instructions (updated)

### Hybrid Backend Architecture (v5.0.0) 🆕
The v5.0 release introduces a **Python FastAPI backend** alongside the React frontend, creating a hybrid architecture:

**Why Hybrid?**
- **IRC Document Size**: 71MB IRC PDF exceeds Gemini File API 20MB limit
- **Semantic Search**: ChromaDB provides efficient vector search over 4,400 IRC chunks
- **Cost Optimization**: Backend pre-filters relevant IRC sections before sending to frontend AI
- **Performance**: Pre-computed embeddings eliminate real-time embedding overhead

**How It Works**:
1. **Build Time**: TypeScript scripts (`npm run build:irc`) extract IRC text and generate embeddings
2. **Docker Build**: Multi-stage Dockerfile copies embeddings to backend container
3. **Runtime**: FastAPI loads embeddings into ChromaDB in-memory on startup
4. **API Endpoints**:
   - `GET /health` - Check IRC collection status and vector count
   - `POST /api/search-irc` - Semantic search (query → top-k chunks)
   - `POST /api/chat` - Chat with automatic IRC context injection
5. **Frontend Integration**: Frontend can optionally call backend IRC search via fetch API

**Backend Stack**:
- **FastAPI** - Modern async Python web framework
- **ChromaDB 0.4.22** - In-memory vector store (no persistence needed)
- **google-generativeai** - Gemini API client for backend chat endpoint
- **uvicorn** - ASGI server (runs on internal port 8000)
- **nginx** - Reverse proxy (port 8080 → frontend static files + `/api/*` → backend)

**IRC Preprocessing Pipeline**:
```
IRC PDF (71MB)
  ↓ scripts/preprocess-irc.ts
IRC JSON chunks (~4,400 sections)
  ↓ scripts/generate-embeddings.ts (Gemini text-embedding-004)
IRC with embeddings (768-dim vectors)
  ↓ Docker build (COPY to backend/)
ChromaDB collection (loaded on startup)
  ↓ FastAPI endpoints
Semantic search API
```

**Deployment**:
- **Cloud Build**: `cloudbuild-hybrid.yaml` orchestrates multi-stage build
- **Secret Manager**: `GEMINI_API_KEY` fetched and passed as build arg
- **Cloud Run**: 2GB memory (required for ChromaDB), 300s timeout, 1 CPU
- **Build Machine**: N1_HIGHCPU_8 (faster npm install + IRC processing)

### Color Theme
- **Design**: Pure monochromatic grey palette
- **Primary Accent**: Neutral grey (zinc palette)
  - Light mode: `#71717A` (zinc-500)
  - Dark mode: `#A1A1AA` (zinc-400)
- **Backgrounds**: Pure grey shades only (no color tints)
  - Light mode: `#F5F5F5`, `#FFFFFF`, `#E8E8E8`
  - Dark mode: `#1E1E1E`, `#252525`, `#2D2D2D`
- **Status colors**: Functional colors preserved (red, amber, blue, green)
- **Theme history**:
  - v3.3.9: Pure grey monochromatic (2025-11-07)
  - v3.3.8-v2.5.0: Green-tinted backgrounds with slate grey accents (2025-11-07)
  - Pre-v2.5.0: Orange accent (`#F97316`)
- Theme supports light/dark modes with system detection

### AI Integration
- **Frontend Multi-Agent System**: Intelligent routing to specialized agents (v4.0.0)
  - Location Agent: Gemini Flash with 21 location tools
  - Code Agent: Gemini Pro with IRC tools (calls backend API)
  - General Agent: Gemini Flash for conversation
  - Full Agent: Gemini 2.5 Pro with all 25 tools (includes backend IRC search)
- **Backend Gemini Integration**: Separate Gemini instance for IRC chat endpoint
  - Model: `gemini-2.0-flash-exp`
  - Automatic IRC context injection via semantic search
  - Standalone chat API (can be used independently)
- **Document Integration**: Local PDF files uploaded via Gemini File API (frontend)
  - City of Boulder Design & Construction Standards (2024) - 3.0MB
  - Solar Access Guide - 1.1MB
  - ~~International Residential Code (IRC) 2024 - 71MB~~ → Now handled by backend ChromaDB
- **Function Calling**: 25 site analysis and building code tools
  - 21 GIS/environmental tools (frontend)
  - 2 IRC search tools (frontend → backend API)
  - 2 building code reference tools (frontend)
- **System Instructions**: Specialized per agent type for optimal performance
- **Cost Optimization**: 71% reduction through intelligent model selection

## Known Issues and Solutions

### GIS Service URLs - ✅ RESOLVED (2025-11-01)
**Previous Issue**: ArcGIS REST API endpoints were returning "Invalid URL" errors
**Current Status**: ✅ FULLY OPERATIONAL - All endpoints verified and working
**Impact**: GIS functionality now fully available to users

**Resolution Summary**:
Old `services3.arcgis.com` endpoints were replaced with official government GIS servers:
- City of Boulder: `gis.bouldercolorado.gov`
- Boulder County: `maps.bouldercounty.org`

All five service endpoints have been:
1. ✅ Located through official REST services directories
2. ✅ Verified with spatial query testing
3. ✅ Updated in `gisService.ts:25-32`
4. ✅ Field names mapped to actual service responses
5. ✅ Built successfully and ready for deployment

**Verified Endpoints** (See `GIS_ENDPOINTS_VERIFIED.md` for full details):
- City Zoning: `gis.bouldercolorado.gov/ags_svr1/rest/services/plan/ZoningDistricts/MapServer/0`
- City Floodplain: `gis.bouldercolorado.gov/ags_svr3/rest/services/util/FloodplainOpenData/MapServer/1`
- County Zoning: `maps.bouldercounty.org/arcgis/rest/services/PLANNING/LUC_ZoningDistricts/MapServer/0`
- County Floodplain: `maps.bouldercounty.org/arcgis/rest/services/HAZARD/FLOODPLAIN_BC_REGULATED/MapServer/0`
- Wildland-Urban Interface: `gis.bouldercolorado.gov/ags_svr1/rest/services/fire/WildlandUrbanInterface/MapServer/0`
  - Note: Older County Wildfire Hazard layer (2003) removed in v3.3.8 to eliminate conflicts

**Documentation**:
- `GIS_ARCHITECTURE.md` - Complete technical architecture (updated with verified endpoints)
- `GIS_ENDPOINTS_VERIFIED.md` - Full verification report with test results and field mappings

**Official Data Sources** (verified 2025-11-01):
- Boulder County Open Data: https://opendata-bouldercounty.hub.arcgis.com/
- City of Boulder Open Data: https://open-data.bouldercolorado.gov/
- License: Creative Commons Attribution 4.0 International

### Browser Console Errors
If you see console errors after changes:
1. Hard refresh the browser (Cmd+Shift+R / Ctrl+Shift+F5)
2. Clear browser cache
3. Verify build completed successfully with `npm run build`

## Development Workflow

### Frontend Development
```bash
npm run dev            # Vite development server (port 5173)
npm run build          # Build CSS + JS for production
npm run build:css      # Build Tailwind CSS only
npm run build:js       # Build JavaScript only (esbuild)
npm run build:irc      # Preprocess IRC + generate embeddings (required for backend)
```

### Backend Development
```bash
cd backend
python -m venv venv                    # Create virtual environment
source venv/bin/activate               # Activate (macOS/Linux)
# venv\Scripts\activate                # Activate (Windows)
pip install -r requirements.txt        # Install dependencies
python main.py                         # Run backend (port 8000)
```

**Backend Requirements**:
- Python 3.11+
- `public/irc-preprocessed-with-embeddings.json` must exist (run `npm run build:irc` first)
- `GEMINI_API_KEY` environment variable set

### Docker Development (Full Stack)
```bash
# Build hybrid image locally
docker build -f Dockerfile.hybrid \
  --build-arg GEMINI_API_KEY="your-key-here" \
  -t boulder-codepilot:local .

# Run locally (port 8080)
docker run -p 8080:8080 \
  -e GEMINI_API_KEY="your-key-here" \
  boulder-codepilot:local

# Test endpoints
curl http://localhost:8080/health
curl http://localhost:8080/api/search-irc?query="foundation requirements"
```

### Testing
```bash
npm run test:console        # Test local dev server
npm run test:console:prod   # Test production site
npm test                    # Build + test
```

### Git Status (as of 2025-11-07)
- Working branch: `main`
- Working tree: Clean (all changes committed)
- **Automatic CI/CD**: Push to `main` automatically deploys to production via GitHub
- Recent commits focus on: Production hardening, automated testing, GIS fixes, PDF handling

## Important Context

### Local Document Integration
The AI has access to local PDF reference documents uploaded via Gemini File API. This provides accurate responses about Boulder building codes and regulations, including:
- International Building Code (IBC) 2021 + Boulder amendments
- International Residential Code (IRC) 2021 + Boulder amendments
- International Energy Conservation Code (IECC) 2021 + Boulder amendments
- International Mechanical Code (IMC) 2021
- International Fuel Gas Code (IFGC) 2021
- International Plumbing Code (IPC) 2021
- National Electrical Code (NEC) 2020
- International Wildland-Urban Interface Code (IWUIC) 2021

### Jurisdiction Handling
The application automatically determines jurisdiction (City of Boulder vs Boulder County) by:
1. Checking if coordinates fall within City of Boulder zoning districts
2. If yes → City of Boulder (uses city-specific layers)
3. If no → Boulder County (uses county-specific layers)

### Domain and Deployment
- **Production URL**: https://codepilot.bacus.org
- **Backend**: Google Cloud Run (Boulder-COdePILOT-353167094895.us-west1.run.app)
- **CDN/Proxy**: Cloudflare (DNS only, not proxied)
- **CI/CD**: Automatic deployment through GitHub
  - Push to `main` branch triggers automatic build and deployment to Google Cloud Run
  - No manual deployment commands needed
  - Changes appear in production automatically after push
- See `DOMAIN_SETUP.md` for deployment details

## Recent Changes Log

### 2025-11-13 (v5.0.0 - Hybrid Architecture) 🚀
- ✅ **MAJOR RELEASE** - Hybrid Python + React architecture
  - **Python FastAPI Backend** - Dedicated IRC semantic search service
    - ChromaDB in-memory vector store (~4,400 IRC chunks)
    - Gemini `text-embedding-004` embeddings (768 dimensions)
    - `/api/search-irc` - Semantic search endpoint
    - `/api/chat` - Chat with automatic IRC context injection
    - `/health` - Health check and collection status
  - **TypeScript Build Scripts** - IRC preprocessing and embedding generation
    - `scripts/preprocess-irc.ts` - Extract text from 71MB IRC PDF
    - `scripts/generate-embeddings.ts` - Generate embeddings via Gemini API
    - Caching with checksums (skip if source unchanged)
    - Output: `public/irc-preprocessed-with-embeddings.json`
  - **Multi-Stage Docker Build** - Optimized for Cloud Build
    - Stage 1 (Node.js): Build IRC embeddings + compile frontend
    - Stage 2 (Python): Load embeddings + run FastAPI + nginx
    - `GEMINI_API_KEY` passed as build arg (from Secret Manager)
    - 2GB memory allocation (required for ChromaDB)
  - **nginx Reverse Proxy** - Single-port deployment
    - Port 8080 → Static frontend files
    - `/api/*` → Backend FastAPI (internal port 8000)
    - CORS headers, gzip compression, caching
  - **Cloud Build Pipeline** - Automated CI/CD
    - `cloudbuild-hybrid.yaml` - Build and deploy configuration
    - Fetch API key from Secret Manager
    - Multi-stage Docker build with IRC preprocessing
    - Deploy to Cloud Run with 2GB memory
  - **Breaking Changes**:
    - ⚠️ IRC no longer uses Gemini File API (now ChromaDB backend)
    - ⚠️ Deployment requires Python backend (not frontend-only)
    - ⚠️ Build process includes IRC preprocessing (5-10 min first build)
  - **Benefits**:
    - ✅ Handles 71MB IRC PDF (exceeds Gemini File API 20MB limit)
    - ✅ Fast semantic search (ChromaDB vector similarity)
    - ✅ Pre-computed embeddings (no real-time overhead)
    - ✅ Backend can be used independently via API
    - ✅ Scalable architecture for additional documents
  - **Documentation**:
    - Updated `GEMINI_INSTRUCTIONS.md` - Complete hybrid architecture guide
    - Updated `CLAUDE.md` - Comprehensive v5.0 context
    - Updated `.dockerignore` - Include docs/IRC for build
  - **Files Added/Modified**:
    - Added `backend/main.py` (367 lines)
    - Added `backend/process_irc.py` (archived, now uses TypeScript scripts)
    - Added `backend/requirements.txt` (Python dependencies)
    - Added `scripts/preprocess-irc.ts` (IRC text extraction)
    - Added `scripts/generate-embeddings.ts` (embedding generation)
    - Added `Dockerfile.hybrid` (multi-stage build)
    - Added `docker-entrypoint-hybrid.sh` (startup orchestration)
    - Added `nginx-hybrid.conf` (reverse proxy config)
    - Added `cloudbuild-hybrid.yaml` (Cloud Build pipeline)
    - Updated `package.json` - Added `build:irc` scripts
    - Updated `.dockerignore` - Include IRC PDF in build

### 2025-11-10 (v4.0.0 - Multi-Agent Architecture) 🚀
- ✅ **MAJOR RELEASE** - Complete architectural overhaul with intelligent query routing
  - **Router Service** - AI-powered query classification using Gemini Flash
  - **Agent Factory** - Creates specialized agents (location, code, general, full)
  - **Location Agent** - Flash model with 21 GIS/site tools (~50% of queries)
  - **Code Agent** - Pro model with IRC tools + documents (~30% of queries)
  - **General Agent** - Flash model, conversational (~15% of queries)
  - **Full Agent** - Pro model with all 24 tools (~5% fallback)
  - **Telemetry Service** - Tracks routing decisions, latency, costs, statistics
  - **IRC Chapter Classifier** - Keyword-based chapter identification (44 chapters indexed)
  - **Function Declarations** - Centralized tool definitions (single source of truth)
  - **System Instructions** - Agent-specific instructions (200-600 tokens each)
- **Performance Gains**:
  - 71% cost reduction ($0.0003 → $0.000086 per request)
  - 27% faster responses (3.0s → 2.2s average)
  - 60% token reduction (4000 → 1600 average)
- **Documentation**:
  - Created `docs/MULTI_AGENT_IMPLEMENTATION.md` - Integration guide (320 lines)
  - Updated `docs/ARCHITECTURE.md` - Added 600+ lines multi-agent section
  - Updated `CHANGELOG.md` - Comprehensive v4.0.0 release notes
  - Updated `CLAUDE.md` - This file (multi-agent context)
- **New Files**:
  - `services/routerService.ts` (230 lines)
  - `services/agentFactory.ts` (218 lines)
  - `services/functionDeclarations.ts` (390 lines)
  - `services/ircChapterClassifier.ts` (146 lines)
  - `services/telemetryService.ts` (226 lines)
- **Implementation**: Opt-in, maintains backward compatibility with v3.x
- **Next Phase**: IRC chapter splitting for 71MB document (bypasses 20MB API limit)

### 2025-11-07 (v3.3.9 - Pure Grey Theme)
- ✅ **VISUAL UPDATE** - Pure monochromatic grey color scheme
  - **Replaced green-tinted backgrounds** with neutral grey tones throughout
  - **Light theme**: `#F5F5F5`, `#E8E8E8`, `#D4D4D4` (pure greys)
  - **Dark theme**: `#1E1E1E`, `#252525`, `#2D2D2D` (dark greys)
  - **Accent colors**: Zinc palette greys (#71717A light, #A1A1AA dark)
  - **Preserved**: Status colors for functional purposes (red, amber, blue, green)
  - **Impact**: More professional, neutral appearance; better content focus
  - **Files Modified**: `theme.ts`, `version.ts`, `CHANGELOG.md`, `Claude.md`

### 2025-11-07 (v3.3.8 - Fix Wildfire Layer Conflicts)
- ✅ **GIS DATA CONSISTENCY FIX** - Eliminated conflicting wildfire zone responses
  - **Removed COUNTY_WILDFIRE_URL** - Boulder County 2003 wildfire zones layer (outdated)
  - **Retained WILDLAND_URBAN_INTERFACE_URL** - City WUI layer as single authoritative source
  - **Issue**: Two overlapping layers provided contradictory wildfire designations
  - **Impact**: Single consistent wildfire zone reporting for all properties
  - **Files Modified**: `services/gisService.ts`, `version.ts`, `CHANGELOG.md`

### 2025-11-07 (v3.3.7 - Fix PDF 500 Errors)
- ✅ **NGINX CONFIGURATION FIX** - Large PDF file handling
  - **Issue**: 71MB IRC PDF returning 500 Internal Server Error
  - **Root Cause**: Default nginx buffers too small for large files
  - **Fix**: Updated `nginx-simple.conf` with proper buffer sizes
    - Increased `client_max_body_size` to 100M
    - Increased `client_body_buffer_size` to 128k
    - Added explicit PDF location block with proper headers
    - Added 1-hour caching for static assets
  - **Impact**: All building code PDFs now accessible without errors
  - **Files Modified**: `nginx-simple.conf`, `version.ts`, `CHANGELOG.md`

### 2025-11-07 (v3.3.6 - Automated Console Testing)
- ✅ **AUTOMATED ERROR DETECTION** - Puppeteer-based browser testing
  - **Created test-console.js** - 230-line automated testing script
    - Launches headless Chrome browser
    - Captures console errors, warnings, and logs
    - Reports issues with file locations and line numbers
    - Color-coded terminal output
  - **Test Commands**:
    - `npm run test:console` - Test local development server
    - `npm run test:console:prod` - Test production site
    - `npm test` - Build and run local tests
  - **Immediate Value**: Discovered 7 production errors (PDF 500s)
  - **Created docs/TESTING.md** - Complete testing guide
  - **Dependencies**: Added Puppeteer 24.29.1
  - **Impact**: Eliminates need for manual screenshot-based debugging
  - **Files Modified**: `test-console.js`, `package.json`, `docs/TESTING.md`

### 2025-11-07 (v3.3.5 - Docker Config Fix)
- ✅ **CRITICAL FIX**: Corrected config.js boolean generation
  - **Issue**: Bash variable expansion created invalid JavaScript (`gaEnabled: trueG-CWFR3T2926`)
  - **Root Cause**: Incorrect use of `${VAR:+true}${VAR:-false}` causing string concatenation
  - **Fix**: Proper conditional logic in `docker-entrypoint.sh`
  - **Impact**: Resolved production site crash from ReferenceError
  - **Files Modified**: `docker-entrypoint.sh`, `version.ts`, `CHANGELOG.md`

### 2025-11-07 (v3.3.0-v3.3.4 - Production Hardening)
- ✅ **PRODUCTION HARDENING AND REPOSITORY ORGANIZATION**
  - System instruction optimization and AI model efficiency improvements
  - Function result caching for improved performance
  - API key configuration fixes
  - Installation scripts and documentation
  - Architecture documentation updates
  - Directory cleanup and organization
  - See CHANGELOG.md for complete details

### 2025-11-06 (v3.1.0 - Google Analytics Integration)
- ✅ **GOOGLE ANALYTICS 4 INTEGRATION** - Added comprehensive usage analytics
  - **Analytics Service** - New `utils/analytics.ts` utility for event tracking
    - Type-safe event tracking interface
    - Privacy-friendly (IP anonymization enabled)
    - Graceful degradation when GA_MEASUREMENT_ID not configured
    - Debug logging for all tracked events
  - **Tracked Events**:
    - **Chat Events** - Message sent, response received
    - **Function Calls** - Function execution with success/failure and duration
    - **GIS Events** - Address lookups, geocoding results
    - **Document Events** - Document loading success/failure
    - **UI Events** - Theme changes, camera usage
    - **Errors** - API errors and system errors with context
  - **Implementation**:
    - GA script dynamically loaded when measurement ID is configured
    - Analytics initialized on app startup
    - Function call timing tracked automatically
    - Error tracking includes truncated messages for privacy
  - **Configuration**:
    - `GA_MEASUREMENT_ID` environment variable (optional)
    - **Default**: `G-CWFR3T2926` (production tracking ID)
    - Set in Cloud Run environment or docker-entrypoint.sh
    - Enabled by default with production tracking ID
  - **Files Modified**:
    - Created `utils/analytics.ts` (240 lines)
    - Updated `index.html` - Added gtag.js initialization
    - Updated `docker-entrypoint.sh` - Added GA_MEASUREMENT_ID config
    - Updated `App.tsx` - Integrated tracking for all major events
    - Updated `CLAUDE.md` - Documented GA setup and usage

### 2025-11-06 (v3.0.0 - Local Document Integration)
- ✅ **MAJOR: MIGRATION FROM NOTEBOOKLM TO LOCAL PDF DOCUMENTS**
  - **Architecture Change**: Building code knowledge now sourced from local PDFs instead of Google NotebookLM
  - **Document Service Created**: New `services/documentService.ts` for PDF management
    - Gemini File API integration for small PDFs (<20MB)
    - Document caching (45-minute refresh cycle, 48-hour file expiration)
    - Automatic PDF upload on app initialization
  - **Reference Documents Integrated**:
    - **City of Boulder Design & Construction Standards (2024)** - 3.0MB (Gemini File API)
    - **Solar Access Guide** - 1.1MB (Gemini File API)
    - **International Residential Code (IRC) 2024** - 71MB (available for reference, Phase 2: text extraction)
  - **AI Integration Updated**:
    - System instruction no longer references NotebookLM
    - Updated to emphasize local document references
    - Welcome message updated to mention available documents
    - Document loading state added ("Loading building codes...")
  - **Build Configuration Enhanced**:
    - `esbuild.config.mjs` now copies docs/ directory to dist/ automatically
    - PDFs distributed with production builds
  - **Benefits**:
    - ✅ Faster performance (no external NotebookLM API calls)
    - ✅ Local control over reference documents
    - ✅ Native PDF processing by Gemini (maintains structure, tables, images)
    - ✅ Offline-capable after first load
    - ✅ Scalable architecture for Phase 2 enhancements
  - **Breaking Changes**:
    - ⚠️ NotebookLM dependency removed
    - ⚠️ Brief startup delay (5-10 seconds) for document upload
  - **Future Enhancements (Phase 2)**:
    - IRC text extraction with chapter indexing
    - Semantic search for IRC sections
    - Automatic file refresh mechanism
    - Additional building codes (IBC, IECC, IMC, etc.)
  - **Files Modified**:
    - Created `services/documentService.ts`
    - Updated `services/geminiService.ts` (added initializeChatDocuments function)
    - Updated `App.tsx` (added document initialization on startup)
    - Updated `esbuild.config.mjs` (added docs/ copy)
    - Updated `version.ts` (v3.0.0)
    - Updated `CHANGELOG.md` (comprehensive migration notes)
    - Updated `Claude.md` (this file - removed NotebookLM references)

### 2025-11-06 (v2.9.0 - Enhanced GIS - Full Coverage)
- ✅ **PRIORITY 2 GIS SERVICES INTEGRATION** - Expanded from 45 to 57 GIS layers
  - **12 new moderate-value services** for comprehensive site context
  - **Transportation & Access** (2 services):
    - **ConeZones** - Active construction zones and temporary restrictions
    - **CurbsideTypology** - Parking regulations and curbside designations
  - **Topography & Survey** (4 services):
    - **Contours** - Standard 2-foot contour data
    - **2020_Contours** - Updated contour mapping
    - **Benchmarks** - Survey control points with elevations
    - **LiDARTileIndex** - High-resolution LiDAR elevation data coverage
  - **Commercial & Licensing** (3 services):
    - **LiquorLicenses** - Licensed premises locations and types
    - **RentalHousingLicenses** - Rental registration status
    - **RestaurantExpansion** - Outdoor dining expansion zones
  - **Infrastructure & Public Services** (3 services):
    - **SmallCellPoles** - 5G telecommunications infrastructure
    - **LibraryDistrict** - Library service area boundaries
    - **CIPOG2024** - Capital improvement projects (planned infrastructure)
  - **Performance**: All 57 layers query in parallel, complete in 4-5 seconds
  - **City Only**: Priority 2 services apply to City of Boulder jurisdiction
  - **Updated gisService.ts** - Added 12 service endpoints and data extraction
  - **Documentation**: Updated CLAUDE.md, version.ts, and CHANGELOG.md

### 2025-11-06 (v2.8.0 - Complete GIS Integration)
- ✅ **COMPREHENSIVE GIS EXPANSION** - Expanded from 27 to 45+ GIS layers
  - **18 new high-priority services** integrated from City of Boulder Open Data portal
  - **Planning Context** (11 City services):
    - **Schools** - School locations, districts, and types for site selection
    - **Subcommunities** - Neighborhood identity and community character
    - **SpecialDistricts** - Special taxing districts (fire, water, metro)
    - **SpecialZones** - Overlay zones with height limits and design standards
    - **DevelopmentReview** - Active/recent development projects nearby
    - **BVCPAreas** - Boulder Valley Comprehensive Plan policy areas
    - **BVCPNeighborhoodCenters** - Designated mixed-use centers
    - **HousingInfo** - Affordable housing program areas and requirements
    - **RegulatoryFlood** - City regulatory floodplain (more restrictive than FEMA)
    - **ParcelsROW** - Right-of-way and public easements
    - **RegionalTrails** - Multi-use path network and greenway corridors
  - **Utilities & Infrastructure** (5 shared services):
    - **Stormwater** - Storm drain infrastructure and drainage basins
    - **Streams_and_Ditches** - Natural streams, irrigation ditches, setbacks
    - **WaterUtilityDistricts** - Water and sewer service providers
    - **BoulderWetlands** - Mapped wetland areas requiring protection
    - **FloodRegulatoryInfo** - Detailed flood parameters (BFE, floodway width)
  - **Fire Protection & Safety** (2 shared services):
    - **FireStations** - Fire station locations, service areas, ISO rating
    - **WildlandUrbanInterface** - WUI zones requiring IWUIC compliance
  - **Performance**: All 45+ layers query in parallel, complete in 3-4 seconds
  - **Enhanced Output**: Warning flags (⚠️, 🚨) for critical constraints
  - **Both Jurisdictions**: Shared services apply to City and County properties
  - **Updated gisService.ts** - Added 18 service endpoints, query logic, data extraction
  - **Created GIS_EXPANSION_ANALYSIS.md** - Comprehensive analysis of all 60+ available services
  - **Documentation**: Updated CLAUDE.md with new layer counts and capabilities

### 2025-11-01 (v2.5.0 - Environmental & Urban Context)
- ✅ **ENVIRONMENTAL & URBAN CONTEXT INTEGRATION** - Added four new data services
  - **Tree Inventory** (City of Boulder Urban Forestry) - Public tree inventory within 500 feet
    - Species identification and tree size data (DBH, height)
    - Significant tree flagging (DBH ≥ 12") and Landmark trees (DBH ≥ 30")
    - Boulder tree permit requirements and mitigation fee estimates
    - Protection requirements per Boulder Revised Code 6-3
  - **Air Quality Monitoring** (EPA AirNow) - Real-time air quality index data
    - Current AQI for PM2.5, PM10, and Ozone
    - HVAC filtration recommendations (MERV 8-16, HEPA)
    - LEED Indoor Environmental Quality credit guidance
    - Colorado wildfire smoke considerations and ASHRAE 62.1 compliance
  - **Contaminated Sites** (EPA Envirofacts) - Superfund site screening within 10 miles
    - EPA Superfund sites and NPL status identification
    - Environmental due diligence and Phase I ESA requirements (ASTM E1527-21)
    - Vapor intrusion risk assessment for foundation design
    - Property liability concerns and remediation guidance
  - **Transit Access Analysis** (RTD) - Public transit accessibility for LEED compliance
    - Distance to Rail, BRT, and Local Bus stops with walk time estimates
    - LEED v4.1 Location & Transportation credit calculations (up to 15 points)
    - Parking reduction opportunities (20-40% for TODs)
    - Boulder-specific routes (Flatiron Flyer, free local buses)
  - **Created services/treeService.ts** (242 lines)
  - **Created services/airQualityService.ts** (272 lines)
  - **Created services/contaminatedSitesService.ts** (326 lines)
  - **Created services/transitService.ts** (326 lines)
  - **Updated geminiService.ts** - Added 4 new AI function tools (14 total, up from 10)
  - **Updated utils/functionRegistry.ts** - Registered 4 new handlers with geocoding wrappers
  - **API Keys**: Optional VITE_AIRNOW_API_KEY for air quality (500 requests/hour free tier)

### 2025-11-01 (v2.2.0 - Comprehensive Site Analysis)
- ✅ **COMPLETE SITE ANALYSIS INTEGRATION** - Added three critical data services
  - **Solar Resource Data** (NREL APIs) - Solar irradiance, PV potential, passive solar design
    - DNI, GHI, latitude tilt irradiance data
    - 5kW residential PV system production estimates
    - Financial analysis and household offset calculations
    - Energy code solar-ready compliance (IECC)
  - **Elevation & Topography** (OpenTopography / USGS 3DEP) - Site grading, slope analysis
    - Site elevation with Boulder context
    - Slope percentage calculation from elevation data
    - Foundation type recommendations based on terrain
    - ADA accessibility analysis
    - Drainage implications and cost estimation
  - **Soil & Geotechnical** (USDA NRCS SSURGO) - Foundation design, drainage
    - Soil type, classification, and taxonomy
    - Drainage class and hydrologic group
    - Depth to bedrock/hardpan
    - Foundation recommendations (slab/crawl/basement)
    - Expansive soil alerts (critical for Boulder clay soils)
    - Geotechnical study requirements
  - **Created services/solarService.ts** (220 lines)
  - **Created services/elevationService.ts** (280 lines)
  - **Created services/soilService.ts** (250 lines)
  - **Added 3 new AI function tools** to Gemini
  - **Updated App.tsx** with solar, elevation, soil handlers
  - **Enhanced system instruction** with comprehensive site analysis capabilities

### 2025-11-01 (v2.1.0 - Weather & Climate Data)
- ✅ **WEATHER AND CLIMATE INTEGRATION** - Added comprehensive weather/climate data service
  - **NOAA Weather.gov API** - Current conditions (temperature, humidity, wind) - free, no API key
  - **Visual Crossing API** - Climate data (HDD/CDD, design temperatures) - free tier 1000/day
  - **Heating/Cooling Degree Days** - Base 65°F for energy code compliance (IECC)
  - **Design Temperatures** - 99% heating / 1% cooling per ASHRAE standards for HVAC sizing
  - **Climate Normals** - January/July averages, annual precipitation/snowfall
  - **Created services/weatherService.ts** - Dual-API integration with graceful fallback
  - **Updated geminiService.ts** - Added getWeatherDataForLocation function tool
  - **Updated App.tsx** - Added weather function handler
  - **Exported geocodeAddress** from gisService.ts for reuse
  - **Architectural context** - Data formatted specifically for building design use cases

### 2025-11-01 (v2.0.0 - MAJOR RELEASE)
- ✅ **COMPREHENSIVE GIS INTEGRATION** - Implemented all available data layers
  - **27 total GIS layers** now queried for every address lookup
  - **City of Boulder** (13 layers): Zoning, Floodplain, Historic Landmarks, Historic Districts, Geologic Constraints, Future Land Use, Area Plans, City Limits, Annexation, Parcels, ADUs, plus County building code layers
  - **Boulder County** (15 layers): Zoning, Floodplain, Wildfire, View Protection, Airport Influence, Natural Resource Protection, Telecom Zones, Historic Sites/Districts/Townsites, Environmental Conservation, Wildlife Migration, Riparian Habitat, Snow Load, Wind Load
  - **Parallel query execution** with Promise.all() for performance
  - **Smart formatting** with ⚠️ and 🚨 emoji flags for critical constraints
  - **Automatic null filtering** for cleaner output
  - **Created GIS_LAYERS_CATALOG.md** - Complete catalog of all 27 layers
- ✅ **CRITICAL FIX**: Verified and restored GIS service functionality
  - Located all five official MapServer endpoints
  - Tested with spatial queries on real coordinates
  - Updated gisService.ts with verified URLs
  - Mapped correct field names from service responses
  - Created comprehensive verification report (GIS_ENDPOINTS_VERIFIED.md)
- ✅ Created comprehensive GIS technical architecture documentation (GIS_ARCHITECTURE.md)
- ✅ Documented all ArcGIS REST API integration points with citations
- ✅ Implemented version numbering scheme
- ✅ Added version display in UI header
- ✅ Replaced orange theme with cool medium grey (slate palette)
- ✅ Build process verified working

### Previous Recent Work
- Implemented Tailwind CSS build process
- Added Claude-inspired theme with light/dark mode
- Resolved console errors and warnings
- Added system theme detection
- Camera support added (for site plan photos)

## Future Enhancements

### Immediate Priorities
1. **GIS Service URLs**: Identify correct current endpoints from Boulder County
2. **Error Handling**: Improve user-facing error messages
3. **Testing**: Comprehensive test plan exists in `TEST_PLAN.md`

### Potential Features
- PDF site plan parsing
- Address autocomplete
- Code citation linking
- Permit requirement checklist
- Project document storage

## Testing Notes

See `TEST_PLAN.md` for comprehensive testing strategy including:
- Address geocoding tests
- GIS layer queries
- Jurisdiction determination
- UI/UX testing scenarios
- Performance benchmarks

## Environment Variables

Key environment variables (not in git):
- `VITE_GEMINI_API_KEY` - Google Gemini API key (required)
- `GA_MEASUREMENT_ID` - Google Analytics 4 Measurement ID (optional, for usage analytics)
  - Format: `G-XXXXXXXXXX`
  - **Default**: `G-CWFR3T2926` (production analytics)
  - Tracks user interactions, function calls, and errors
  - Privacy-friendly: IP addresses are anonymized
  - Can be overridden by setting environment variable
  - Sign up: https://analytics.google.com/
- `VISUAL_CROSSING_API_KEY` - Visual Crossing Weather API key (optional, for climate data)
  - Free tier: 1000 records/day
  - Without this key, weather service falls back to NOAA only (current conditions)
  - Sign up: https://www.visualcrossing.com/weather-api
- `VITE_AIRNOW_API_KEY` - EPA AirNow API key (optional, for air quality data)
  - Free tier: 500 requests/hour
  - Without this key, air quality service displays configuration instructions
  - Sign up: https://docs.airnowapi.org/account/request/
- `NREL_API_KEY` - NREL Solar Resource API key (optional)
  - DEMO_KEY included (30 requests/hour)
  - Free production key available at: https://developer.nrel.gov/signup/
- `OPENTOPOGRAPHY_API_KEY` - OpenTopography Elevation API key (optional)
  - Free tier: 300 calls/day (academic), 100 calls/day (commercial)
  - Sign up: https://opentopography.org/
  - Without this key, elevation service displays configuration instructions
- USDA Soil Data Access - No API key required (public service)
- EPA Envirofacts (Superfund sites) - No API key required (public service)
- City of Boulder Tree Inventory - No API key required (public ArcGIS service)
- RTD Transit Data - No API key required (static station data)
- Other config in Cloud Run environment

## Code Style and Patterns

### TypeScript
- Strict typing enabled
- Interfaces defined in `types.ts`
- Async/await for all service calls

### React Patterns
- Functional components with hooks
- useRef for chat instance
- useState for reactive state
- useEffect for theme initialization

### Error Handling
- Try-catch blocks in service layers
- User-friendly error messages
- Console logging via `utils/logger.ts`

## Quick Reference

### Updating Version Number
1. Edit `version.ts` and update:
   - `VERSION` - Use semantic versioning (e.g., "1.1.0")
   - `BUILD_DATE` - Current date (YYYY-MM-DD format)
   - `VERSION_NAME` - Optional release name
2. Run `npm run build`
3. Commit changes with version number in commit message
4. Deploy to production
5. Update `Claude.md` Recent Changes Log

**Version Guidelines**:
- MAJOR (x.0.0): Breaking changes, major redesigns
- MINOR (1.x.0): New features, UI improvements
- PATCH (1.0.x): Bug fixes, small tweaks

### Adding a New AI Function Tool
1. Define function in `services/geminiService.ts` tools array
2. Implement handler in `App.tsx` toolResponses mapping
3. Create service function if external API needed
4. Update system instruction to reference new capability

### Modifying Theme Colors
1. Edit `theme.ts` lightTheme and darkTheme objects
2. Run `npm run build`
3. Refresh browser

### Debugging GIS Issues
See `GIS_ARCHITECTURE.md` for comprehensive troubleshooting guide. Quick checklist:
1. Check browser console for service URLs being called
2. Verify logger output in Console component
3. Test URLs directly with curl or Postman
4. Verify service metadata with `?f=json` parameter
5. Check CORS headers if requests are blocked
6. Review ArcGIS REST API documentation

### Working with GIS Services
See `GIS_ARCHITECTURE.md` for:
- Complete API documentation and examples
- Testing procedures with sample curl commands
- Data flow architecture diagrams
- Security and performance considerations
- Step-by-step re-enabling instructions
- All citations and references
