# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Retrieval-Augmented Generation (RAG) chatbot for course materials built with FastAPI, ChromaDB, Anthropic Claude, and vanilla JavaScript. The system uses **tool-based RAG** where Claude autonomously decides when to search rather than automatic retrieval on every query.

## Running the Application

### Quick Start
```bash
./run.sh
```
This starts the FastAPI server on port 8000 with auto-reload enabled.

### Manual Start
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

### Access Points
- Web UI: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs
- API endpoint: http://localhost:8000/api/query

### Prerequisites
- Python 3.13+
- uv package manager
- `ANTHROPIC_API_KEY` in `.env` file

### Installing Dependencies
```bash
uv sync
```

## Architecture

### RAG Flow Pattern: Two-Stage Claude API Calls

This system uses a **tool-based RAG pattern** with two distinct Claude API calls per query:

1. **First Call**: Claude receives the query + tool definitions, decides if/when to use the `search_course_content` tool
2. **Tool Execution**: If Claude requests a tool, we execute the search against ChromaDB
3. **Second Call**: Claude receives tool results and synthesizes the final answer (no tools parameter to prevent loops)

### Core Components

**Backend Structure** (`backend/`):

- **`app.py`**: FastAPI application, REST endpoints, static file serving
- **`rag_system.py`**: Main orchestrator coordinating all RAG components
- **`ai_generator.py`**: Handles Claude API interactions and tool execution flow
- **`search_tools.py`**: Tool interface (`CourseSearchTool`) and `ToolManager` for registering/executing tools
- **`vector_store.py`**: ChromaDB wrapper with two collections:
  - `course_catalog`: Course metadata for semantic course name resolution
  - `course_content`: Actual chunked content with lesson metadata
- **`document_processor.py`**: Parses course documents, extracts metadata, creates sentence-based chunks (800 chars, 100 overlap)
- **`session_manager.py`**: Conversation history (keeps last 4 messages per session)
- **`config.py`**: Configuration dataclass with environment variables
- **`models.py`**: Pydantic models (`Course`, `Lesson`, `CourseChunk`)

**Frontend** (`frontend/`):
- Vanilla HTML/CSS/JavaScript
- Uses marked.js for markdown rendering
- Single-page application with chat interface

### Document Processing Pipeline

Documents in `docs/` folder are processed on startup:

1. **Parse Structure**: Extract metadata from first 3 lines (Course Title, Link, Instructor)
2. **Detect Lessons**: Regex pattern `Lesson N: Title` for lesson boundaries
3. **Chunk Text**: Sentence-based chunking with overlap
4. **Add Context**: Prefix chunks with course/lesson context (e.g., `"Course X Lesson 3 content: ..."`)
5. **Embed & Store**: Generate embeddings via `all-MiniLM-L6-v2`, store in ChromaDB with metadata

### Vector Search Strategy

Three-step search process in `vector_store.py`:

1. **Resolve Course Name**: If `course_name` provided, do semantic search on `course_catalog` to get exact title (handles partial matches like "MCP" → full title)
2. **Build Filter**: Construct ChromaDB `where` clause from course_title and/or lesson_number
3. **Content Search**: Query `course_content` collection with embeddings + metadata filters

### Session Management

- Creates unique session IDs (`session_1`, `session_2`, etc.)
- Stores last `MAX_HISTORY * 2` messages (default: 4 messages total)
- History is injected into Claude's system prompt on each call

### Configuration Values

Set in `backend/config.py`:
- Model: `claude-sonnet-4-20250514`
- Embedding: `all-MiniLM-L6-v2` (SentenceTransformers)
- Chunk size: 800 chars, overlap: 100 chars
- Max search results: 5
- Max conversation history: 2 exchanges (4 messages)
- Temperature: 0 (deterministic)
- Max tokens: 800

## Key Implementation Details

### Tool Execution Flow

The `AIGenerator._handle_tool_execution()` method:
1. Appends Claude's tool_use response to messages list
2. Executes all requested tools via `tool_manager.execute_tool()`
3. Builds tool_result messages with matching `tool_use_id`
4. Makes second API call **without** tools parameter (prevents infinite loops)

### Course Name Resolution

The system uses semantic search to resolve partial course names. When a user asks about "MCP", the vector store:
1. Queries `course_catalog` collection with "MCP" as query text
2. Returns best matching course title via embedding similarity
3. Uses exact title for filtering `course_content` collection

This allows fuzzy matching ("MCP" → "MCP: Build Rich-Context AI Apps with Anthropic").

### Source Tracking

- `CourseSearchTool` stores sources in `last_sources` list during result formatting
- `ToolManager.get_last_sources()` retrieves sources after query completes
- Sources are reset after each query to avoid stale data
- Frontend displays sources in collapsible dropdown

### Document Format Requirements

Course documents in `docs/` must follow this structure:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [title]
Lesson Link: [url]
[content]

Lesson 1: [title]
[content]
```

## Development Workflow

### Adding New Tools

1. Create tool class inheriting from `Tool` ABC in `search_tools.py`
2. Implement `get_tool_definition()` returning Anthropic tool schema
3. Implement `execute(**kwargs)` with tool logic
4. Register in `RAGSystem.__init__()` via `tool_manager.register_tool()`

### Modifying System Prompt

Edit `AIGenerator.SYSTEM_PROMPT` in `ai_generator.py`. This is a static class variable to avoid rebuilding on each call.

### Changing Chunk Strategy

Modify `DocumentProcessor.chunk_text()` in `document_processor.py`. Current strategy is sentence-based with overlap; alternative strategies (fixed-size, paragraph-based) would require changes here.

### Adding New API Endpoints

Add route handlers in `app.py`. Existing endpoints:
- `POST /api/query`: Main query endpoint (returns `QueryResponse`)
- `GET /api/courses`: Course statistics (returns `CourseStats`)

### Clearing Vector Database

```python
rag_system.vector_store.clear_all_data()
# Or delete backend/chroma_db/ directory
```

### Adding Course Documents

Place `.txt`, `.pdf`, or `.docx` files in `docs/` folder. Server restart triggers automatic processing via `app.py` startup event.

## Important Behavioral Notes

### Why Two Claude API Calls?

The two-call pattern is essential:
- **First call**: Claude must have tools available to decide usage
- **Second call**: Claude needs tool results to answer, but tools parameter must be omitted to prevent requesting more tools (infinite loop)

### Conversation History Limits

Sessions keep only last 4 messages (2 exchanges) to:
- Control token costs (history is in system prompt for both API calls)
- Prevent context window issues with long conversations
- Maintain reasonable latency

### Temperature = 0

Deterministic responses are used because:
- Chatbot should be consistent for same questions
- RAG systems benefit from predictable behavior
- Educational content requires accuracy over creativity

### Context Prefixes on Chunks

Chunks are prefixed with course/lesson context (e.g., "Course X Lesson 3 content: ...") because:
- Improves semantic search relevance (query embeddings match better)
- Helps Claude understand which lesson content comes from
- Reduces ambiguity in multi-course scenarios

## File Locations

- Course transcripts: `docs/*.txt`
- Vector DB: `backend/chroma_db/` (auto-created)
- Static frontend: `frontend/` (served by FastAPI)
- Environment config: `.env` (required)
- Dependencies: `pyproject.toml`, `uv.lock`
- always use uv to run the server do not use pip directly
- make sure to use uv to manage all dependencies
- use uv to run Python files