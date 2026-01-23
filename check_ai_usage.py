#!/usr/bin/env python3
"""
Check current AI usage and cache performance.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from app.database import db

async def check_usage():
    await db.connect()

    # Check current month usage
    result = await db.fetch_one('''
        SELECT
            COUNT(*) as total_requests,
            COALESCE(SUM(cost_usd), 0) as total_cost,
            COALESCE(SUM(input_tokens), 0) as total_input_tokens,
            COALESCE(SUM(output_tokens), 0) as total_output_tokens
        FROM api_usage
        WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
    ''')

    print('Current Month AI Usage:')
    print(f'  Total Requests: {result["total_requests"]}')
    print(f'  Total Cost: ${float(result["total_cost"]):.6f}')
    print(f'  Total Tokens: {int(result["total_input_tokens"] or 0) + int(result["total_output_tokens"] or 0):,}')

    # Check cache performance
    cache_result = await db.fetch_one('''
        SELECT
            COUNT(*) as total_entries,
            COALESCE(SUM(hit_count), 0) as total_hits,
            COALESCE(SUM(tokens_saved * hit_count), 0) as total_tokens_saved
        FROM semantic_cache
        WHERE expires_at IS NULL OR expires_at > NOW()
    ''')

    print('\nSemantic Cache Performance:')
    print(f'  Total Cache Entries: {cache_result["total_entries"]}')
    print(f'  Total Cache Hits: {cache_result["total_hits"]}')
    print(f'  Total Tokens Saved: {cache_result["total_tokens_saved"]:,}')

    # Calculate cache hit rate
    total_requests = result["total_requests"] or 1
    cache_hits = cache_result["total_hits"] or 0
    cache_hit_rate = (cache_hits / total_requests) * 100 if total_requests > 0 else 0

    print(f'\nCache Hit Rate: {cache_hit_rate:.1f}%')

    # Estimate cost savings (rough estimate: $0.0001 per token)
    tokens_saved = cache_result["total_tokens_saved"] or 0
    estimated_savings = tokens_saved * 0.0001
    print(f'Estimated Cost Savings: ${estimated_savings:.4f}')

    await db.close()

if __name__ == "__main__":
    asyncio.run(check_usage())