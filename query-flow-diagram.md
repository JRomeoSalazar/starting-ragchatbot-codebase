# RAG Chatbot Query Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  FRONTEND                                    │
│                            (script.js + index.html)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    User types: "What is in lesson 3 of MCP?"
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  sendMessage() triggered        │
                    │  • Display user message         │
                    │  • Show loading animation       │
                    │  • Disable input                │
                    └─────────────────────────────────┘
                                      │
                                      │ HTTP POST
                                      ▼
                    ╔═════════════════════════════════╗
                    ║   POST /api/query               ║
                    ║   Body: {                       ║
                    ║     query: "What is in...",     ║
                    ║     session_id: "session_1"     ║
                    ║   }                             ║
                    ╚═════════════════════════════════╝
                                      │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND - API LAYER                             │
│                                  (app.py)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  @app.post("/api/query")        │
                    │  • Validate request             │
                    │  • Create/get session_id        │
                    └─────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  rag_system.query(              │
                    │    query,                       │
                    │    session_id                   │
                    │  )                              │
                    └─────────────────────────────────┘
                                      │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                          RAG ORCHESTRATION LAYER                             │
│                              (rag_system.py)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
      ┌──────────────────────────┐      ┌──────────────────────────┐
      │  SessionManager          │      │  ToolManager             │
      │  • Get history           │      │  • Get tool definitions  │
      │  • Format context        │      │  • Register search tool  │
      └──────────────────────────┘      └──────────────────────────┘
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      ▼
                    ┌─────────────────────────────────┐
                    │  ai_generator.generate_response(│
                    │    query,                       │
                    │    conversation_history,        │
                    │    tools,                       │
                    │    tool_manager                 │
                    │  )                              │
                    └─────────────────────────────────┘
                                      │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AI GENERATION LAYER                               │
│                            (ai_generator.py)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  Build System Prompt:           │
                    │  • Instructions for tool use    │
                    │  • Conversation history         │
                    │  • Response guidelines          │
                    └─────────────────────────────────┘
                                      │
                                      ▼
                    ╔═════════════════════════════════╗
                    ║  CLAUDE API CALL #1             ║
                    ║  ────────────────────           ║
                    ║  Model: claude-sonnet-4         ║
                    ║  Messages: [user query]         ║
                    ║  Tools: [search_course_content] ║
                    ║  System: [prompt + history]     ║
                    ╚═════════════════════════════════╝
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  Claude Response:               │
                    │  {                              │
                    │    stop_reason: "tool_use",     │
                    │    content: [{                  │
                    │      type: "tool_use",          │
                    │      name: "search_course_...", │
                    │      input: {                   │
                    │        query: "lesson 3",       │
                    │        course_name: "MCP",      │
                    │        lesson_number: 3         │
                    │      }                          │
                    │    }]                           │
                    │  }                              │
                    └─────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  tool_manager.execute_tool(     │
                    │    "search_course_content",     │
                    │    **tool_input                 │
                    │  )                              │
                    └─────────────────────────────────┘
                                      │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TOOL EXECUTION                                  │
│                            (search_tools.py)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  CourseSearchTool.execute()     │
                    │  • Validate parameters          │
                    │  • Call vector store            │
                    └─────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  vector_store.search(           │
                    │    query: "lesson 3",           │
                    │    course_name: "MCP",          │
                    │    lesson_number: 3             │
                    │  )                              │
                    └─────────────────────────────────┘
                                      │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VECTOR SEARCH LAYER                                │
│                            (vector_store.py)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
      ┌──────────────────────────┐      ┌──────────────────────────┐
      │  STEP 1:                 │      │  ChromaDB Collections:   │
      │  Resolve Course Name     │      │  • course_catalog        │
      │                          │      │  • course_content        │
      │  Query: "MCP"            │      │                          │
      │      ↓                   │      │  Embedding Model:        │
      │  Search course_catalog   │      │  all-MiniLM-L6-v2        │
      │      ↓                   │      └──────────────────────────┘
      │  Returns: "MCP: Build    │
      │  Rich-Context AI Apps    │
      │  with Anthropic"         │
      └──────────────────────────┘
                    │
                    ▼
      ┌──────────────────────────┐
      │  STEP 2:                 │
      │  Build Filter            │
      │                          │
      │  filter = {              │
      │    "$and": [             │
      │      {course_title: ...},│
      │      {lesson_number: 3}  │
      │    ]                     │
      │  }                       │
      └──────────────────────────┘
                    │
                    ▼
      ┌──────────────────────────┐
      │  STEP 3:                 │
      │  Semantic Search         │
      │                          │
      │  course_content.query(   │
      │    query_texts=["..."],  │
      │    n_results=5,          │
      │    where=filter          │
      │  )                       │
      │                          │
      │  Returns top 5 chunks    │
      │  by embedding similarity │
      └──────────────────────────┘
                    │
                    ▼
      ┌──────────────────────────────────────┐
      │  SearchResults:                      │
      │  ─────────────                       │
      │  documents: [                        │
      │    "Lesson 3 content: In this...",   │
      │    "Lesson 3 content: We cover...",  │
      │    ...                               │
      │  ]                                   │
      │  metadata: [                         │
      │    {course_title: "...",             │
      │     lesson_number: 3,                │
      │     chunk_index: 15},                │
      │    ...                               │
      │  ]                                   │
      └──────────────────────────────────────┘
                    │
                    │ Return to search_tools.py
                    ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                            BACK TO TOOL LAYER                                │
