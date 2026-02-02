# Technology Stack

## Backend

**Framework**: FastAPI 0.109.0 with Uvicorn
- Python 3.9+ required
- Async/await support for I/O operations
- Automatic OpenAPI documentation at `/docs`
- Pydantic v2 for data validation and type safety

**Key Libraries**:
- `pyyaml` - YAML configuration management
- `requests` - HTTP client for LM Studio API
- `pypdfium2` - PDF rendering and processing
- `Pillow` - Image processing
- `python-multipart` - File upload handling

**Configuration**: YAML-based (`backend/config/config.yaml`) with environment variable overrides

## Frontend

**Framework**: Nuxt 3 with Vue 3 Composition API
- Node.js 18+ required
- TypeScript strict mode enabled
- Auto-imports for components and composables

**Key Libraries**:
- `@nuxtjs/tailwindcss` - Utility-first CSS framework
- `marked` - Markdown parsing for results display
- `vue-router` - Client-side routing

**State Management**: Nuxt `useState` for global state (no Vuex/Pinia needed)

## External Dependencies

**LM Studio**: Local inference server for OCR models
- Runs at `http://localhost:1234` by default
- OpenAI-compatible API endpoints
- Supports GGUF quantized models

## Common Commands

### Backend

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run development server (with auto-reload)
python main.py

# Run production server
uvicorn main:app --host 0.0.0.0 --port 8000

# Test configuration
python demo_config.py
```

### Frontend

```bash
# Install dependencies
cd frontend
npm install

# Run development server (with HMR)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Generate static site
npm run generate
```

### Full Stack

```bash
# Terminal 1: Start backend
cd backend && python main.py

# Terminal 2: Start frontend
cd frontend && npm run dev

# Terminal 3: Ensure LM Studio is running
# Open LM Studio and start server with OCR model loaded
```

## Environment Variables

**Backend**:
- `LM_STUDIO_BASE_URL` - Override LM Studio URL (default: http://localhost:1234)
- `DEFAULT_MODEL_ID` - Override default OCR model
- `UPLOAD_FOLDER` - Override upload directory (default: uploads)
- `MAX_FILE_SIZE_MB` - Override max file size (default: 10)

**Frontend**:
- `API_BASE_URL` - Backend API URL (default: http://localhost:8000)

## Testing

**Backend**: Manual testing scripts provided
- `demo_config.py` - Test configuration loading
- `test_routes_extraction.py` - Test extraction endpoints
- `test_extraction_config.py` - Test extraction configuration

**Frontend**: Vitest for component testing
- `SchemaBuilder.test.ts` - Schema builder component tests
- `ConfigPanel.test.ts` - Config panel component tests

## Build System

**Backend**: No build step required (Python interpreted)
- Configuration validation on startup
- Hot reload in development mode

**Frontend**: Vite-based build via Nuxt
- TypeScript compilation
- TailwindCSS JIT compilation
- Auto-import resolution
- Code splitting and tree shaking
