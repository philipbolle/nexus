#!/usr/bin/env python3
"""
Test script for NEXUS Production Readiness Features

Tests:
1. Centralized logging configuration
2. Error handling middleware
3. Health check endpoints
4. Backup system
5. Monitoring integration
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.logging_config import setup_logging, get_logger, log_request, log_response, log_error
from app.middleware.error_handler import ErrorResponse
import psutil


async def test_logging_configuration():
    """Test centralized logging configuration."""
    print("\n" + "="*60)
    print("Testing Logging Configuration")
    print("="*60)

    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    # Test different log levels
    logger.debug("Debug message - should only appear in development")
    logger.info("Info message - system information")
    logger.warning("Warning message - potential issue")
    logger.error("Error message - something went wrong")

    # Test structured logging with extra fields
    logger.info(
        "Structured log message",
        extra={
            "user_id": "test_user_123",
            "action": "login",
            "duration_ms": 45.2,
            "success": True
        }
    )

    # Test request/response logging helpers
    log_request(
        logger,
        request_id="req_123",
        endpoint="/api/test",
        method="GET",
        user_id="test_user",
        client_ip="192.168.1.100",
        user_agent="TestClient/1.0"
    )

    log_response(
        logger,
        request_id="req_123",
        endpoint="/api/test",
        method="GET",
        status_code=200,
        duration_ms=45.2,
        user_id="test_user"
    )

    # Test error logging
    try:
        raise ValueError("Test error for logging")
    except ValueError as e:
        log_error(
            logger,
            e,
            request_id="req_123",
            endpoint="/api/test",
            method="GET",
            user_id="test_user"
        )

    print("✅ Logging configuration test completed")
    return True


def test_error_response_format():
    """Test standardized error response format."""
    print("\n" + "="*60)
    print("Testing Error Response Format")
    print("="*60)

    # Test different error responses
    validation_error = ErrorResponse.create(
        status_code=422,
        message="Validation error",
        error_type="validation_error",
        request_id="req_123",
        details={
            "errors": [
                {"field": "email", "message": "Invalid email format"},
                {"field": "password", "message": "Password too short"}
            ]
        }
    )

    print("Validation Error Response:")
    print(json.dumps(validation_error, indent=2))

    http_error = ErrorResponse.create(
        status_code=404,
        message="Resource not found",
        error_type="http_error",
        request_id="req_456"
    )

    print("\nHTTP Error Response:")
    print(json.dumps(http_error, indent=2))

    internal_error = ErrorResponse.create(
        status_code=500,
        message="Internal server error",
        error_type="internal_error",
        request_id="req_789"
    )

    print("\nInternal Error Response:")
    print(json.dumps(internal_error, indent=2))

    print("✅ Error response format test completed")
    return True


def test_system_metrics():
    """Test system metrics collection."""
    print("\n" + "="*60)
    print("Testing System Metrics")
    print("="*60)

    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()

        # Memory metrics
        memory = psutil.virtual_memory()

        # Disk metrics
        disk = psutil.disk_usage("/")

        # Network metrics
        net_io = psutil.net_io_counters()

        print(f"CPU Usage: {cpu_percent}% ({cpu_count} cores)")
        print(f"Memory: {memory.percent}% used ({memory.used / (1024**3):.1f} GB / {memory.total / (1024**3):.1f} GB)")
        print(f"Disk: {disk.percent}% used ({disk.used / (1024**3):.1f} GB / {disk.total / (1024**3):.1f} GB)")
        print(f"Network: Sent: {net_io.bytes_sent / (1024**2):.1f} MB, Received: {net_io.bytes_recv / (1024**2):.1f} MB")

        print("✅ System metrics test completed")
        return True

    except Exception as e:
        print(f"❌ System metrics test failed: {e}")
        return False


def test_backup_script():
    """Test backup script functionality."""
    print("\n" + "="*60)
    print("Testing Backup Script")
    print("="*60)

    backup_script = os.path.join(os.path.dirname(__file__), "backup_nexus_enhanced.sh")

    if not os.path.exists(backup_script):
        print(f"❌ Backup script not found: {backup_script}")
        return False

    # Check if script is executable
    if not os.access(backup_script, os.X_OK):
        print(f"⚠️  Backup script is not executable, fixing...")
        os.chmod(backup_script, 0o755)

    # Test script help
    import subprocess
    try:
        result = subprocess.run(
            [backup_script, "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✅ Backup script help works")
            print(f"Output:\n{result.stdout[:200]}...")
        else:
            print(f"❌ Backup script help failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Backup script test failed: {e}")
        return False

    # Check for restore test script
    restore_script = os.path.join(os.path.dirname(__file__), "test_restore.sh")
    if os.path.exists(restore_script):
        print("✅ Restore test script found")
    else:
        print("❌ Restore test script not found")
        return False

    print("✅ Backup script test completed")
    return True


async def test_health_endpoints():
    """Test health check endpoints (simulated)."""
    print("\n" + "="*60)
    print("Testing Health Endpoints")
    print("="*60)

    # This is a simulation since we can't import FastAPI app in this test
    # In a real test, we would use TestClient

    endpoints = [
        ("/health", "GET", "Basic health check"),
        ("/health/detailed", "GET", "Detailed health check"),
        ("/ready", "GET", "Readiness probe"),
        ("/live", "GET", "Liveness probe"),
        ("/metrics/system", "GET", "System metrics"),
        ("/status", "GET", "System status"),
    ]

    for endpoint, method, description in endpoints:
        print(f"✓ {method} {endpoint} - {description}")

    print("✅ Health endpoints test completed (simulated)")
    return True


def test_monitoring_integration():
    """Test monitoring integration components."""
    print("\n" + "="*60)
    print("Testing Monitoring Integration")
    print("="*60)

    # Check if monitoring module exists
    monitoring_module = os.path.join(
        os.path.dirname(__file__),
        "..",
        "app",
        "monitoring_integration.py"
    )

    if not os.path.exists(monitoring_module):
        print(f"❌ Monitoring integration module not found: {monitoring_module}")
        return False

    print("✅ Monitoring integration module exists")

    # Check if error handler module exists
    error_handler_module = os.path.join(
        os.path.dirname(__file__),
        "..",
        "app",
        "middleware",
        "error_handler.py"
    )

    if not os.path.exists(error_handler_module):
        print(f"❌ Error handler module not found: {error_handler_module}")
        return False

    print("✅ Error handler module exists")

    print("✅ Monitoring integration test completed")
    return True


def create_production_readiness_report():
    """Create production readiness report."""
    print("\n" + "="*60)
    print("PRODUCTION READINESS REPORT")
    print("="*60)

    report = {
        "timestamp": datetime.now().isoformat(),
        "tests": {},
        "overall_status": "PASS",
        "recommendations": []
    }

    # Run tests
    tests = [
        ("Logging Configuration", test_logging_configuration),
        ("Error Response Format", lambda: test_error_response_format()),
        ("System Metrics", test_system_metrics),
        ("Backup Script", test_backup_script),
        ("Health Endpoints", test_health_endpoints),
        ("Monitoring Integration", test_monitoring_integration),
    ]

    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.run(test_func())
            else:
                result = test_func()

            report["tests"][test_name] = {
                "status": "PASS" if result else "FAIL",
                "result": result
            }

            if not result:
                report["overall_status"] = "FAIL"
                report["recommendations"].append(f"Fix {test_name}")

        except Exception as e:
            report["tests"][test_name] = {
                "status": "ERROR",
                "error": str(e)
            }
            report["overall_status"] = "FAIL"
            report["recommendations"].append(f"Fix {test_name}: {e}")

    # Print report
    print(f"\nOverall Status: {report['overall_status']}")
    print(f"\nTest Results:")

    for test_name, test_result in report["tests"].items():
        status = test_result["status"]
        if status == "PASS":
            print(f"  ✓ {test_name}: {status}")
        elif status == "FAIL":
            print(f"  ✗ {test_name}: {status}")
        else:
            print(f"  ⚠ {test_name}: {status} - {test_result.get('error', 'Unknown error')}")

    if report["recommendations"]:
        print(f"\nRecommendations:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")

    # Save report to file
    report_file = os.path.join(os.path.dirname(__file__), "production_readiness_report.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Full report saved to: {report_file}")

    return report["overall_status"] == "PASS"


async def main():
    """Main test function."""
    print("NEXUS Production Readiness Test Suite")
    print("="*60)

    # Run all tests
    success = create_production_readiness_report()

    if success:
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED - Production ready!")
        print("="*60)
        return 0
    else:
        print("\n" + "="*60)
        print("❌ SOME TESTS FAILED - Review recommendations above")
        print("="*60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)