│                            (search_tools.py)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  Format Results:                │
                    │                                 │
                    │  "[MCP: ... - Lesson 3]         │
                    │   Lesson 3 content: In this..." │
                    │                                 │
                    │  "[MCP: ... - Lesson 3]         │
                    │   Lesson 3 content: We cover..."│
                    │                                 │
                    │  Store sources: [               │
                    │    "MCP: ... - Lesson 3"        │
                    │  ]                              │
                    └─────────────────────────────────┘
                                      │
                    │ Return formatted string to ai_generator.py
                    ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACK TO AI GENERATION                                │
│                            (ai_generator.py)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  Build Tool Result Message:     │
                    │                                 │
                    │  messages = [                   │
                    │    {role: "user",               │
                    │     content: original_query},   │
                    │    {role: "assistant",          │
                    │     content: tool_use_blocks},  │
                    │    {role: "user",               │
                    │     content: [{                 │
                    │       type: "tool_result",      │
                    │       tool_use_id: "...",       │
                    │       content: formatted_results│
                    │     }]}                         │
                    │  ]                              │
                    └─────────────────────────────────┘
                                      │
                                      ▼
                    ╔═════════════════════════════════╗
                    ║  CLAUDE API CALL #2             ║
                    ║  ────────────────────           ║
                    ║  Model: claude-sonnet-4         ║
                    ║  Messages: [full conversation]  ║
                    ║  System: [prompt + history]     ║
                    ║  Tools: NONE (no infinite loop) ║
                    ╚═════════════════════════════════╝
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  Claude Synthesizes Answer:     │
                    │                                 │
                    │  "Lesson 3 of the MCP course    │
                    │   covers the following topics:  │
                    │   • Topic 1...                  │
                    │   • Topic 2...                  │
                    │   ..."                          │
                    └─────────────────────────────────┘
                                      │
                    │ Return response text
                    ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACK TO RAG ORCHESTRATION                            │
│                              (rag_system.py)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
      ┌──────────────────────────┐      ┌──────────────────────────┐
      │  SessionManager          │      │  ToolManager             │
      │  • Store exchange        │      │  • Get last sources      │
      │  • Keep last 4 messages  │      │  • Reset sources         │
      └──────────────────────────┘      └──────────────────────────┘
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      ▼
                    ┌─────────────────────────────────┐
                    │  Return:                        │
                    │  • answer: "Lesson 3..."        │
                    │  • sources: ["MCP: ... - L3"]   │
                    │  • session_id: "session_1"      │
                    └─────────────────────────────────┘
                                      │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACK TO API LAYER                                  │
│                                  (app.py)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  Return QueryResponse:          │
                    │  {                              │
                    │    answer: "Lesson 3...",       │
                    │    sources: ["MCP: ... - L3"],  │
                    │    session_id: "session_1"      │
                    │  }                              │
                    └─────────────────────────────────┘
                                      │
                                      │ JSON Response
                                      ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  FRONTEND                                    │
│                            (script.js + UI)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  Receive Response:              │
                    │  • Remove loading animation     │
                    │  • Parse markdown (marked.js)   │
                    │  • Display formatted answer     │
                    │  • Show sources dropdown        │
                    │  • Re-enable input              │
                    └─────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  User Sees:                     │
                    │  ┌───────────────────────────┐  │
                    │  │ Lesson 3 of the MCP       │  │
                    │  │ course covers:            │  │
                    │  │ • Topic 1...              │  │
                    │  │ • Topic 2...              │  │
                    │  │                           │  │
                    │  │ ▼ Sources                 │  │
                    │  │   MCP: ... - Lesson 3     │  │
                    │  └───────────────────────────┘  │
                    └─────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                            KEY COMPONENTS SUMMARY
═══════════════════════════════════════════════════════════════════════════════

┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│   ChromaDB       │   │  Sentence        │   │  Claude Sonnet   │
│   Vector Store   │   │  Transformers    │   │  4 API           │
│                  │   │                  │   │                  │
│  • course_       │   │  Model:          │   │  • Temperature 0 │
│    catalog       │   │  all-MiniLM-L6-v2│   │  • Max 800 tok   │
│  • course_       │   │                  │   │  • Tool calling  │
│    content       │   │  Generates       │   │  • 2 API calls   │
│                  │   │  embeddings      │   │    per query     │
└──────────────────┘   └──────────────────┘   └──────────────────┘

┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  Session         │   │  Document        │   │  RAG System      │
│  Manager         │   │  Processor       │   │  Orchestrator    │
│                  │   │                  │   │                  │
│  • Stores last   │   │  • 800 char      │   │  • Coordinates   │
│    4 messages    │   │    chunks        │   │    all layers    │
│  • Per-session   │   │  • 100 overlap   │   │  • Tool-based    │
│    history       │   │  • Context       │   │    RAG pattern   │
│                  │   │    prefixes      │   │                  │
└──────────────────┘   └──────────────────┘   └──────────────────┘
```

## Key Flow Characteristics

1. **Two-Stage LLM Process**: Claude is called twice - once to decide tools, once to generate answer
2. **Semantic Course Matching**: "MCP" fuzzy-matches to full course title via embeddings
3. **Tool-Based RAG**: Not automatic retrieval - Claude decides when to search
4. **Context Preservation**: Session history included in both Claude calls
5. **Source Tracking**: UI displays which course/lesson chunks were used
6. **Markdown Rendering**: Frontend uses marked.js for formatted display
