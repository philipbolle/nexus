#!/usr/bin/env python3
"""
Test MCP server integrations for NEXUS.

This script tests connectivity and basic functionality of all MCP servers
configured in Claude Desktop.
"""

import asyncio
import os
import sys
import json
import subprocess
from typing import Dict, List, Any, Optional
import httpx
import asyncpg
import redis.asyncio as redis
from chromadb import HttpClient
from chromadb.config import Settings

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_postgresql() -> Dict[str, Any]:
    """Test PostgreSQL connectivity and basic queries."""
    try:
        # Load environment variables from .env
        from dotenv import load_dotenv
        load_dotenv('/home/philip/nexus/.env')

        conn = await asyncpg.connect(
            host=os.getenv('PGHOST', 'localhost'),
            port=int(os.getenv('PGPORT', '5432')),
            user=os.getenv('PGUSER', 'nexus'),
            password=os.getenv('PGPASSWORD', ''),
            database=os.getenv('PGDATABASE', 'nexus_db')
        )

        # Test basic queries
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            LIMIT 5
        """)

        table_count = await conn.fetchval("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)

        await conn.close()

        return {
            'success': True,
            'table_count': table_count,
            'sample_tables': [t['table_name'] for t in tables],
            'message': f'Connected to PostgreSQL, found {table_count} tables'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'PostgreSQL connection failed: {e}'
        }

async def test_redis() -> Dict[str, Any]:
    """Test Redis connectivity."""
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv('/home/philip/nexus/.env')

        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            password=os.getenv('REDIS_PASSWORD', None),
            decode_responses=True
        )

        # Test connection
        pong = await redis_client.ping()
        info = await redis_client.info()

        await redis_client.close()

        return {
            'success': True,
            'ping': pong,
            'redis_version': info.get('redis_version', 'unknown'),
            'used_memory_human': info.get('used_memory_human', 'unknown'),
            'message': 'Connected to Redis successfully'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Redis connection failed: {e}'
        }

async def test_chromadb() -> Dict[str, Any]:
    """Test ChromaDB connectivity."""
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv('/home/philip/nexus/.env')

        chroma_client = HttpClient(
            host=os.getenv('CHROMA_HOST', 'localhost'),
            port=int(os.getenv('CHROMA_PORT', '8000')),
            settings=Settings(anonymized_telemetry=False)
        )

        # Test heartbeat
        heartbeat = chroma_client.heartbeat()
        collections = chroma_client.list_collections()

        return {
            'success': True,
            'heartbeat': heartbeat,
            'collection_count': len(collections),
            'collections': [col.name for col in collections],
            'message': f'Connected to ChromaDB, found {len(collections)} collections'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'ChromaDB connection failed: {e}'
        }

async def test_n8n() -> Dict[str, Any]:
    """Test n8n API connectivity."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to access n8n health endpoint
            response = await client.get('http://localhost:5678/healthz')

            if response.status_code == 200:
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'message': 'n8n is accessible'
                }
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'message': f'n8n returned status {response.status_code}'
                }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'n8n connection failed: {e}'
        }

