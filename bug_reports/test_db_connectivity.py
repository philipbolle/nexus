#!/usr/bin/env python3
"""
Simple database connectivity test.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def test_db_connection():
    """Test PostgreSQL database connection."""
    load_dotenv('/home/philip/nexus/.env')

    db_host = os.getenv('POSTGRES_HOST', 'localhost')
    db_port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'nexus_db')
    db_user = os.getenv('POSTGRES_USER', 'nexus')
    db_password = os.getenv('POSTGRES_PASSWORD', '')

    print(f"Testing database connection...")
    print(f"Host: {db_host}:{db_port}")
    print(f"Database: {db_name}")
    print(f"User: {db_user}")

    try:
        conn = await asyncpg.connect(
            host=db_host,
            port=int(db_port),
            database=db_name,
            user=db_user,
            password=db_password
        )

        # Test basic query
        version = await conn.fetchval('SELECT version()')
        print(f"✅ Database connected")
        print(f"PostgreSQL version: {version.split(',')[0]}")

        # Count tables
        tables = await conn.fetchval("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        print(f"Tables in public schema: {tables}")

        # Check agents table
        try:
            agent_count = await conn.fetchval("SELECT COUNT(*) FROM agents")
            print(f"Agents in database: {agent_count}")

            # Check a sample agent config
            if agent_count > 0:
                agent = await conn.fetchrow("SELECT id, name, config FROM agents LIMIT 1")
                print(f"Sample agent: {agent['name']}")
                print(f"Config type: {type(agent['config'])}")
                print(f"Config value: {agent['config']}")
        except Exception as e:
            print(f"⚠️  Could not query agents table: {e}")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def test_redis_connection():
    """Test Redis connection."""
    try:
        import redis
        load_dotenv('/home/philip/nexus/.env')

        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', '6379')
        redis_password = os.getenv('REDIS_PASSWORD', '')

        print(f"\nTesting Redis connection...")
        print(f"Host: {redis_host}:{redis_port}")

        r = redis.Redis(
            host=redis_host,
            port=int(redis_port),
            password=redis_password or None,
            decode_responses=True
        )

        # Test connection
        pong = r.ping()
        print(f"✅ Redis connected: {pong}")

        # Get info
        info = r.info()
        print(f"Redis version: {info.get('redis_version')}")
        print(f"Connected clients: {info.get('connected_clients')}")

        # Count keys
        keys = r.dbsize()
        print(f"Keys in database: {keys}")

        return True

    except ImportError:
        print("⚠️  Redis module not installed")
        return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

async def main():
    """Run all connectivity tests."""
    print("="*60)
    print("NEXUS Connectivity Tests")
    print("="*60)

    db_ok = await test_db_connection()
    redis_ok = await test_redis_connection()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Database: {'✅ OK' if db_ok else '❌ FAILED'}")
    print(f"Redis: {'✅ OK' if redis_ok else '❌ FAILED'}")

    if db_ok and redis_ok:
        print("\n✅ All connectivity tests passed!")
        return 0
    else:
        print("\n❌ Some connectivity tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)