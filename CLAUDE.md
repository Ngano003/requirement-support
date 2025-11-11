# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Japanese requirements definition support AI system that helps engineers create and review requirements documents through AI-powered breakdown and analysis. The system uses LLMs (via OpenRouter or vLLM) to generate requirement drafts, ask clarifying questions, and review documents for completeness and consistency.

**Core Features:**
- **Breakdown Mode**: Transforms meeting notes into structured requirements documents through iterative Q&A
- **Review Mode**: Analyzes requirements documents for gaps, contradictions, and quality issues
- **Dual-Panel UI**: Real-time markdown preview (left) + chat interface (right)

## Architecture

This is a **monorepo with separate backend and frontend**:

```
backend/   → FastAPI (Python 3.10+) - REST API
frontend/  → Next.js 14 App Router (TypeScript)
data/      → File-based storage (sessions + requirements)
docs/      → Architecture and design docs
```

**Key Design Patterns:**
- Backend follows a **service-oriented architecture**: API routes → Services → LLM Service
- Frontend uses **Zustand** for state management
- LLM abstraction layer supports both **OpenRouter** (dev/test) and **vLLM** (production)
- Sessions are stored as JSON files, requirements as Markdown files

**Phase 2 Expansions (planned):**
- GraphRAG + Neo4j for relationship graph analysis
- Git integration for automatic version control

## Development Commands

### Docker Compose (Recommended)

The easiest way to get started is with Docker Compose, which starts both backend and frontend:

```bash
# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Start all services (backend + frontend)
docker-compose up

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up --build

# Clean everything (including volumes)
docker-compose down -v
```

Services will be available at:
- Frontend: http://localhost:3000
- Backend: http://localhost:8001
- API Docs: http://localhost:8001/docs

### Dev Container (VS Code)

For development with VS Code Dev Containers:

1. Install "Dev Containers" extension in VS Code
2. Open the project in VS Code
3. Press `F1` → "Dev Containers: Reopen in Container"
4. VS Code will build and connect to the container
5. Inside the container, run:
   ```bash
   # Start backend
   cd /app && uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

   # Or in a separate terminal, start frontend
   cd /workspace/frontend && npm run dev
   ```

The devcontainer includes Python and Node.js development tools with proper extensions.

### Manual Development (Without Docker)

#### Backend (FastAPI)

```bash
# Setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Run development server (default port 8001)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Run tests
pytest
```

#### Frontend (Next.js)

```bash
# Setup
cd frontend
npm install

# Copy and configure environment
cp .env.example .env.local
# Edit .env.local (set NEXT_PUBLIC_API_URL=http://localhost:8001)

# Run development server (default port 3000)
npm run dev

# Build for production
npm run build

# Run linter
npm run lint
```

### Environment Configuration

**Backend (.env)**:
```env
# Development with OpenRouter
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-key
OPENROUTER_MODEL=qwen/qwen-2.5-coder-32b-instruct

# Production with vLLM
LLM_PROVIDER=vllm
VLLM_API_BASE=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct
```

**Frontend (.env.local)**:
```env
NEXT_PUBLIC_API_URL=http://localhost:8001
```

## Code Architecture Details

### Backend Service Layer

The backend follows a three-tier architecture:

1. **API Layer** (`app/api/`): FastAPI route handlers
   - `breakdown.py`: Breakdown feature endpoints
   - `review.py`: Review feature endpoints

2. **Service Layer** (`app/services/`): Business logic
   - `breakdown_service.py`: Manages breakdown sessions, generates questions, updates requirements
   - `review_service.py`: Analyzes requirements for issues and quality
   - `llm_service.py`: **Core abstraction for LLM interactions** - handles both OpenRouter and vLLM

3. **Utilities** (`app/utils/`):
   - `session_manager.py`: File-based session persistence (JSON)
   - `config.py`: Environment configuration management

**Critical Pattern**: All LLM calls go through `llm_service.py` which uses OpenAI-compatible API format. This allows swapping between OpenRouter and vLLM seamlessly.

### Frontend Architecture