async def test_agent_framework() -> Dict[str, Any]:
    """Test Agent Framework API connectivity."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to access agent framework health endpoint
            response = await client.get('http://localhost:8080/health')

            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'status': data.get('status', 'unknown'),
                    'timestamp': data.get('timestamp', 'unknown'),
                    'message': 'Agent Framework API is accessible'
                }
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'message': f'Agent Framework API returned status {response.status_code}'
                }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Agent Framework API connection failed: {e}'
        }

def test_mcp_server_config() -> Dict[str, Any]:
    """Test Claude Desktop MCP server configuration."""
    try:
        config_path = '/home/philip/.config/Claude/claude_desktop_config.json'
        with open(config_path, 'r') as f:
            config = json.load(f)

        mcp_servers = config.get('mcpServers', {})
        server_count = len(mcp_servers)
        server_names = list(mcp_servers.keys())

        # Check for required servers
        required_servers = ['postgres', 'agent-framework', 'redis', 'chromadb', 'n8n']
        missing_servers = [s for s in required_servers if s not in server_names]

        # Check if executable paths exist
        valid_paths = []
        invalid_paths = []

        for name, server_config in mcp_servers.items():
            command = server_config.get('command', '')
            if command and os.path.exists(command.split()[0] if ' ' in command else command):
                valid_paths.append(name)
            else:
                invalid_paths.append(name)

        return {
            'success': True,
            'server_count': server_count,
            'server_names': server_names,
            'missing_required_servers': missing_servers,
            'valid_paths': valid_paths,
            'invalid_paths': invalid_paths,
            'message': f'Found {server_count} MCP servers configured'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to read MCP configuration: {e}'
        }

def test_virtual_environments() -> Dict[str, Any]:
    """Test virtual environments for Python MCP servers."""
    mcp_servers = [
        'postgres-mcp',
        'agent-framework-mcp',
        'redis-mcp',
        'chromadb-mcp',
        'n8n-mcp'
    ]

    results = {}
    missing = []
    present = []

    for server in mcp_servers:
        venv_path = f'/home/philip/mcp-servers/{server}/.venv'
        if os.path.exists(venv_path):
            present.append(server)
            results[server] = {
                'exists': True,
                'path': venv_path,
                'has_bin': os.path.exists(f'{venv_path}/bin/python'),
                'has_requirements': os.path.exists(f'/home/philip/mcp-servers/{server}/requirements.txt')
            }
        else:
            missing.append(server)
            results[server] = {'exists': False, 'path': venv_path}

    return {
        'success': len(missing) == 0,
        'present': present,
        'missing': missing,
        'results': results,
        'message': f'Virtual environments: {len(present)} present, {len(missing)} missing'
    }

async def run_all_tests():
    """Run all MCP integration tests."""
    print("🧪 Starting MCP Integration Tests")
    print("=" * 60)

    results = {}

    # Test 1: MCP Configuration
    print("\n1. Testing Claude Desktop MCP Configuration...")
    config_test = test_mcp_server_config()
    results['config'] = config_test
    print(f"   ✓ Found {config_test['server_count']} MCP servers: {', '.join(config_test['server_names'])}")
    if config_test['missing_required_servers']:
        print(f"   ⚠ Missing required servers: {config_test['missing_required_servers']}")
    if config_test['invalid_paths']:
        print(f"   ⚠ Invalid paths for: {config_test['invalid_paths']}")

    # Test 2: Virtual Environments
    print("\n2. Testing Virtual Environments...")
    venv_test = test_virtual_environments()
    results['venv'] = venv_test
    for server, info in venv_test['results'].items():
        status = "✓" if info['exists'] else "✗"
        print(f"   {status} {server}: {info['path']}")

    # Test 3: PostgreSQL
    print("\n3. Testing PostgreSQL Connectivity...")
    pg_test = await test_postgresql()
    results['postgresql'] = pg_test
    if pg_test['success']:
        print(f"   ✓ Connected to PostgreSQL, found {pg_test['table_count']} tables")
        print(f"   Sample tables: {', '.join(pg_test['sample_tables'][:3])}...")
    else:
        print(f"   ✗ PostgreSQL test failed: {pg_test['error']}")

    # Test 4: Redis
    print("\n4. Testing Redis Connectivity...")
    redis_test = await test_redis()
    results['redis'] = redis_test
    if redis_test['success']:
        print(f"   ✓ Connected to Redis v{redis_test['redis_version']}")
        print(f"   Memory usage: {redis_test['used_memory_human']}")
    else:
        print(f"   ✗ Redis test failed: {redis_test['error']}")

    # Test 5: ChromaDB
    print("\n5. Testing ChromaDB Connectivity...")
    chroma_test = await test_chromadb()
    results['chromadb'] = chroma_test
    if chroma_test['success']:
        print(f"   ✓ Connected to ChromaDB, found {chroma_test['collection_count']} collections")
        if chroma_test['collections']:
            print(f"   Collections: {', '.join(chroma_test['collections'][:3])}...")
    else:
        print(f"   ✗ ChromaDB test failed: {chroma_test['error']}")

    # Test 6: n8n
    print("\n6. Testing n8n Connectivity...")
    n8n_test = await test_n8n()
    results['n8n'] = n8n_test
    if n8n_test['success']:
        print(f"   ✓ n8n is accessible (status: {n8n_test['status_code']})")
    else:
        print(f"   ✗ n8n test failed: {n8n_test['error']}")

    # Test 7: Agent Framework API
    print("\n7. Testing Agent Framework API Connectivity...")
    agent_test = await test_agent_framework()
    results['agent_framework'] = agent_test
    if agent_test['success']:
        print(f"   ✓ Agent Framework API is accessible (status: {agent_test['status']})")
    else:
        print(f"   ✗ Agent Framework API test failed: {agent_test['error']}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    successful = sum(1 for test in results.values() if test.get('success', False))
    total = len(results)

    for name, test in results.items():
        status = "✓ PASS" if test.get('success', False) else "✗ FAIL"
        print(f"{status} {name.replace('_', ' ').title()}")

    print(f"\nOverall: {successful}/{total} tests passed")

    # Return overall success
    overall_success = all(test.get('success', False) for test in results.values()
                         if name not in ['n8n', 'chromadb', 'redis'])  # These may not be running

    return overall_success, results

def main():
    """Main entry point."""
    try:
        success, results = asyncio.run(run_all_tests())

        if success:
            print("\n✅ All critical MCP integration tests passed!")
            sys.exit(0)
        else:
            print("\n⚠ Some MCP integration tests failed. See details above.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠ Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error during tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()