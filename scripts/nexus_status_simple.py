#!/usr/bin/env python3
"""
NEXUS Status Dashboard - Simple Version

A simpler version that uses only standard library modules.
No external dependencies required.

Usage:
    python3 scripts/nexus_status_simple.py
"""

import urllib.request
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8080"
TIMEOUT = 5  # seconds

# Simple color codes (works in most terminals)
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def fetch_json(endpoint):
    """Fetch JSON from an endpoint using urllib."""
    try:
        url = f"{BASE_URL}{endpoint}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            if response.status == 200:
                data = response.read()
                return json.loads(data)
            else:
                print(f"{Colors.YELLOW}Warning: {endpoint} returned {response.status}{Colors.END}")
                return None
    except Exception as e:
        print(f"{Colors.YELLOW}Warning: Could not fetch {endpoint}: {e}{Colors.END}")
        return None

def print_header():
    """Print dashboard header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}    NEXUS STATUS DASHBOARD (Simple){Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.WHITE}📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
    print()

def print_system_health():
    """Print system health section."""
    print(f"{Colors.BOLD}{Colors.WHITE}🖥️ SYSTEM HEALTH{Colors.END}")
    print(f"{Colors.WHITE}{'-'*40}{Colors.END}")

    # Basic health
    health = fetch_json("/health")
    if health:
        status = health.get("status", "unknown")
        color = Colors.GREEN if status == "healthy" else Colors.RED if status == "unhealthy" else Colors.YELLOW
        print(f"  Status: {color}{status.upper()}{Colors.END}")

    # Detailed status
    status = fetch_json("/status")
    if status:
        overall = status.get("status", "unknown")
        services = status.get("services", [])

        color = Colors.GREEN if overall == "healthy" else Colors.RED if overall == "unhealthy" else Colors.YELLOW
        print(f"  Overall: {color}{overall.upper()}{Colors.END}")

        print(f"  Services:")
        for service in services:
            name = service.get("name", "unknown")
            status_val = service.get("status", "unknown")
            details = service.get("details", "")

            color = Colors.GREEN if status_val == "healthy" else Colors.RED if status_val == "unhealthy" else Colors.YELLOW
            print(f"    • {name}: {color}{status_val}{Colors.END} {details}")

    # System metrics
    metrics = fetch_json("/metrics/system")
    if metrics:
        if "cpu" in metrics:
            cpu = metrics["cpu"]
            print(f"  CPU: {cpu.get('percent', 0):.1f}%")

        if "memory" in metrics:
            mem = metrics["memory"]
            print(f"  Memory: {mem.get('used_percent', 0):.1f}% used")

        if "disk" in metrics:
            disk = metrics["disk"]
            print(f"  Disk: {disk.get('used_percent', 0):.1f}% used")

def print_agent_info():
    """Print agent information section."""
    print(f"\n{Colors.BOLD}{Colors.WHITE}🤖 AGENT FRAMEWORK{Colors.END}")
    print(f"{Colors.WHITE}{'-'*40}{Colors.END}")

    # Agent list
    agents = fetch_json("/agents")
    if agents and "agents" in agents:
        agent_list = agents["agents"]
        print(f"  Total Agents: {Colors.BOLD}{len(agent_list)}{Colors.END}")

        # Count by type
        type_count = {}
        for agent in agent_list:
            agent_type = agent.get("agent_type", "unknown")
            type_count[agent_type] = type_count.get(agent_type, 0) + 1

        print(f"  By Type:")
        for agent_type, count in type_count.items():
            print(f"    • {agent_type}: {Colors.BOLD}{count}{Colors.END}")

        # Show a few agents
        print(f"  Sample Agents:")
        for agent in agent_list[:3]:
            name = agent.get("name", "Unknown")
            status = agent.get("status", "unknown")
            status_icon = "🟢" if status == "active" else "🟡" if status == "idle" else "🔴"
            print(f"    {status_icon} {name}")

def print_finance_info():
    """Print finance information section."""
    print(f"\n{Colors.BOLD}{Colors.WHITE}💰 FINANCE{Colors.END}")
    print(f"{Colors.WHITE}{'-'*40}{Colors.END}")

    # Budget status
    budget = fetch_json("/finance/budget-status")
    if budget:
        total_spent = budget.get("total_spent", "0")
        month = budget.get("month", "Unknown")

        print(f"  Month: {Colors.BOLD}{month}{Colors.END}")
        print(f"  Total Spent: {Colors.BOLD}${total_spent}{Colors.END}")

        # Show categories with spending
        categories = budget.get("categories", [])
        if categories:
            print(f"  Categories:")
            for category in categories[:3]:  # Show top 3
                name = category.get("name", "Unknown")
                spent = category.get("spent", 0)
                if spent > 0:
                    print(f"    • {name}: ${spent:.2f}")

def print_email_info():
    """Print email information section."""
    print(f"\n{Colors.BOLD}{Colors.WHITE}📧 EMAIL INTELLIGENCE{Colors.END}")
    print(f"{Colors.WHITE}{'-'*40}{Colors.END}")

    # Email stats
    stats = fetch_json("/email/stats")
    if stats:
        print(f"  Email Processing:")

        if "email_processing" in stats:
            processing = stats["email_processing"]
            total = processing.get("total_processed", 0)
            print(f"    Total Processed: {Colors.BOLD}{total}{Colors.END}")

def print_footer():
    """Print dashboard footer."""
    print(f"\n{Colors.WHITE}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}Quick Commands:{Colors.END}")
    print(f"  {Colors.WHITE}• Check API: curl {BASE_URL}/health{Colors.END}")
    print(f"  {Colors.WHITE}• View docs: {BASE_URL}/docs{Colors.END}")
    print(f"  {Colors.WHITE}• Run again: python3 scripts/nexus_status_simple.py{Colors.END}")
    print()

def main():
    """Main function."""
    print_header()

    try:
        print_system_health()
        print_agent_info()
        print_finance_info()
        print_email_info()
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        print(f"{Colors.YELLOW}Make sure Nexus API is running at {BASE_URL}{Colors.END}")

    print_footer()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Dashboard interrupted.{Colors.END}")
        sys.exit(0)