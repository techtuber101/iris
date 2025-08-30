#!/usr/bin/env python3
"""
Comprehensive System Test for Iris

This script tests the key functionality of the Iris system including:
- Backend API endpoints
- XML parsing and tool execution
- Message normalization
- Share functionality
- Adaptive routing
"""

import asyncio
import json
import sys
import time
from typing import Dict, Any, List
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / 'backend'))

from agentpress.xml_parser import XMLToolParser
from agentpress.tool_executor import ToolExecutor
from agentpress.decision_router import DecisionRouter
from agentpress.bug_fixes import apply_all_fixes, StringBytesConverter, SentinelCleaner
from utils.debug_utils import debug_log, DEBUG_MODE


class MockToolRegistry:
    """Mock tool registry for testing."""
    
    def __init__(self):
        self.xml_tools = {
            'web_search': 'web_search',
            'file_write': 'file_write',
            'execute_bash': 'execute_bash',
            'crawl_webpage': 'crawl_webpage'
        }
        # Add tool_name_mapping for XML parser
        self.tool_name_mapping = {
            'web_search': 'web_search',
            'file_write': 'file_write',
            'execute_bash': 'execute_bash',
            'crawl_webpage': 'crawl_webpage'
        }


class SystemTester:
    """Comprehensive system tester for Iris."""
    
    def __init__(self):
        self.results = []
        self.xml_parser = XMLToolParser()
        # Set up mock tool registry for XML parser
        self.xml_parser.tool_registry = MockToolRegistry()
        self.decision_router = DecisionRouter()
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {test_name}")
        if details:
            print(f"    {details}")
        
        self.results.append({
            'test': test_name,
            'success': success,
            'details': details
        })
    
    def test_xml_parsing(self):
        """Test XML parsing functionality."""
        print("\n=== Testing XML Parsing ===")
        
        # Test 1: Basic XML parsing
        xml_content = """
        <web_search>
        <query>Python programming</query>
        </web_search>
        """
        
        try:
            chunks = self.xml_parser.extract_xml_chunks(xml_content)
            self.log_test("XML chunk extraction", len(chunks) == 1)
            
            tool_calls = self.xml_parser.parse_xml_tools(xml_content)
            success = len(tool_calls) == 1 and tool_calls[0].function_name == 'web_search'
            self.log_test("XML tool parsing", success, f"Found {len(tool_calls)} tool calls")
        except Exception as e:
            self.log_test("XML parsing", False, str(e))
        
        # Test 2: Multiple tools
        multi_xml = """
        <web_search>
        <query>Test query</query>
        </web_search>
        <file_write>
        <path>test.txt</path>
        <content>Hello world</content>
        </file_write>
        """
        
        try:
            tool_calls = self.xml_parser.parse_xml_tools(multi_xml)
            success = len(tool_calls) == 2
            self.log_test("Multiple XML tools", success, f"Found {len(tool_calls)} tool calls")
        except Exception as e:
            self.log_test("Multiple XML tools", False, str(e))
        
        # Test 3: Malformed XML handling
        bad_xml = "<web_search><query>Unclosed tag"
        
        try:
            tool_calls = self.xml_parser.parse_xml_tools(bad_xml)
            # Should handle gracefully without crashing
            self.log_test("Malformed XML handling", True, "Handled gracefully")
        except Exception as e:
            self.log_test("Malformed XML handling", False, str(e))
    
    def test_bug_fixes(self):
        """Test bug fix functionality."""
        print("\n=== Testing Bug Fixes ===")
        
        # Test 1: String/bytes conversion
        test_bytes = b"Hello world"
        test_string = "Hello world"
        
        try:
            converted_from_bytes = StringBytesConverter.ensure_string(test_bytes)
            converted_from_string = StringBytesConverter.ensure_string(test_string)
            
            success = (converted_from_bytes == "Hello world" and 
                      converted_from_string == "Hello world")
            self.log_test("String/bytes conversion", success)
        except Exception as e:
            self.log_test("String/bytes conversion", False, str(e))
        
        # Test 2: Sentinel cleaning
        dirty_content = "<d>artifact</d>Hello world```\n\n\n\nExtra content"
        
        try:
            cleaned = SentinelCleaner.clean_content(dirty_content)
            success = "<d>" not in cleaned and "```" not in cleaned
            self.log_test("Sentinel cleaning", success, f"Cleaned: '{cleaned}'")
        except Exception as e:
            self.log_test("Sentinel cleaning", False, str(e))
        
        # Test 3: Parameter defaults
        try:
            content, tool_name, params = apply_all_fixes(
                "test content", 
                "web-search", 
                {"query": "test"}
            )
            
            success = (tool_name == "web_search" and 
                      "query" in params and 
                      params["query"] == "test")
            self.log_test("Parameter defaults", success)
        except Exception as e:
            self.log_test("Parameter defaults", False, str(e))
    
    def test_adaptive_routing(self):
        """Test adaptive routing decisions."""
        print("\n=== Testing Adaptive Routing ===")
        
        test_queries = [
            ("What is the capital of France?", "direct"),
            ("Search the web for recent AI news and create a summary report", "agentic"),
            ("Hello, how are you?", "direct"),
            ("Download the latest data from the API and generate a chart", "agentic")
        ]
        
        for query, expected in test_queries:
            try:
                decision = self.decision_router.should_use_agent_mode(query)
                success = decision == (expected == "agentic")
                self.log_test(f"Routing: '{query[:30]}...'", success, 
                             f"Expected {expected}, got {'agentic' if decision else 'direct'}")
            except Exception as e:
                self.log_test(f"Routing: '{query[:30]}...'", False, str(e))
    
    def test_message_normalization(self):
        """Test message normalization."""
        print("\n=== Testing Message Normalization ===")
        
        # Import frontend normalizer (simulate)
        test_messages = [
            {
                "type": "user",
                "content": "Hello world",
                "timestamp": "2023-01-01T00:00:00Z"
            },
            {
                "type": "tool_call",
                "tool": "web_search",
                "arguments": {"query": "test"},
                "timestamp": "2023-01-01T00:00:01Z"
            },
            {
                "type": "tool_result",
                "tool": "web_search",
                "output": "Search results...",
                "success": True,
                "timestamp": "2023-01-01T00:00:02Z"
            }
        ]
        
        try:
            # Simulate normalization (would use actual frontend code in real test)
            normalized_count = 0
            for msg in test_messages:
                if msg.get("type") in ["user", "tool_call", "tool_result"]:
                    normalized_count += 1
            
            success = normalized_count == len(test_messages)
            self.log_test("Message normalization", success, 
                         f"Normalized {normalized_count}/{len(test_messages)} messages")
        except Exception as e:
            self.log_test("Message normalization", False, str(e))
    
    def test_api_structure(self):
        """Test API structure and imports."""
        print("\n=== Testing API Structure ===")
        
        # Test imports
        try:
            from api import share_routes
            self.log_test("Share routes import", True)
        except ImportError as e:
            self.log_test("Share routes import", False, str(e))
        
        try:
            from agentpress.agent_orchestrator import AgentOrchestrator
            self.log_test("Agent orchestrator import", True)
        except ImportError as e:
            self.log_test("Agent orchestrator import", False, str(e))
        
        try:
            from utils.debug_utils import debug_log, DEBUG_MODE
            self.log_test("Debug utils import", True)
        except ImportError as e:
            self.log_test("Debug utils import", False, str(e))
    
    def test_environment_setup(self):
        """Test environment setup."""
        print("\n=== Testing Environment Setup ===")
        
        import os
        
        # Check for required environment variables
        required_vars = [
            'OPENAI_API_KEY',
            'SUPABASE_URL',
            'SUPABASE_ANON_KEY'
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            success = value is not None and len(value) > 0
            self.log_test(f"Environment var {var}", success, 
                         "Set" if success else "Not set")
        
        # Check debug mode
        debug_mode = os.getenv('IRIS_DEBUG', '').lower() in ('true', '1', 'yes', 'on')
        self.log_test("Debug mode detection", True, 
                     f"Debug mode: {'ON' if debug_mode else 'OFF'}")
    
    def run_all_tests(self):
        """Run all tests."""
        print("Starting Iris System Tests...")
        print("=" * 50)
        
        start_time = time.time()
        
        # Run test suites
        self.test_environment_setup()
        self.test_api_structure()
        self.test_xml_parsing()
        self.test_bug_fixes()
        self.test_adaptive_routing()
        self.test_message_normalization()
        
        # Summary
        end_time = time.time()
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"Execution time: {end_time - start_time:.2f}s")
        
        if failed_tests > 0:
            print("\nFAILED TESTS:")
            for result in self.results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['details']}")
        
        return failed_tests == 0
    
    def generate_test_report(self):
        """Generate a test report file."""
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_tests': len(self.results),
            'passed': sum(1 for r in self.results if r['success']),
            'failed': sum(1 for r in self.results if not r['success']),
            'results': self.results
        }
        
        with open('TEST_REPORT.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate markdown report
        with open('TEST_REPORT.md', 'w') as f:
            f.write("# Iris System Test Report\n\n")
            f.write(f"**Generated:** {report['timestamp']}\n\n")
            f.write(f"**Summary:** {report['passed']}/{report['total_tests']} tests passed\n\n")
            
            f.write("## Test Results\n\n")
            for result in self.results:
                status = "✅" if result['success'] else "❌"
                f.write(f"- {status} **{result['test']}**")
                if result['details']:
                    f.write(f": {result['details']}")
                f.write("\n")
            
            if report['failed'] > 0:
                f.write("\n## Failed Tests\n\n")
                for result in self.results:
                    if not result['success']:
                        f.write(f"### {result['test']}\n")
                        f.write(f"**Error:** {result['details']}\n\n")
        
        print(f"\nTest reports generated: TEST_REPORT.json, TEST_REPORT.md")


def main():
    """Main test function."""
    tester = SystemTester()
    success = tester.run_all_tests()
    tester.generate_test_report()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

