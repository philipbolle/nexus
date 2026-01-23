#!/usr/bin/env python3
"""
NEXUS Agent Framework Progress Monitor
Run this script to track implementation progress.
"""

import json
import sys
from datetime import datetime
import requests
from typing import List, Dict, Any

BASE_URL = "http://localhost:8080"

class AgentFrameworkProgress:
    """Track agent framework implementation progress."""

    def __init__(self):
        self.results = []
        self.timestamp = datetime.now()

    def test_endpoint(self, method: str, path: str, name: str,
                     expected_status: int = 200, data: Dict = None) -> Dict[str, Any]:
        """Test an endpoint and record result."""
        url = f"{BASE_URL}{path}"
        result = {
            "name": name,
            "method": method,
            "path": path,
            "expected": expected_status,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }

        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=10)
            elif method == "PUT":
                response = requests.put(url, json=data, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, timeout=10)
            else:
                result["status"] = "error"
                result["error"] = f"Unsupported method: {method}"
                self.results.append(result)
                return result

            result["actual"] = response.status_code
            result["success"] = response.status_code == expected_status

            if result["success"]:
                result["status"] = "success"
            elif response.status_code == 500:
                result["status"] = "server_error"
                result["error"] = "Internal server error - implementation issue"
            elif response.status_code == 422:
                result["status"] = "validation_error"
                result["error"] = "Validation error - check request format"
            elif response.status_code == 404:
                result["status"] = "not_found"
                result["error"] = "Endpoint not found or resource doesn't exist"
            else:
                result["status"] = "failed"
                result["error"] = f"Unexpected status: {response.status_code}"

            # Store response for debugging
            if response.text:
                try:
                    result["response"] = response.json()
                except:
                    result["response"] = response.text[:200]

        except Exception as e:
            result["status"] = "error"
            result["error"] = f"Exception: {str(e)}"

        self.results.append(result)
        return result

    def run_tests(self):
        """Run all progress tests."""
        print("NEXUS Agent Framework Progress Monitor")
        print("="*70)
        print(f"Test Time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Base URL: {BASE_URL}")
        print()

        # Test categories
        self.test_core_api()
        self.test_agent_management()
        self.test_session_management()
        self.test_task_execution()
        self.test_tool_management()
        self.test_performance_monitoring()

        self.print_summary()

    def test_core_api(self):
        """Test core API functionality."""
        print("1. CORE API FUNCTIONALITY")
        print("-"*40)

        tests = [
            ("GET", "/health", "Health Check", 200),
            ("GET", "/status", "System Status", 200),
            ("GET", "/docs", "API Documentation", 200),
        ]

        for method, path, name, expected in tests:
            result = self.test_endpoint(method, path, name, expected)
            self.print_result(result)

    def test_agent_management(self):
        """Test agent management endpoints."""
        print("\n2. AGENT MANAGEMENT")
        print("-"*40)

        # Correct enum values based on schema
        agent_data = {
            "name": f"progress-test-{datetime.now().strftime('%H%M%S')}",
            "agent_type": "worker",  # Valid: domain, orchestrator, supervisor, worker, analyzer
            "description": "Progress test agent",
            "system_prompt": "Test",
            "capabilities": ["testing"],
            "domain": "testing",
            "config": {}
        }

        tests = [
            ("GET", "/agents", "List Agents", 200),
            ("POST", "/agents", "Create Agent", 201, agent_data),
        ]

        for test in tests:
            if len(test) == 4:
                method, path, name, expected = test
                result = self.test_endpoint(method, path, name, expected)
            else:
                method, path, name, expected, data = test
                result = self.test_endpoint(method, path, name, expected, data)
            self.print_result(result)

            # If agent was created, test related endpoints
            if name == "Create Agent" and result.get("success") and result.get("response", {}).get("id"):
                agent_id = result["response"]["id"]
                agent_tests = [
                    ("GET", f"/agents/{agent_id}", "Get Agent", 200),
                    ("GET", f"/agents/{agent_id}/status", "Get Agent Status", 200),
                    ("POST", f"/agents/{agent_id}/start", "Start Agent", 200),
                    ("POST", f"/agents/{agent_id}/stop", "Stop Agent", 200),
                    ("DELETE", f"/agents/{agent_id}", "Delete Agent", 204),
                ]
                for a_method, a_path, a_name, a_expected in agent_tests:
                    a_result = self.test_endpoint(a_method, a_path, a_name, a_expected)
                    self.print_result(a_result)

        # Registry status
        self.test_endpoint("GET", "/registry/status", "Registry Status", 200)
        self.print_result(self.results[-1])

    def test_session_management(self):
        """Test session management endpoints."""
        print("\n3. SESSION MANAGEMENT")
        print("-"*40)

        session_data = {
            "title": f"Progress Test Session {datetime.now().strftime('%H:%M')}",
            "session_type": "testing",
            "metadata": {"test": True}
        }

        tests = [
            ("GET", "/sessions", "List Sessions", 200),
            ("POST", "/sessions", "Create Session", 201, session_data),
        ]

        for test in tests:
            if len(test) == 4:
                method, path, name, expected = test
                result = self.test_endpoint(method, path, name, expected)
            else:
                method, path, name, expected, data = test
                result = self.test_endpoint(method, path, name, expected, data)
            self.print_result(result)

    def test_task_execution(self):
        """Test task execution endpoints."""
        print("\n4. TASK EXECUTION")
        print("-"*40)

        task_data = {
            "task": {
                "description": "Progress test task",
                "type": "test"
            },
            "priority": 1  # Integer, not string
        }

        tests = [
            ("POST", "/tasks", "Submit Task", 200, task_data),
        ]

        for test in tests:
            if len(test) == 4:
                method, path, name, expected = test
                result = self.test_endpoint(method, path, name, expected)
            else:
                method, path, name, expected, data = test
                result = self.test_endpoint(method, path, name, expected, data)
            self.print_result(result)

    def test_tool_management(self):
        """Test tool management endpoints."""
        print("\n5. TOOL MANAGEMENT")
        print("-"*40)

        # Correct tool type based on validation error
        tool_data = {
            "name": f"progress_tool_{datetime.now().strftime('%H%M%S')}",
            "display_name": "Progress Test Tool",
            "description": "Tool for progress testing",
            "tool_type": "analysis",  # Valid values: database, api, file, calculation, notification, automation, analysis, python_function, web_search
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "requires_confirmation": False
        }

        tests = [
            ("GET", "/tools", "List Tools", 200),
            ("POST", "/tools", "Create Tool", 201, tool_data),
        ]

        for test in tests:
            if len(test) == 4:
                method, path, name, expected = test
                result = self.test_endpoint(method, path, name, expected)
            else:
                method, path, name, expected, data = test
                result = self.test_endpoint(method, path, name, expected, data)
            self.print_result(result)

    def test_performance_monitoring(self):
        """Test performance monitoring endpoints."""
        print("\n6. PERFORMANCE MONITORING")
        print("-"*40)

        tests = [
            ("GET", "/system/performance", "System Performance", 200),
            ("GET", "/system/alerts", "System Alerts", 200),
            ("POST", "/registry/select-agent", "Select Agent", 200, {
                "task_description": "Test task",
                "required_capabilities": ["testing"],
                "preferred_domain": "testing"
            }),
        ]

        for test in tests:
            if len(test) == 4:
                method, path, name, expected = test
                result = self.test_endpoint(method, path, name, expected)
            else:
                method, path, name, expected, data = test
                result = self.test_endpoint(method, path, name, expected, data)
            self.print_result(result)

    def print_result(self, result: Dict[str, Any]):
        """Print a single test result."""
        status_icons = {
            "success": "✅",
            "server_error": "🔧",
            "validation_error": "📝",
            "not_found": "🔍",
            "failed": "❌",
            "error": "💥",
            "pending": "⏳"
        }

        icon = status_icons.get(result["status"], "❓")
        print(f"  {icon} {result['name']}")

        if result["status"] != "success":
            if result.get("error"):
                print(f"     Error: {result['error']}")
            if result.get("actual"):
                print(f"     Status: {result['actual']} (expected: {result['expected']})")

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*70)
        print("PROGRESS SUMMARY")
        print("="*70)

        # Count by status
        status_counts = {}
        for result in self.results:
            status = result["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        total = len(self.results)

        print(f"Total tests: {total}")
        print(f"✅ Success: {status_counts.get('success', 0)}")
        print(f"🔧 Server errors: {status_counts.get('server_error', 0)}")
        print(f"📝 Validation errors: {status_counts.get('validation_error', 0)}")
        print(f"🔍 Not found: {status_counts.get('not_found', 0)}")
        print(f"❌ Other failures: {status_counts.get('failed', 0) + status_counts.get('error', 0)}")

        print("\nIMPLEMENTATION STATUS:")
        print("-"*40)

        categories = {
            "Core API": ["Health Check", "System Status", "API Documentation"],
            "Agent Management": ["List Agents", "Create Agent", "Get Agent", "Registry Status"],
            "Session Management": ["List Sessions", "Create Session"],
            "Task Execution": ["Submit Task"],
            "Tool Management": ["List Tools", "Create Tool"],
            "Performance Monitoring": ["System Performance", "System Alerts", "Select Agent"]
        }

        for category, tests in categories.items():
            category_results = [r for r in self.results if r["name"] in tests]
            if category_results:
                success_count = sum(1 for r in category_results if r["status"] == "success")
                total_count = len(category_results)
                percentage = (success_count / total_count * 100) if total_count > 0 else 0

                if percentage == 100:
                    status = "✅ Complete"
                elif percentage >= 50:
                    status = "🟡 Partial"
                else:
                    status = "🔴 Needs work"

                print(f"{status} {category}: {success_count}/{total_count} ({percentage:.0f}%)")

        print("\nNEXT STEPS:")
        print("-"*40)
        print("1. Fix server errors (🔧) - Implement missing methods")
        print("2. Fix validation errors (📝) - Use correct data formats")
        print("3. Run this script after each implementation change")
        print("\nTrack progress by watching the 🔧 → ✅ transitions")

        # Save results to file
        report = {
            "timestamp": self.timestamp.isoformat(),
            "base_url": BASE_URL,
            "total_tests": total,
            "results": self.results,
            "summary": status_counts
        }

        filename = f"agent_progress_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📊 Full results saved to: {filename}")

def main():
    """Main entry point."""
    monitor = AgentFrameworkProgress()
    monitor.run_tests()
    return 0

if __name__ == "__main__":
    sys.exit(main())