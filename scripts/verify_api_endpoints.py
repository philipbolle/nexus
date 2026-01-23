#!/usr/bin/env python3
"""
Verify FastAPI endpoints match documentation.
"""
import re
import sys
from pathlib import Path
import ast


def count_endpoints_in_file(filepath: Path) -> int:
    """Count @router decorators in a Python file."""
    if not filepath.exists():
        return 0

    content = filepath.read_text()
    # Count @router decorators (including @router.get, @router.post, etc.)
    return len(re.findall(r'@router\.(get|post|put|delete|patch|head|options|trace)', content, re.IGNORECASE))


def get_router_prefix(content: str) -> str:
    """Extract router prefix from APIRouter definition."""
    # Look for router = APIRouter(prefix="...")
    prefix_pattern = r'router\s*=\s*APIRouter\s*\([^)]*prefix\s*=\s*["\']([^"\']+)["\']'
    match = re.search(prefix_pattern, content, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def extract_endpoints_from_file(filepath: Path) -> list:
    """Extract endpoint information from a Python file."""
    if not filepath.exists():
        return []

    content = filepath.read_text()
    endpoints = []

    # Get router prefix if present
    prefix = get_router_prefix(content)
    if prefix and not prefix.startswith('/'):
        prefix = '/' + prefix
    if prefix and prefix.endswith('/'):
        prefix = prefix.rstrip('/')

    # Find all @router decorators and their function definitions
    pattern = r'@router\.(get|post|put|delete|patch|head|options|trace)\s*\(\s*["\']([^"\']*)["\']'
    matches = re.findall(pattern, content, re.IGNORECASE)

    for method, path in matches:
        # Handle empty path (root of router)
        if path == '':
            path = '/'

        # Apply prefix
        full_path = path
        if prefix:
            if path == '/':
                # Root of prefixed router is just the prefix
                full_path = prefix
            elif path.startswith('/'):
                # Avoid double slash if prefix ends with / and path starts with /
                if prefix.endswith('/') and path.startswith('/'):
                    full_path = prefix.rstrip('/') + path
                else:
                    full_path = prefix + path
            else:
                full_path = prefix + '/' + path
        elif not full_path.startswith('/'):
            full_path = '/' + full_path

        endpoints.append({
            'method': method.upper(),
            'path': full_path,
            'file': filepath.name
        })

    return endpoints


def count_documented_endpoints(claude_md: Path) -> int:
    """Count endpoints documented in CLAUDE.md."""
    if not claude_md.exists():
        return 0

    content = claude_md.read_text()

    # Count lines starting with "- " that look like endpoints
    # Exclude n8n webhooks and Auto-Yes tool
    lines = content.split('\n')
    count = 0

    in_fastapi_section = False
    for line in lines:
        line = line.strip()

        # Check for FastAPI section
        if '**FastAPI Endpoints' in line:
            in_fastapi_section = True
            continue
        elif '**n8n Webhooks' in line:
            in_fastapi_section = False
            continue
        elif '**Auto-Yes Tool' in line:
            in_fastapi_section = False
            continue

        # Count endpoint lines in FastAPI section
        if in_fastapi_section and line.startswith('- '):
            # Check if it looks like an endpoint (contains HTTP method or path)
            if any(x in line.lower() for x in ['get ', 'post ', 'put ', 'delete ', 'patch ', '/']):
                count += 1

    return count


def extract_documented_endpoints(claude_md: Path) -> list:
    """Extract documented endpoints from CLAUDE.md."""
    if not claude_md.exists():
        return []

    content = claude_md.read_text()
    lines = content.split('\n')
    endpoints = []

    in_fastapi_section = False
    current_section = None

    for line in lines:
        line = line.strip()

        # Check for FastAPI section
        if '**FastAPI Endpoints' in line:
            in_fastapi_section = True
            continue
        elif '**n8n Webhooks' in line:
            in_fastapi_section = False
            continue
        elif '**Auto-Yes Tool' in line:
            in_fastapi_section = False
            continue

        # Check for section headers (like "Core:", "Finance:", etc.)
        if in_fastapi_section and line.endswith(':'):
            current_section = line.rstrip(':')
            continue

        # Extract endpoints
        if in_fastapi_section and line.startswith('- '):
            endpoint_text = line[2:].strip()

            # Try to parse method and path
            # Format: "METHOD /path - Description" or "/path - Description"
            if ' - ' in endpoint_text:
                endpoint_part = endpoint_text.split(' - ')[0].strip()
            else:
                endpoint_part = endpoint_text

            # Extract method and path
            method = None
            path = None

            # Check if method is specified
            # Match case-insensitively for HTTP methods
            method_match = re.match(r'^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|TRACE)\s+(\S+)', endpoint_part, re.IGNORECASE)
            if method_match:
                method = method_match.group(1).upper()
                # Extract path preserving original case
                path_start = method_match.end(1) + 1  # Position after method and space
                path = endpoint_part[path_start:].strip()
            else:
                # Assume GET if no method specified
                if endpoint_part.startswith('/'):
                    method = 'GET'
                    path = endpoint_part

            if method and path:
                endpoints.append({
                    'method': method,
                    'path': path,
                    'section': current_section,
                    'raw': endpoint_text
                })

    return endpoints


def main():
    """Main verification function."""
    nexus_dir = Path("/home/philip/nexus")
    app_dir = nexus_dir / "app"
    routers_dir = app_dir / "routers"
    claude_md = nexus_dir / "CLAUDE.md"

    print("🔍 Verifying FastAPI endpoints match documentation")
    print("=" * 50)

    # List router files
    router_files = [
        routers_dir / "health.py",
        routers_dir / "chat.py",
        routers_dir / "finance.py",
        routers_dir / "email.py",
        routers_dir / "agents.py",
        routers_dir / "evolution.py",
        routers_dir / "swarm.py",
    ]

    # Count endpoints in each file
    total_implemented = 0
    all_implemented_endpoints = []

    print("\n📊 Implemented endpoints by router:")
    for router_file in router_files:
        if router_file.exists():
            count = count_endpoints_in_file(router_file)
            endpoints = extract_endpoints_from_file(router_file)
            total_implemented += count
            all_implemented_endpoints.extend(endpoints)
            print(f"  - {router_file.name}: {count} endpoints")
        else:
            print(f"  - {router_file.name}: NOT FOUND")

    # Add root endpoint (in main.py)
    main_file = app_dir / "main.py"
    if main_file.exists():
        content = main_file.read_text()
        if '@app.get("/")' in content:
            total_implemented += 1
            all_implemented_endpoints.append({
                'method': 'GET',
                'path': '/',
                'file': 'main.py'
            })
            print(f"  - main.py: 1 endpoint (root)")

    print(f"\n✅ TOTAL IMPLEMENTED: {total_implemented} FastAPI endpoints")

    # Count documented endpoints
    documented_count = count_documented_endpoints(claude_md)
    documented_endpoints = extract_documented_endpoints(claude_md)

    print(f"\n📄 Documented in CLAUDE.md: {documented_count} endpoints")

    # Compare counts
    if total_implemented == documented_count:
        print(f"\n🎉 SUCCESS: Implemented endpoints ({total_implemented}) match documentation ({documented_count})")
    else:
        print(f"\n⚠️  MISMATCH: Implemented endpoints ({total_implemented}) ≠ Documentation ({documented_count})")
        print(f"   Difference: {abs(total_implemented - documented_count)} endpoints")

    # Show detailed comparison
    print("\n📋 Detailed endpoint analysis:")
    print("\nImplemented endpoints:")
    for ep in sorted(all_implemented_endpoints, key=lambda x: x['path']):
        print(f"  {ep['method']} {ep['path']} ({ep['file']})")

    print("\nDocumented endpoints:")
    for ep in sorted(documented_endpoints, key=lambda x: x['path']):
        print(f"  {ep['method']} {ep['path']} ({ep['section']})")

    # Check for missing documentation
    print("\n🔍 Checking for missing documentation:")
    implemented_set = {(ep['method'], ep['path']) for ep in all_implemented_endpoints}
    documented_set = {(ep['method'], ep['path']) for ep in documented_endpoints}

    missing_in_docs = implemented_set - documented_set
    extra_in_docs = documented_set - implemented_set

    if missing_in_docs:
        print("\n❌ Endpoints implemented but NOT documented:")
        for method, path in sorted(missing_in_docs):
            print(f"  - {method} {path}")

    if extra_in_docs:
        print("\n❌ Endpoints documented but NOT implemented:")
        for method, path in sorted(extra_in_docs):
            print(f"  - {method} {path}")

    if not missing_in_docs and not extra_in_docs:
        print("\n✅ All endpoints match between implementation and documentation!")

    # Summary
    print("\n" + "=" * 50)
    print("📈 SUMMARY:")
    print(f"  Total implemented: {total_implemented}")
    print(f"  Total documented: {documented_count}")
    print(f"  Missing in docs: {len(missing_in_docs)}")
    print(f"  Extra in docs: {len(extra_in_docs)}")

    return 0 if total_implemented == documented_count and not missing_in_docs and not extra_in_docs else 1


if __name__ == "__main__":
    sys.exit(main())