- **App Router** (`src/app/`): Next.js 14 pages with server/client components
  - `page.tsx`: Home page with feature selection
  - `breakdown/page.tsx`: Breakdown interface with dual-panel layout
  - `review/page.tsx`: Review interface

- **Components** (`src/components/`):
  - `MarkdownViewer.tsx`: Renders requirements documents
  - `ChatInterface.tsx`: Question/answer UI for breakdown mode

- **State Management**: Uses Zustand for managing session state, questions, and requirements

### Data Flow (Breakdown Feature)

1. User submits meeting notes → `POST /api/breakdown/initialize`
2. `breakdown_service.initialize_session()` calls LLM twice:
   - First: Generate requirements draft
   - Second: Generate clarifying questions (JSON format)
3. Session saved to `data/sessions/{session_id}.json`
4. Requirements saved to `data/requirements/{session_id}.md`
5. User answers question → `POST /api/breakdown/answer`
6. Service updates requirements and generates new questions
7. Loop continues until user is satisfied

### LLM Integration

The `llm_service.py` is the **single point of contact** for all LLM operations:
- Uses OpenAI Python SDK (works with OpenRouter and vLLM)
- Configurable via `LLM_PROVIDER` environment variable
- Supports system prompts and temperature control
- Both services use structured prompts to guide LLM behavior

**Important**: The system heavily relies on prompt engineering. System prompts define the AI's role as a requirements engineer. User prompts include structured instructions with clear output format expectations.

## Docker Architecture

### Multi-Stage Dockerfiles

Both backend and frontend use multi-stage builds:

- **Backend Dockerfile**: Has `base`, `development`, and `production` stages
- **Frontend Dockerfile**: Has `base`, `development`, `builder`, and `production` stages

Development stage includes hot reload capabilities. Production stage is optimized for deployment.

### Volume Mounts

When running with docker-compose:
- Backend code is mounted for hot reload: `./backend:/app`
- Frontend code is mounted for hot reload: `./frontend:/app`
- Data directory is shared: `./data:/data`
- Frontend node_modules and .next are anonymous volumes to avoid conflicts

### Networking

All services run in a custom bridge network (`requirement-support-network`) allowing them to communicate using service names.

## Testing Strategy

- Backend tests use `pytest` with `pytest-asyncio` for async tests
- Test files should be placed in `backend/tests/`
- Mock the LLM service when testing to avoid API calls

## File Storage Conventions

- **Sessions**: `data/sessions/{session_id}.json` - Contains full session state
- **Requirements**: `data/requirements/{session_id}.md` - Markdown documents
- Session IDs are UUIDs generated by `breakdown_service`

## Important Considerations

1. **Language**: All requirements documents and UI are in **Japanese**
2. **LLM Model**: System is optimized for Qwen2.5-Coder (coding-focused model)
3. **No Database**: Current implementation uses file-based storage
4. **CORS**: Backend allows `localhost:3000` and `localhost:3001` origins
5. **Port Allocation**: Backend on 8001, Frontend on 3000 (avoid conflicts)
6. **Data Persistence**: The `data/` directory contains all generated requirements and sessions

## Common Tasks

**Add a new API endpoint:**
1. Define route in `backend/app/api/`
2. Implement business logic in `backend/app/services/`
3. Update schemas in `backend/app/models/schemas.py` if needed
4. Register router in `backend/app/main.py`

**Modify LLM behavior:**
- Edit the `SYSTEM_PROMPT` in respective service classes
- Adjust prompt templates in service methods
- Consider temperature parameter (0.5 for structured output, higher for creativity)

**Add new UI features:**
- Create components in `frontend/src/components/`
- Add pages under `frontend/src/app/`
- Update state management if global state is needed

**Debug inside Docker:**
```bash
# Access backend container
docker-compose exec backend bash

# Access frontend container
docker-compose exec frontend sh

# View live logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Documentation

Always refer to these documents for detailed specifications:
- `requirements.md`: Full project requirements (Japanese)
- `docs/architecture.md`: Detailed architecture specifications
- `docs/USAGE.md`: User guide
- `docs/graphrag-architecture.md`: Phase 2 GraphRAG plans
