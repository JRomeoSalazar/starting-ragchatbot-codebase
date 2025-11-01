# RAG Chatbot Test Suite

## Overview

Comprehensive test suite for the RAG chatbot system covering CourseSearchTool, AIGenerator, and RAGSystem integration.

## Test Results

**Total Tests**: 38
**Passed**: 37 (97.4%)
**Failed**: 1 (2.6%)

## Quick Start

### Run All Tests
```bash
cd backend
uv run pytest tests/ -v
```

### Run Specific Test File
```bash
# Test search tools
uv run pytest tests/test_search_tools.py -v

# Test AI generator
uv run pytest tests/test_ai_generator.py -v

# Test RAG system integration
uv run pytest tests/test_rag_system.py -v
```

### Run Single Test
```bash
uv run pytest tests/test_search_tools.py::TestCourseSearchTool::test_execute_query_only -v
```

## Test Coverage

### 1. CourseSearchTool Tests (9 tests)
**File**: `test_search_tools.py`

Tests the search tool's ability to:
- Execute searches with various filter combinations
- Format results with course/lesson context
- Track sources for UI display
- Handle empty results and errors

### 2. ToolManager Tests (6 tests)
**File**: `test_search_tools.py`

Tests tool orchestration:
- Tool registration and retrieval
- Tool execution by name
- Source tracking and reset
- Error handling for non-existent tools

### 3. CourseOutlineTool Tests (2 tests)
**File**: `test_search_tools.py`

Tests course outline retrieval:
- Valid course outline fetching
- Non-existent course handling

### 4. AIGenerator Tests (9 tests)
**File**: `test_ai_generator.py`

Tests Claude API interaction:
- Direct responses without tools
- Tool calling flow (two-call pattern)
- Message structure for tool execution
- **Critical**: Second call omits tools (prevents infinite loops)
- Conversation history integration
- Multiple tool calls handling

### 5. RAGSystem Integration Tests (12 tests)
**File**: `test_rag_system.py`

Tests end-to-end query flow:
- Query routing (with/without tools)
- Source tracking and reset
- Conversation history management
- Error propagation
- Course document processing

## Known Issues

### 1. Conversation History Bug (MEDIUM severity)
**Status**: ❌ 1 test failing
**Test**: `test_rag_system.py::TestRAGSystemIntegration::test_conversation_history`
**Location**: `backend/rag_system.py:139`

**Issue**: System stores raw user query in history but sends formatted prompt to AI, causing context mismatch in multi-turn conversations.

**Fix**: Change line 139 from:
```python
self.session_manager.add_exchange(session_id, query, response)
```

To:
```python
self.session_manager.add_exchange(session_id, prompt, response)
```

**See**: `FIX_PROPOSAL.md` for detailed fix instructions

## Test Files

### `conftest.py`
Shared fixtures for all tests:
- Mock configurations
- Mock VectorStore with sample data
- Mock Anthropic API responses
- Mock ToolManager and SessionManager
- Sample course data and search results

### `test_search_tools.py`
Tests for search functionality:
- CourseSearchTool execution and formatting
- ToolManager orchestration
- CourseOutlineTool retrieval

### `test_ai_generator.py`
Tests for AI interaction:
- Response generation with/without tools
- Tool execution flow
- Message structure
- Conversation history integration

### `test_rag_system.py`
Integration tests:
- End-to-end query processing
- Component orchestration
- Source management
- Document processing

## Documentation

- **TEST_ANALYSIS.md**: Detailed analysis of all test results
- **FIX_PROPOSAL.md**: Comprehensive fix proposal for discovered bug
- **README.md**: This file

## Key Findings

### ✅ What's Working Well

1. **CourseSearchTool**: Correctly searches, filters, and formats results
2. **AIGenerator**: Properly implements two-call pattern to prevent infinite loops
3. **Tool Execution**: Tools are called correctly with proper parameter passing
4. **Source Tracking**: Sources are tracked and reset properly
5. **Error Handling**: Errors propagate correctly throughout the system

### ❌ What Needs Fixing

1. **Conversation History**: Raw query vs. formatted prompt mismatch (see FIX_PROPOSAL.md)

### 🔍 Critical Insights

**Two-Call Pattern Validation** ✅:
The tests confirm that the AIGenerator correctly implements the critical two-call pattern:
1. **First call**: Includes tools → Claude decides to use them
2. **Tool execution**: Results collected
3. **Second call**: **NO tools parameter** → Prevents infinite loops

This is the foundation of tool-based RAG and the tests validate it's working correctly.

## Running Tests in CI/CD

### GitHub Actions Example
```yaml
- name: Run tests
  run: |
    cd backend
    uv sync
    uv run pytest tests/ -v --tb=short
```

### Test Coverage Report
```bash
cd backend
uv run pytest tests/ --cov=. --cov-report=html
```

## Adding New Tests

### 1. Add fixtures to `conftest.py` if needed
### 2. Create test class in appropriate file
### 3. Use descriptive test names: `test_<action>_<scenario>`
### 4. Mock external dependencies (VectorStore, Anthropic API)
### 5. Assert both behavior and interactions

Example:
```python
def test_my_new_feature(self, mock_vector_store):
    """Test description"""
    # Arrange
    tool = CourseSearchTool(mock_vector_store)

    # Act
    result = tool.execute(query="test")

    # Assert
    assert result is not None
    mock_vector_store.search.assert_called_once()
```

## Troubleshooting

### Import Errors
Make sure you're running from the `backend` directory:
```bash
cd backend
uv run pytest tests/
```

### Fixture Not Found
Check that `conftest.py` is in the `tests/` directory and contains the fixture.

### Mock Not Working
Verify you're patching the correct import path. Use the path where the object is used, not where it's defined.

## Next Steps

1. **Fix the Bug**: Apply the fix in `FIX_PROPOSAL.md`
2. **Re-run Tests**: Verify all 38 tests pass
3. **Manual Testing**: Test multi-turn conversations
4. **Add More Tests**: Consider adding real integration tests with ChromaDB
5. **Performance Tests**: Add tests for response time and token usage

## Questions?

See the detailed documentation:
- **TEST_ANALYSIS.md**: For comprehensive test analysis
- **FIX_PROPOSAL.md**: For fix implementation details
