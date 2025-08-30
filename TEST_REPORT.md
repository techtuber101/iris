# Iris System Test Report

**Generated:** 2025-08-23 16:12:10

**Summary:** 12/19 tests passed

## Test Results

- ✅ **Environment var OPENAI_API_KEY**: Set
- ❌ **Environment var SUPABASE_URL**: Not set
- ❌ **Environment var SUPABASE_ANON_KEY**: Not set
- ✅ **Debug mode detection**: Debug mode: OFF
- ❌ **Share routes import**: No module named 'litellm'
- ❌ **Agent orchestrator import**: No module named 'litellm'
- ✅ **Debug utils import**
- ❌ **XML chunk extraction**
- ❌ **XML tool parsing**: Found 0 tool calls
- ❌ **Multiple XML tools**: Found 0 tool calls
- ✅ **Malformed XML handling**: Handled gracefully
- ✅ **String/bytes conversion**
- ✅ **Sentinel cleaning**: Cleaned: 'Hello world
Extra content'
- ✅ **Parameter defaults**
- ✅ **Routing: 'What is the capital of France?...'**: Expected direct, got direct
- ✅ **Routing: 'Search the web for recent AI n...'**: Expected agentic, got agentic
- ✅ **Routing: 'Hello, how are you?...'**: Expected direct, got direct
- ✅ **Routing: 'Download the latest data from ...'**: Expected agentic, got agentic
- ✅ **Message normalization**: Normalized 3/3 messages

## Failed Tests

### Environment var SUPABASE_URL
**Error:** Not set

### Environment var SUPABASE_ANON_KEY
**Error:** Not set

### Share routes import
**Error:** No module named 'litellm'

### Agent orchestrator import
**Error:** No module named 'litellm'

### XML chunk extraction
**Error:** 

### XML tool parsing
**Error:** Found 0 tool calls

### Multiple XML tools
**Error:** Found 0 tool calls

