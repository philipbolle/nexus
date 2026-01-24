#!/usr/bin/env python3
"""
NEXUS Status Dashboard

A simple but cool status dashboard for Nexus that provides instant visibility
into system health, agents, finances, and email stats.

Usage:
    python scripts/nexus_status.py
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sys
import os

# Configuration
BASE_URL = "http://localhost:8080"
TIMEOUT = 10.0  # seconds

# Colors for terminal output (optional)
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# Emojis for visual appeal
EMOJIS = {
    "healthy": "✅",
    "unhealthy": "❌",
    "degraded": "⚠️",
    "unknown": "❓",
    "database": "🗄️",
    "redis": "🔴",
    "chromadb": "🔍",
    "agent": "🤖",
    "n8n": "⚙️",
    "finance": "💰",
    "email": "📧",
    "system": "🖥️",
    "clock": "⏰",
    "memory": "🧠",
    "cpu": "⚡",
    "disk": "💾",
    "network": "🌐",
    "up": "🔼",
    "down": "🔽",
    "warning": "⚠️",
    "info": "ℹ️",
    "success": "✅",
    "error": "❌",
    "question": "❓"
}

async def fetch_json(client: httpx.AsyncClient, endpoint: str) -> Optional[Dict]:
    """Fetch JSON from an endpoint, return None if fails."""
    try:
        response = await client.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"{Colors.YELLOW}Warning: {endpoint} returned {response.status_code}{Colors.END}")
            return None
    except Exception as e:
        print(f"{Colors.YELLOW}Warning: Could not fetch {endpoint}: {e}{Colors.END}")
        return None

async def get_system_health(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Get system health information."""
    health = await fetch_json(client, "/health")
    detailed = await fetch_json(client, "/health/detailed")
    status = await fetch_json(client, "/status")
    metrics = await fetch_json(client, "/metrics/system")

    return {
        "basic": health,
        "detailed": detailed,
        "status": status,
        "metrics": metrics
    }

