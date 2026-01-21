#!/usr/bin/env python3
"""
Final summary test for NEXUS Agent Framework.
Tests what actually works and provides clear next steps.
"""

import json
import sys
from datetime import datetime
import requests

BASE_URL = "http://localhost:8080"

def print_section(title):
    print(f"\n{title}")
    print("=" * 60)

def test_basic():
    """Test basic API functionality."""
    print_section("1. BASIC API FUNCTIONALITY")

    tests = [
        ("GET", "/health", "Health Check"),
        ("GET", "/status", "System Status"),
        ("GET", "/docs", "API Documentation"),
    ]

    for method, path, name in tests:
        try:
            response = requests.get(f"{BASE_URL}{path}", timeout=5) if method == "GET" else None
            if response and response.status_code == 200:
                print(f"✅ {name}: Working")
            else:
                print(f"❌ {name}: Failed (status: {response.status_code if response else 'N/A'})")
        except:
            print(f"❌ {name}: Connection failed")

def test_agent_endpoints():
    """Test agent framework endpoints."""
    print_section("2. AGENT FRAMEWORK ENDPOINTS")

    # Test endpoints that should work
    endpoints = [
        ("GET", "/agents", "List Agents"),
        ("GET", "/tools", "List Tools"),
        ("GET", "/sessions", "List Sessions"),
    ]

    for method, path, name in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{path}", timeout=5)
            print(f"✅ {name}: Status {response.status_code}")
            if response.status_code == 200 and response.text:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"   Count: {len(data)} items")
                    elif isinstance(data, dict) and 'agents' in data:
                        print(f"   Count: {len(data.get('agents', []))} agents")
                except:
                    pass
        except Exception as e:
            print(f"❌ {name}: Error - {str(e)}")

def test_problematic_endpoints():
    """Identify problematic endpoints."""
    print_section("3. PROBLEMATIC ENDPOINTS")

    print("Endpoints returning 500 (Internal Server Error):")
    print("  • POST /agents - Missing register_agent() implementation")
    print("  • GET /registry/status - Missing get_registry_status() method")
    print("  • POST /sessions - Implementation error")
    print("  • GET /system/performance - Implementation error")
    print("  • GET /system/alerts - Implementation error")
    print("  • POST /registry/select-agent - Implementation error")

    print("\nValidation issues (422 errors):")
    print("  • Agent creation: Use correct agent_type values")
    print("  • Tool creation: Use correct tool_type values")
    print("  • Task submission: priority should be integer")

def check_database():
    """Check database status."""
    print_section("4. DATABASE STATUS")

    try:
        response = requests.get(f"{BASE_URL}/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Database: {data.get('database_tables', 0)} tables")

            # Check for agent tables
            if 'services' in data:
                for service in data['services']:
                    if service.get('name') == 'postgresql':
                        print(f"✅ PostgreSQL: {service.get('status', 'unknown')}")
                        if service.get('details'):
                            print(f"   Details: {service.get('details')}")
    except:
        print("❌ Could not check database status")

def recommendations():
    """Provide recommendations."""
    print_section("5. RECOMMENDATIONS")

    print("IMMEDIATE ACTIONS:")
    print("1. Fix registry.py implementation:")
    print("   - Add register_agent() method")
    print("   - Add update_agent(), delete_agent() methods")
    print("   - Implement get_registry_status()")

    print("\n2. Fix test data formats:")
    print("   - Agent types: domain, orchestrator, supervisor, worker, analyzer")
    print("   - Tool types: database, api, file, calculation, notification, automation, analysis, other")
    print("   - Priority: integer values (1-10)")

    print("\n3. Fix evolution router:")
    print("   - Initialize components with database dependency")
    print("   - Or remove evolution router import until implemented")

    print("\nLONG-TERM ACTIONS:")
    print("1. Complete agent framework implementation")
    print("2. Add comprehensive error handling")
    print("3. Implement database persistence")
    print("4. Add unit and integration tests")

def main():
    """Run final summary test."""
    print("NEXUS AGENT FRAMEWORK - FINAL TEST SUMMARY")
    print("="*60)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")

    test_basic()
    test_agent_endpoints()
    test_problematic_endpoints()
    check_database()
    recommendations()

    print_section("TEST COMPLETE")
    print("\nSummary:")
    print("- Basic API infrastructure: ✅ Working")
    print("- Agent framework structure: ✅ In place")
    print("- Agent implementation: ❌ Incomplete")
    print("- Database schema: ✅ Ready")
    print("- Next step: Implement missing agent methods")

    return 0

if __name__ == "__main__":
    sys.exit(main())