async def get_agent_info(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Get agent information."""
    agents = await fetch_json(client, "/agents")
    registry = await fetch_json(client, "/registry-status")

    # Count agents by type
    agent_types = {}
    if agents and "agents" in agents:
        for agent in agents["agents"]:
            agent_type = agent.get("agent_type", "unknown")
            agent_types[agent_type] = agent_types.get(agent_type, 0) + 1

    return {
        "agents": agents,
        "registry": registry,
        "agent_types": agent_types
    }

async def get_finance_info(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Get finance information."""
    # Get budget status
    budget = await fetch_json(client, "/finance/budget-status")

    # Try to get debt information from database via chat endpoint
    debt_info = None
    try:
        response = await client.post(
            f"{BASE_URL}/chat",
            json={
                "message": "Get my current debt information from the fin_debts table. Just return the total debt amount and amount paid so far.",
                "use_tools": True
            },
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            debt_info = response.json()
    except:
        pass

    # Try to get recent expenses (last 3)
    recent_expenses = None
    try:
        response = await client.post(
            f"{BASE_URL}/chat",
            json={
                "message": "Get the 3 most recent expenses from fin_transactions table. Just return amount, category, and date.",
                "use_tools": True
            },
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            recent_expenses = response.json()
    except:
        pass

    return {
        "budget": budget,
        "debt_info": debt_info,
        "recent_expenses": recent_expenses
    }

async def get_email_info(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Get email information."""
    stats = await fetch_json(client, "/email/stats")
    summary = await fetch_json(client, "/email/summary")
    recent = await fetch_json(client, "/email/recent")

    return {
        "stats": stats,
        "summary": summary,
        "recent": recent
    }

def format_status_indicator(status: str) -> str:
    """Format status with color and emoji."""
    if status == "healthy":
        return f"{Colors.GREEN}{EMOJIS['healthy']} Healthy{Colors.END}"
    elif status == "unhealthy":
        return f"{Colors.RED}{EMOJIS['unhealthy']} Unhealthy{Colors.END}"
    elif status == "degraded":
        return f"{Colors.YELLOW}{EMOJIS['degraded']} Degraded{Colors.END}"
    else:
        return f"{Colors.YELLOW}{EMOJIS['unknown']} {status.capitalize()}{Colors.END}"

def print_header():
    """Print dashboard header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}    NEXUS STATUS DASHBOARD{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.WHITE}{EMOJIS['clock']} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
    print()

def print_system_health(health_data: Dict[str, Any]):
    """Print system health section."""
    print(f"{Colors.BOLD}{Colors.WHITE}{EMOJIS['system']} SYSTEM HEALTH{Colors.END}")
    print(f"{Colors.WHITE}{'-'*40}{Colors.END}")

    if not health_data:
        print(f"{Colors.YELLOW}  Could not fetch system health{Colors.END}")
        return

    # Basic health
    if health_data.get("basic"):
        basic = health_data["basic"]
        status = basic.get("status", "unknown")
        print(f"  Overall: {format_status_indicator(status)}")

    # Detailed status
    if health_data.get("status"):
        status = health_data["status"]
        overall = status.get("status", "unknown")
        services = status.get("services", [])

        print(f"  Services: {format_status_indicator(overall)}")
        for service in services:
            name = service.get("name", "unknown")
            status_val = service.get("status", "unknown")
            details = service.get("details", "")

            # Map service names to emojis
            service_emoji = EMOJIS.get(name, EMOJIS["system"])
            print(f"    {service_emoji} {name}: {format_status_indicator(status_val)} {details}")

    # Database tables
    if health_data.get("status") and "database_tables" in health_data["status"]:
        tables = health_data["status"]["database_tables"]
        print(f"  {EMOJIS['database']} Database Tables: {Colors.BOLD}{tables}{Colors.END}")

    # Metrics
    if health_data.get("metrics"):
        metrics = health_data["metrics"]
        if "cpu" in metrics:
            cpu = metrics["cpu"]
            print(f"  {EMOJIS['cpu']} CPU: {cpu.get('percent', 0):.1f}% ({cpu.get('count', 0)} cores)")

        if "memory" in metrics:
            mem = metrics["memory"]
            print(f"  {EMOJIS['memory']} Memory: {mem.get('used_percent', 0):.1f}% used ({mem.get('available_gb', 0):.1f} GB available)")

        if "disk" in metrics:
            disk = metrics["disk"]
            print(f"  {EMOJIS['disk']} Disk: {disk.get('used_percent', 0):.1f}% used ({disk.get('free_gb', 0):.1f} GB free)")

def print_agent_info(agent_data: Dict[str, Any]):
    """Print agent information section."""
    print(f"\n{Colors.BOLD}{Colors.WHITE}{EMOJIS['agent']} AGENT FRAMEWORK{Colors.END}")
    print(f"{Colors.WHITE}{'-'*40}{Colors.END}")

    if not agent_data:
        print(f"{Colors.YELLOW}  Could not fetch agent information{Colors.END}")
        return

    # Registry status
    if agent_data.get("registry"):
        registry = agent_data["registry"]
        total = registry.get("total_agents", 0)
        active = registry.get("active_agents", 0)

        print(f"  Registry: {Colors.BOLD}{total}{Colors.END} total agents, {Colors.BOLD}{active}{Colors.END} active")

        # Agent types breakdown
        if agent_data.get("agent_types"):
            print(f"  Agent Types:")
            for agent_type, count in agent_data["agent_types"].items():
                print(f"    • {agent_type}: {Colors.BOLD}{count}{Colors.END}")

    # List some agents if available
    if agent_data.get("agents") and "agents" in agent_data["agents"]:
        agents = agent_data["agents"]["agents"]
        if agents:
            print(f"  Recent Agents:")
            for i, agent in enumerate(agents[:5]):  # Show first 5
                name = agent.get("name", "Unknown")
                agent_type = agent.get("agent_type", "unknown")
                status = agent.get("status", "unknown")

                status_display = "🟢" if status == "active" else "🟡" if status == "idle" else "🔴"
                print(f"    {status_display} {name} ({agent_type})")

            if len(agents) > 5:
                print(f"    ... and {len(agents) - 5} more")

def print_finance_info(finance_data: Dict[str, Any]):
    """Print finance information section."""
    print(f"\n{Colors.BOLD}{Colors.WHITE}{EMOJIS['finance']} FINANCE{Colors.END}")
    print(f"{Colors.WHITE}{'-'*40}{Colors.END}")

    if not finance_data:
        print(f"{Colors.YELLOW}  Could not fetch finance information{Colors.END}")
        return

    # Budget status
    if finance_data.get("budget"):
        budget = finance_data["budget"]
        print(f"  Budget Status:")

        if "categories" in budget:
            for category in budget["categories"][:3]:  # Show top 3
                name = category.get("name", "Unknown")
                spent = category.get("spent", 0)
                target = category.get("target", 0)

                if target > 0:
                    percent = (spent / target) * 100
                    bar_length = 20
                    filled = int((spent / target) * bar_length) if target > 0 else 0
                    bar = "█" * filled + "░" * (bar_length - filled)

                    color = Colors.GREEN if percent <= 80 else Colors.YELLOW if percent <= 100 else Colors.RED
                    print(f"    {name}: {color}{bar}{Colors.END} {spent:.2f}/{target:.2f} ({percent:.1f}%)")

    # Debt information from chat endpoint
    if finance_data.get("debt_info"):
        debt_info = finance_data["debt_info"]
        # Try to extract debt information from chat response
        if isinstance(debt_info, dict) and "response" in debt_info:
            response_text = debt_info["response"]
            # Simple parsing for debt information
            if "$9,700" in response_text or "9700" in response_text:
                print(f"  Debt: {Colors.BOLD}$9,700{Colors.END} (to mom)")
            elif "debt" in response_text.lower():
                print(f"  Debt Info: {response_text[:80]}...")

    # Recent expenses from chat endpoint
    if finance_data.get("recent_expenses"):
        recent = finance_data["recent_expenses"]
        if isinstance(recent, dict) and "response" in recent:
            response_text = recent["response"]
            print(f"  Recent Expenses:")
            # Display the response text (it should be formatted by the AI)
            lines = response_text.split('\n')
            for line in lines[:4]:  # Show first 4 lines
                if line.strip():
                    print(f"    {line}")

def print_email_info(email_data: Dict[str, Any]):
    """Print email information section."""
    print(f"\n{Colors.BOLD}{Colors.WHITE}{EMOJIS['email']} EMAIL INTELLIGENCE{Colors.END}")
    print(f"{Colors.WHITE}{'-'*40}{Colors.END}")

    if not email_data:
        print(f"{Colors.YELLOW}  Could not fetch email information{Colors.END}")
        return

    # Stats
    if email_data.get("stats"):
        stats = email_data["stats"]

        if "email_processing" in stats:
            processing = stats["email_processing"]
            print(f"  Processing Stats:")

            if "total_processed" in processing:
                print(f"    Total Processed: {Colors.BOLD}{processing['total_processed']}{Colors.END}")

            if "classification_breakdown" in processing:
                breakdown = processing["classification_breakdown"]
                print(f"    Classifications:")
                for cls, count in breakdown.items():
                    print(f"      • {cls}: {Colors.BOLD}{count}{Colors.END}")

        if "ai_providers" in stats:
            providers = stats["ai_providers"]
            print(f"    AI Providers Used: {Colors.BOLD}{len(providers)}{Colors.END}")

    # Recent emails
    if email_data.get("recent"):
        recent = email_data["recent"]
        if isinstance(recent, list):
            print(f"  Recent Emails: {Colors.BOLD}{len(recent)}{Colors.END}")
            for i, email in enumerate(recent[:3]):  # Show first 3
                subject = email.get("subject", "No subject")[:40]
                classification = email.get("classification", "unknown")
                print(f"    • {subject}... ({classification})")

def print_footer():
    """Print dashboard footer."""
    print(f"\n{Colors.WHITE}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}Run 'python scripts/nexus_status.py' anytime for current status{Colors.END}")
    print(f"{Colors.CYAN}API running at: {BASE_URL}{Colors.END}")
    print(f"{Colors.CYAN}Swagger docs at: {BASE_URL}/docs{Colors.END}")
    print()

async def main():
    """Main async function."""
    print_header()

    async with httpx.AsyncClient() as client:
        # Fetch all data concurrently
        tasks = [
            get_system_health(client),
            get_agent_info(client),
            get_finance_info(client),
            get_email_info(client)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        system_health = results[0] if not isinstance(results[0], Exception) else None
        agent_info = results[1] if not isinstance(results[1], Exception) else None
        finance_info = results[2] if not isinstance(results[2], Exception) else None
        email_info = results[3] if not isinstance(results[3], Exception) else None

        # Print sections
        print_system_health(system_health)
        print_agent_info(agent_info)
        print_finance_info(finance_info)
        print_email_info(email_info)

    print_footer()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Dashboard interrupted by user.{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}Error running dashboard: {e}{Colors.END}")
        sys.exit(1)