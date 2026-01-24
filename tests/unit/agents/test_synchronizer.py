"""
NEXUS Test Synchronizer Agent

Autonomous test synchronization and repair agent.
Detects mismatches between test expectations and actual implementations,
generates corrected test files, and validates fixes.

Capabilities:
- Test file analysis
- Method signature extraction
- Test-implementation comparison
- Test correction generation
- Test validation
- Test coverage analysis
"""

import asyncio
import ast
import inspect
import logging
import json
import re
import os
import sys
from typing import Dict, Any, List, Optional, Tuple, Union, Set
from datetime import datetime
import uuid
import importlib.util

from .base import BaseAgent, AgentType, AgentStatus
from .tools import ToolSystem, ToolDefinition, ToolParameter, ToolType
from .memory import MemorySystem
from ..database import db
from ..config import settings

logger = logging.getLogger(__name__)


class TestSynchronizerAgent(BaseAgent):
    """
    Test Synchronizer Agent - Autonomous test synchronization and repair.

    Capabilities: test_analysis, signature_extraction, mismatch_detection,
                  test_correction, test_validation, coverage_analysis
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: str = "Test Synchronizer Agent",
        description: str = "Autonomous test synchronization and repair agent. Detects mismatches between test expectations and actual implementations, generates corrected test files, and validates fixes.",
        system_prompt: str = "You are a Test Synchronizer Agent. You analyze test files, compare them with actual implementations, detect mismatches in method signatures and behavior, and generate corrected test files. You prioritize maintaining test intent while fixing technical mismatches.",
        capabilities: Optional[List[str]] = None,
        supervisor_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        if capabilities is None:
            capabilities = [
                "test_analysis",
                "signature_extraction",
                "mismatch_detection",
                "test_correction",
                "test_validation",
                "coverage_analysis",
                "python_ast_parsing",
                "test_generation"
            ]

        if config is None:
            config = {
                "auto_correct_safe_fixes": False,   # Whether to auto-apply safe fixes
                "require_approval": True,           # Whether to require human approval
                "test_directory": "tests",          # Directory containing tests
                "source_directory": "app",          # Directory containing source code
                "backup_before_changes": True,      # Whether to backup test files before changes
                "run_tests_after_fix": True,        # Whether to run tests after applying fixes
                "max_corrections_per_run": 10,      # Maximum number of corrections per run
            }

        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.DOMAIN,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities,
            domain="testing",
            supervisor_id=supervisor_id,
            config=config,
            **kwargs
        )

        self.tool_system = ToolSystem()
        self.memory_system = MemorySystem()
        self.test_directory = self.config.get("test_directory", "tests")
        self.source_directory = self.config.get("source_directory", "app")

    async def initialize(self) -> None:
        """Initialize the agent and register tools."""
        await super().initialize()

        # Register tools
        await self._register_tools()

        logger.info(f"TestSynchronizerAgent {self.name} initialized with ID: {self.agent_id}")

    async def _register_tools(self) -> None:
        """Register all tools available to this agent."""

        # Tool 1: Analyze test failures
        await self.tool_system.register_tool(
            ToolDefinition(
                name="analyze_test_failures",
                display_name="Analyze Test Failures",
                description="Analyze pytest output or test files to identify failure patterns",
                tool_type=ToolType.ANALYSIS,
                parameters=[
                    ToolParameter("pytest_output", "string", "Pytest output to analyze (optional)", required=False),
                    ToolParameter("test_file", "string", "Specific test file to analyze (optional)", required=False),
                    ToolParameter("failure_type", "string", "Type of failures to focus on (e.g., 'signature', 'import', 'mock')", required=False),
                ]
            )
        )

        # Tool 2: Extract method signatures from implementation
        await self.tool_system.register_tool(
            ToolDefinition(
                name="extract_method_signatures",
                display_name="Extract Method Signatures",
                description="Extract method signatures from Python source files",
                tool_type=ToolType.ANALYSIS,
                parameters=[
                    ToolParameter("source_file", "string", "Path to Python source file", required=True),
                    ToolParameter("class_name", "string", "Specific class to analyze (optional)", required=False),
                    ToolParameter("method_name", "string", "Specific method to analyze (optional)", required=False),
                ]
            )
        )

        # Tool 3: Extract test expectations
        await self.tool_system.register_tool(
            ToolDefinition(
                name="extract_test_expectations",
                display_name="Extract Test Expectations",
                description="Extract method calls and expectations from test files",
                tool_type=ToolType.ANALYSIS,
                parameters=[
                    ToolParameter("test_file", "string", "Path to test file", required=True),
                    ToolParameter("test_class", "string", "Specific test class to analyze (optional)", required=False),
                    ToolParameter("test_method", "string", "Specific test method to analyze (optional)", required=False),
                ]
            )
        )

        # Tool 4: Compare test expectations with implementations
        await self.tool_system.register_tool(
            ToolDefinition(
                name="compare_test_with_implementation",
                display_name="Compare Test with Implementation",
                description="Compare test expectations with actual implementation signatures",
                tool_type=ToolType.ANALYSIS,
                parameters=[
                    ToolParameter("test_file", "string", "Path to test file", required=True),
                    ToolParameter("source_file", "string", "Path to source file", required=True),
                    ToolParameter("generate_report", "boolean", "Generate detailed mismatch report", required=False, default=True),
                ]
            )
        )

        # Tool 5: Generate test corrections
        await self.tool_system.register_tool(
            ToolDefinition(
                name="generate_test_corrections",
                display_name="Generate Test Corrections",
                description="Generate corrected test code based on mismatches",
                tool_type=ToolType.ANALYSIS,
                parameters=[
                    ToolParameter("mismatches", "array", "List of mismatches to fix", required=True),
                    ToolParameter("original_test_code", "string", "Original test code", required=True),
                    ToolParameter("strategy", "string", "Correction strategy: 'update_signature', 'update_mock', 'update_import'", required=False, default="update_signature"),
                ]
            )
        )

        # Tool 6: Apply test corrections
        await self.tool_system.register_tool(
            ToolDefinition(
                name="apply_test_corrections",
                display_name="Apply Test Corrections",
                description="Apply test corrections to files with backup and validation",
                tool_type=ToolType.FILE,
                parameters=[
                    ToolParameter("test_file", "string", "Path to test file to update", required=True),
                    ToolParameter("corrected_code", "string", "Corrected test code", required=True),
                    ToolParameter("create_backup", "boolean", "Create backup before updating", required=False, default=True),
                    ToolParameter("validate_syntax", "boolean", "Validate Python syntax before saving", required=False, default=True),
                ]
            )
        )

        # Tool 7: Run test validation
        await self.tool_system.register_tool(
            ToolDefinition(
                name="run_test_validation",
                display_name="Run Test Validation",
                description="Run pytest on test file to validate corrections",
                tool_type=ToolType.ANALYSIS,
                parameters=[
                    ToolParameter("test_file", "string", "Path to test file to validate", required=True),
                    ToolParameter("test_method", "string", "Specific test method to run (optional)", required=False),
                    ToolParameter("timeout_seconds", "number", "Timeout for test execution", required=False, default=30),
                ]
            )
        )

        logger.info(f"Registered {len(self.tool_system.tools)} tools for TestSynchronizerAgent")

    # ============ Core Analysis Methods ============

    async def analyze_test_failures(
        self,
        pytest_output: Optional[str] = None,
        test_file: Optional[str] = None,
        failure_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze test failures to identify patterns.

        Returns:
            Dictionary with failure analysis results.
        """
        logger.info(f"Analyzing test failures (file: {test_file or 'all'}, type: {failure_type or 'all'})")

        results = {
            "timestamp": datetime.now().isoformat(),
            "test_file": test_file,
            "failure_type_focus": failure_type,
            "failure_patterns": [],
            "common_issues": {},
            "recommended_actions": [],
            "summary": {}
        }

        try:
            # If pytest output provided, parse it
            if pytest_output:
                parsed_failures = self._parse_pytest_output(pytest_output)
                results["failure_patterns"].extend(parsed_failures)
                results["summary"]["parsed_failures"] = len(parsed_failures)

            # If test file provided, analyze it for potential issues
            if test_file and os.path.exists(test_file):
                file_issues = await self._analyze_test_file(test_file)
                results["failure_patterns"].extend(file_issues)
                results["summary"]["file_issues"] = len(file_issues)

            # Categorize failures
            categorized = self._categorize_failures(results["failure_patterns"])
            results["common_issues"] = categorized

            # Generate recommendations
            results["recommended_actions"] = self._generate_failure_recommendations(categorized)

            # Calculate overall status
            total_issues = len(results["failure_patterns"])
            results["status"] = "no_issues" if total_issues == 0 else "issues_found"
            results["summary"]["total_issues"] = total_issues

            # Store in memory for tracking
            await self._store_analysis_results(results)

        except Exception as e:
            logger.error(f"Error analyzing test failures: {e}", exc_info=True)
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def _parse_pytest_output(self, pytest_output: str) -> List[Dict[str, Any]]:
        """Parse pytest output to extract failure information."""
        failures = []

        # Common error patterns
        patterns = {
            "signature_mismatch": [
                r"TypeError: .*got an unexpected keyword argument ['\"](.*?)['\"]",
                r"TypeError: .*takes (.*?) positional argument",
                r"AttributeError: .*object has no attribute ['\"](.*?)['\"]",
            ],
            "import_error": [
                r"ImportError: (.*)",
                r"ModuleNotFoundError: (.*)",
                r"NameError: name ['\"](.*?)['\"] is not defined",
            ],
            "mock_mismatch": [
                r"AssertionError: expected call not found",
                r"Expected: .*Actual:",
                r"mock\.(.*?)\.assert_called_with",
            ],
            "database_error": [
                r"RuntimeError: Database not connected",
                r"asyncpg\.exceptions\.(.*)",
                r"psycopg2\.(.*)",
            ]
        }

        lines = pytest_output.split('\n')
        current_failure = None

        for i, line in enumerate(lines):
            # Look for test failure indicators
            if "FAILED" in line and "test_" in line:
                # Extract test name
                test_match = re.search(r'test_[^\s]+', line)
                if test_match:
                    current_failure = {
                        "test_name": test_match.group(0),
                        "error_type": "unknown",
                        "error_message": "",
                        "line_number": i + 1,
                        "full_error": []
                    }

            elif current_failure and ("Error:" in line or "AssertionError" in line):
                # Check error type
                for error_type, error_patterns in patterns.items():
                    for pattern in error_patterns:
                        match = re.search(pattern, line)
                        if match:
                            current_failure["error_type"] = error_type
                            current_failure["error_message"] = line.strip()
                            break

            elif current_failure and line.strip() and not line.startswith(" " * 4):
                # End of error traceback
                if current_failure["error_message"]:
                    current_failure["full_error"] = "\n".join(current_failure["full_error"])
                    failures.append(current_failure)
                current_failure = None

            elif current_failure:
                # Accumulate error details
                current_failure["full_error"].append(line)

        return failures

    async def _analyze_test_file(self, test_file_path: str) -> List[Dict[str, Any]]:
        """Analyze test file for potential issues without running tests."""
        issues = []

        try:
            with open(test_file_path, 'r') as f:
                content = f.read()

            # Parse AST
            tree = ast.parse(content)

            # Check for common issues
            issues.extend(self._check_test_imports(tree, test_file_path))
            issues.extend(self._check_test_mocks(tree, test_file_path))
            issues.extend(self._check_test_structure(tree, test_file_path))

        except Exception as e:
            logger.error(f"Error analyzing test file {test_file_path}: {e}", exc_info=True)
            issues.append({
                "file": test_file_path,
                "issue": "analysis_error",
                "severity": "error",
                "details": f"Failed to analyze test file: {str(e)}"
            })

        return issues

    def _check_test_imports(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        """Check for import issues in test file."""
        issues = []

        # Track imports
        imports_found = set()
        import_aliases = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports_found.add(alias.name)
                    if alias.asname:
                        import_aliases[alias.asname] = alias.name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full_import = f"{module}.{alias.name}" if module else alias.name
                    imports_found.add(full_import)
                    if alias.asname:
                        import_aliases[alias.asname] = alias.name

        # Check for common problematic patterns
        # This would need to compare with actual available modules
        # For now, just check for obviously wrong patterns

        return issues

    def _check_test_mocks(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        """Check for mock-related issues."""
        issues = []

        # Look for AsyncMock usage (common in async tests)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for AsyncMock calls
                if isinstance(node.func, ast.Name):
                    if node.func.id == 'AsyncMock':
                        # Check if used correctly
                        pass

        return issues

    def _check_test_structure(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        """Check test structure issues."""
        issues = []

        # Count test methods
        test_methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                test_methods.append(node.name)

        if not test_methods:
            issues.append({
                "file": file_path,
                "issue": "no_test_methods",
                "severity": "warning",
                "details": "Test file contains no test_* methods"
            })

        return issues

    def _categorize_failures(self, failures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Categorize failures by type and frequency."""
        categories = {
            "signature_mismatch": [],
            "import_error": [],
            "mock_mismatch": [],
            "database_error": [],
            "other": []
        }

        for failure in failures:
            error_type = failure.get("error_type", "other")
            if error_type in categories:
                categories[error_type].append(failure)
            else:
                categories["other"].append(failure)

        # Calculate statistics
        stats = {}
        for category, items in categories.items():
            stats[category] = {
                "count": len(items),
                "tests": [f.get("test_name", "unknown") for f in items],
                "example": items[0] if items else None
            }

        return stats

    def _generate_failure_recommendations(self, categorized: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate recommendations based on failure categories."""
        recommendations = []

        # Signature mismatch recommendations
        sig_mismatches = categorized.get("signature_mismatch", {}).get("count", 0)
        if sig_mismatches > 0:
            recommendations.append({
                "action": "analyze_signature_mismatches",
                "priority": "high",
                "description": f"Found {sig_mismatches} signature mismatches between tests and implementations",
                "details": "Method signatures in tests don't match actual implementation",
                "auto_fix_possible": True
            })

        # Import error recommendations
        import_errors = categorized.get("import_error", {}).get("count", 0)
        if import_errors > 0:
            recommendations.append({
                "action": "fix_import_errors",
                "priority": "high",
                "description": f"Found {import_errors} import errors in tests",
                "details": "Missing or incorrect imports in test files",
                "auto_fix_possible": True
            })

        # Mock mismatch recommendations
        mock_mismatches = categorized.get("mock_mismatch", {}).get("count", 0)
        if mock_mismatches > 0:
            recommendations.append({
                "action": "fix_mock_expectations",
                "priority": "medium",
                "description": f"Found {mock_mismatches} mock expectation mismatches",
                "details": "Mock expectations don't match actual calls",
                "auto_fix_possible": True
            })

        return recommendations

    async def _store_analysis_results(self, results: Dict[str, Any]) -> None:
        """Store analysis results in memory system."""
        try:
            await self.memory_system.store_memory(
                agent_id=self.agent_id,
                content=json.dumps(results, default=str),
                memory_type="test_analysis",
                tags=["test_analysis", results.get("status", "unknown")],
                metadata={
                    "timestamp": results["timestamp"],
                    "total_issues": results.get("summary", {}).get("total_issues", 0),
                    "test_file": results.get("test_file"),
                    "agent_id": self.agent_id
                }
            )
        except Exception as e:
            logger.error(f"Failed to store analysis results in memory: {e}")

    # ============ Signature Analysis Methods ============

    async def extract_method_signatures(
        self,
        source_file: str,
        class_name: Optional[str] = None,
        method_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract method signatures from Python source file.

        Returns:
            Dictionary with method signatures.
        """
        logger.info(f"Extracting method signatures from {source_file} (class: {class_name}, method: {method_name})")

        results = {
            "timestamp": datetime.now().isoformat(),
            "source_file": source_file,
            "class_name": class_name,
            "method_name": method_name,
            "classes": {},
            "functions": {},
            "imports": [],
            "status": "unknown"
        }

        try:
            if not os.path.exists(source_file):
                results["status"] = "error"
                results["error"] = f"File not found: {source_file}"
                return results

            with open(source_file, 'r') as f:
                content = f.read()

            tree = ast.parse(content)

            # Extract imports
            results["imports"] = self._extract_imports(tree)

            # Extract classes and methods
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if this is the class we're looking for
                    if class_name and node.name != class_name:
                        continue

                    class_info = {
                        "name": node.name,
                        "methods": {},
                        "bases": [ast.unparse(base) for base in node.bases],
                        "docstring": ast.get_docstring(node)
                    }

                    # Extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            # Check if this is the method we're looking for
                            if method_name and item.name != method_name:
                                continue

                            method_info = self._extract_method_info(item)
                            class_info["methods"][item.name] = method_info

                    results["classes"][node.name] = class_info

                elif isinstance(node, ast.FunctionDef) and not class_name:
                    # Standalone function
                    if method_name and node.name != method_name:
                        continue

                    func_info = self._extract_method_info(node)
                    results["functions"][node.name] = func_info

            results["status"] = "success"
            results["summary"] = {
                "classes_found": len(results["classes"]),
                "methods_found": sum(len(c["methods"]) for c in results["classes"].values()),
                "functions_found": len(results["functions"])
            }

        except Exception as e:
            logger.error(f"Error extracting method signatures: {e}", exc_info=True)
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract import statements from AST."""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append({
                        "type": "from_import",
                        "module": node.module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "level": node.level,
                        "line": node.lineno
                    })

        return imports

    def _extract_method_info(self, func_node: ast.FunctionDef) -> Dict[str, Any]:
        """Extract method information from function definition."""
        # Extract parameters
        args = func_node.args
        parameters = []

        # Positional arguments
        for arg in args.args:
            parameters.append({
                "name": arg.arg,
                "type": "positional",
                "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
                "default": None
            })

        # Default arguments
        for i, default in enumerate(args.defaults):
            idx = len(args.args) - len(args.defaults) + i
            if idx < len(parameters):
                parameters[idx]["default"] = ast.unparse(default)

        # *args and **kwargs
        if args.vararg:
            parameters.append({
                "name": args.vararg.arg,
                "type": "vararg",
                "annotation": ast.unparse(args.vararg.annotation) if args.vararg.annotation else None
            })

        if args.kwarg:
            parameters.append({
                "name": args.kwarg.arg,
                "type": "kwarg",
                "annotation": ast.unparse(args.kwarg.annotation) if args.kwarg.annotation else None
            })

        # Return annotation
        return_annotation = ast.unparse(func_node.returns) if func_node.returns else None

        # Decorators
        decorators = [ast.unparse(decorator) for decorator in func_node.decorator_list]

        # Async?
        is_async = isinstance(func_node, ast.AsyncFunctionDef)

        return {
            "name": func_node.name,
            "parameters": parameters,
            "return_annotation": return_annotation,
            "decorators": decorators,
            "async": is_async,
            "docstring": ast.get_docstring(func_node),
            "line_number": func_node.lineno
        }

    # ============ Test-Implementation Comparison ============

    async def compare_test_with_implementation(
        self,
        test_file: str,
        source_file: str,
        generate_report: bool = True
    ) -> Dict[str, Any]:
        """
        Compare test expectations with actual implementation signatures.

        Returns:
            Dictionary with comparison results and mismatches.
        """
        logger.info(f"Comparing test {test_file} with implementation {source_file}")

        results = {
            "timestamp": datetime.now().isoformat(),
            "test_file": test_file,
            "source_file": source_file,
            "mismatches": [],
            "matches": [],
            "warnings": [],
            "status": "unknown"
        }

        try:
            # Extract test expectations
            test_expectations = await self.extract_test_expectations(test_file)
            if test_expectations.get("status") != "success":
                results["status"] = "error"
                results["error"] = test_expectations.get("error", "Failed to extract test expectations")
                return results

            # Extract implementation signatures
            impl_signatures = await self.extract_method_signatures(source_file)
            if impl_signatures.get("status") != "success":
                results["status"] = "error"
                results["error"] = impl_signatures.get("error", "Failed to extract implementation signatures")
                return results

            # Compare test calls with implementation
            mismatches = await self._compare_test_calls_with_implementation(
                test_expectations, impl_signatures
            )

            results["mismatches"] = mismatches
            results["matches"] = self._find_matches(test_expectations, impl_signatures)
            results["summary"] = {
                "total_test_calls": len(test_expectations.get("test_calls", [])),
                "total_mismatches": len(mismatches),
                "total_matches": len(results["matches"])
            }

            if generate_report:
                results["report"] = self._generate_comparison_report(results)

            results["status"] = "success"

            # Store comparison results
            await self.memory_system.store_memory(
                agent_id=self.agent_id,
                content=json.dumps(results, default=str),
                memory_type="test_comparison",
                tags=["test_comparison", results["status"]],
                metadata={
                    "timestamp": results["timestamp"],
                    "test_file": test_file,
                    "source_file": source_file,
                    "mismatches_found": len(mismatches)
                }
            )

        except Exception as e:
            logger.error(f"Error comparing test with implementation: {e}", exc_info=True)
            results["status"] = "error"
            results["error"] = str(e)

        return results

    async def extract_test_expectations(
        self,
        test_file: str,
        test_class: Optional[str] = None,
        test_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract method calls and expectations from test file.

        Returns:
            Dictionary with test expectations.
        """
        logger.info(f"Extracting test expectations from {test_file} (class: {test_class}, method: {test_method})")

        results = {
            "timestamp": datetime.now().isoformat(),
            "test_file": test_file,
            "test_class": test_class,
            "test_method": test_method,
            "test_calls": [],
            "imports": [],
            "mock_setups": [],
            "status": "unknown"
        }

        try:
            if not os.path.exists(test_file):
                results["status"] = "error"
                results["error"] = f"File not found: {test_file}"
                return results

            with open(test_file, 'r') as f:
                content = f.read()

            tree = ast.parse(content)

            # Extract imports
            results["imports"] = self._extract_imports(tree)

            # Find test classes and methods
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if this is the test class we're looking for
                    if test_class and node.name != test_class:
                        continue

                    # Check if it's a test class (name starts with Test or contains test)
                    is_test_class = node.name.startswith('Test') or 'test' in node.name.lower()

                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            # Check if this is the test method we're looking for
                            if test_method and item.name != test_method:
                                continue

                            # Check if it's a test method
                            is_test_method = item.name.startswith('test_')

                            if is_test_class or is_test_method:
                                # Extract method calls from this test
                                test_calls = self._extract_method_calls_from_test(item)
                                for call in test_calls:
                                    call["test_class"] = node.name
                                    call["test_method"] = item.name
                                    results["test_calls"].append(call)

            results["status"] = "success"
            results["summary"] = {
                "test_calls_found": len(results["test_calls"])
            }

        except Exception as e:
            logger.error(f"Error extracting test expectations: {e}", exc_info=True)
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def _extract_method_calls_from_test(self, func_node: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Extract method calls from a test function."""
        calls = []

        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                # Try to extract call information
                call_info = self._extract_call_info(node)
                if call_info:
                    calls.append(call_info)

        return calls

    def _extract_call_info(self, call_node: ast.Call) -> Optional[Dict[str, Any]]:
        """Extract information from a method call."""
        try:
            # Get the function being called
            if isinstance(call_node.func, ast.Attribute):
                # obj.method()
                if isinstance(call_node.func.value, ast.Name):
                    obj_name = call_node.func.value.id
                    method_name = call_node.func.attr
                    call_string = f"{obj_name}.{method_name}"
                else:
                    # Complex attribute chain, skip for now
                    return None
            elif isinstance(call_node.func, ast.Name):
                # function()
                obj_name = None
                method_name = call_node.func.id
                call_string = method_name
            else:
                return None

            # Extract arguments
            args = []
            keywords = {}

            for i, arg in enumerate(call_node.args):
                try:
                    arg_value = ast.unparse(arg)
                    args.append({
                        "position": i,
                        "value": arg_value[:100] if arg_value else None  # Truncate long values
                    })
                except:
                    args.append({
                        "position": i,
                        "value": "COMPLEX_EXPRESSION"
                    })

            for keyword in call_node.keywords:
                if keyword.arg:  # Not **kwargs
                    try:
                        keyword_value = ast.unparse(keyword.value)
                        keywords[keyword.arg] = keyword_value[:100] if keyword_value else None
                    except:
                        keywords[keyword.arg] = "COMPLEX_EXPRESSION"

            return {
                "object": obj_name,
                "method": method_name,
                "call_string": call_string,
                "args": args,
                "keywords": keywords,
                "line_number": call_node.lineno
            }

        except Exception as e:
            logger.debug(f"Failed to extract call info: {e}")
            return None

    async def _compare_test_calls_with_implementation(
        self,
        test_expectations: Dict[str, Any],
        impl_signatures: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Compare test calls with implementation signatures."""
        mismatches = []

        test_calls = test_expectations.get("test_calls", [])
        impl_classes = impl_signatures.get("classes", {})
        impl_functions = impl_signatures.get("functions", {})

        for call in test_calls:
            call_string = call.get("call_string", "")
            method_name = call.get("method", "")

            # Try to find matching implementation
            found_match = False
            mismatch_details = None

            # Check classes
            for class_name, class_info in impl_classes.items():
                if method_name in class_info.get("methods", {}):
                    method_info = class_info["methods"][method_name]
                    mismatch_details = self._compare_call_with_method_signature(call, method_info)
                    found_match = True
                    break

            # Check standalone functions
            if not found_match and method_name in impl_functions:
                method_info = impl_functions[method_name]
                mismatch_details = self._compare_call_with_method_signature(call, method_info)
                found_match = True

            if mismatch_details:
                mismatch_details.update({
                    "test_call": call,
                    "call_string": call_string,
                    "line_number": call.get("line_number")
                })
                mismatches.append(mismatch_details)

        return mismatches

    def _compare_call_with_method_signature(
        self,
        call: Dict[str, Any],
        method_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Compare a test call with a method signature."""
        issues = []

        call_keywords = set(call.get("keywords", {}).keys())
        method_params = method_info.get("parameters", [])

        # Extract parameter names from method signature
        method_param_names = set()
        positional_params = []
        keyword_params = []

        for param in method_params:
            param_name = param.get("name")
            param_type = param.get("type", "positional")
            if param_name:
                method_param_names.add(param_name)
                if param_type == "positional":
                    positional_params.append(param_name)
                elif param_type not in ["vararg", "kwarg"]:
                    keyword_params.append(param_name)

        # Check for unexpected keyword arguments
        for keyword in call_keywords:
            if keyword not in method_param_names:
                issues.append({
                    "type": "unexpected_keyword",
                    "keyword": keyword,
                    "message": f"Method '{method_info.get('name')}' doesn't accept keyword argument '{keyword}'"
                })

        # Check if method is async but test doesn't await (basic check)
        if method_info.get("async") and not call.get("call_string", "").startswith("await "):
            # This is heuristic - would need more sophisticated analysis
            pass

        if issues:
            return {
                "method_name": method_info.get("name"),
                "issues": issues,
                "method_signature": method_info,
                "severity": "high" if any(i["type"] == "unexpected_keyword" for i in issues) else "medium"
            }

        return None

    def _find_matches(
        self,
        test_expectations: Dict[str, Any],
        impl_signatures: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find test calls that match implementation signatures."""
        matches = []

        test_calls = test_expectations.get("test_calls", [])
        impl_classes = impl_signatures.get("classes", {})
        impl_functions = impl_signatures.get("functions", {})

        for call in test_calls:
            method_name = call.get("method", "")

            # Check classes
            for class_name, class_info in impl_classes.items():
                if method_name in class_info.get("methods", {}):
                    matches.append({
                        "test_call": call,
                        "implementation": class_info["methods"][method_name],
                        "type": "class_method",
                        "class_name": class_name
                    })
                    break

            # Check standalone functions
            if method_name in impl_functions:
                matches.append({
                    "test_call": call,
                    "implementation": impl_functions[method_name],
                    "type": "function"
                })

        return matches

    def _generate_comparison_report(self, comparison_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a detailed comparison report."""
        mismatches = comparison_results.get("mismatches", [])
        matches = comparison_results.get("matches", [])

        # Categorize mismatches
        categories = {}
        for mismatch in mismatches:
            for issue in mismatch.get("issues", []):
                issue_type = issue.get("type", "unknown")
                if issue_type not in categories:
                    categories[issue_type] = []
                categories[issue_type].append(mismatch)

        return {
            "summary": {
                "total_mismatches": len(mismatches),
                "total_matches": len(matches),
                "mismatch_categories": {k: len(v) for k, v in categories.items()}
            },
            "critical_mismatches": [m for m in mismatches if m.get("severity") == "high"],
            "all_mismatches": mismatches,
            "categories": categories,
            "recommendations": self._generate_comparison_recommendations(mismatches)
        }

    def _generate_comparison_recommendations(self, mismatches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate recommendations based on comparison results."""
        recommendations = []

        if mismatches:
            # Group by method
            methods = {}
            for mismatch in mismatches:
                method_name = mismatch.get("method_name", "unknown")
                if method_name not in methods:
                    methods[method_name] = []
                methods[method_name].append(mismatch)

            for method_name, method_mismatches in methods.items():
                # Check for signature mismatches
                signature_issues = []
                for mismatch in method_mismatches:
                    for issue in mismatch.get("issues", []):
                        if issue.get("type") == "unexpected_keyword":
                            signature_issues.append(issue)

                if signature_issues:
                    unexpected_keywords = [issue.get("keyword") for issue in signature_issues]
                    recommendations.append({
                        "action": "update_test_signature",
                        "method": method_name,
                        "priority": "high",
                        "description": f"Test calls to '{method_name}' use unexpected keywords: {', '.join(unexpected_keywords)}",
                        "details": signature_issues,
                        "auto_fix_possible": True
                    })

        return recommendations

    # ============ Public API Methods ============

    async def run_synchronization_pipeline(
        self,
        test_file: Optional[str] = None,
        source_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run complete test synchronization pipeline.

        Returns:
            Comprehensive synchronization report.
        """
        logger.info(f"Running test synchronization pipeline (test: {test_file}, source: {source_file})")

        pipeline_results = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "test_file": test_file,
            "source_file": source_file,
            "steps": [],
            "corrections_generated": 0,
            "corrections_applied": 0,
            "overall_status": "unknown"
        }

        try:
            # Step 1: Test failure analysis
            if test_file:
                test_analysis = await self.analyze_test_failures(test_file=test_file)
                pipeline_results["steps"].append({
                    "step": "test_failure_analysis",
                    "status": test_analysis.get("status", "error"),
                    "issues_found": len(test_analysis.get("failure_patterns", [])),
                    "details": test_analysis
                })

            # Step 2: Test-implementation comparison
            if test_file and source_file:
                comparison = await self.compare_test_with_implementation(test_file, source_file)
                pipeline_results["steps"].append({
                    "step": "test_implementation_comparison",
                    "status": comparison.get("status", "error"),
                    "mismatches_found": len(comparison.get("mismatches", [])),
                    "details": comparison
                })

                # Step 3: Generate corrections if mismatches found
                mismatches = comparison.get("mismatches", [])
                if mismatches and source_file:
                    # For now, just report the mismatches
                    # In a full implementation, this would generate and apply corrections
                    pipeline_results["corrections_needed"] = len(mismatches)
                    pipeline_results["mismatch_summary"] = {
                        "total": len(mismatches),
                        "by_severity": {
                            "high": sum(1 for m in mismatches if m.get("severity") == "high"),
                            "medium": sum(1 for m in mismatches if m.get("severity") == "medium"),
                            "low": sum(1 for m in mismatches if m.get("severity") in ["low", None])
                        }
                    }

            # Determine overall status
            has_errors = any(
                step["details"].get("status") == "error"
                for step in pipeline_results["steps"]
            )
            has_mismatches = pipeline_results.get("corrections_needed", 0) > 0

            if has_errors:
                pipeline_results["overall_status"] = "pipeline_error"
            elif has_mismatches:
                pipeline_results["overall_status"] = "mismatches_found"
            else:
                pipeline_results["overall_status"] = "synchronized"

            # Store pipeline results
            await self.memory_system.store_memory(
                agent_id=self.agent_id,
                content=json.dumps(pipeline_results, default=str),
                memory_type="synchronization_pipeline",
                tags=["synchronization_pipeline", pipeline_results["overall_status"]],
                metadata={
                    "timestamp": pipeline_results["timestamp"],
                    "test_file": test_file,
                    "source_file": source_file,
                    "corrections_needed": pipeline_results.get("corrections_needed", 0)
                }
            )

        except Exception as e:
            logger.error(f"Error in synchronization pipeline: {e}", exc_info=True)
            pipeline_results["overall_status"] = "pipeline_error"
            pipeline_results["error"] = str(e)

        return pipeline_results


# ============ Agent Registration Helper ============

async def register_test_synchronizer_agent() -> TestSynchronizerAgent:
    """
    Register test synchronizer agent with the agent registry.

    Call this during system startup to register the test synchronizer agent.
    Returns existing agent if already registered.
    """
    from .registry import registry

    # Check if test synchronizer agent already exists by name
    existing_agent = await registry.get_agent_by_name("Test Synchronizer Agent")
    if existing_agent:
        logger.info(f"Test synchronizer agent already registered: {existing_agent.name}")
        return existing_agent

    # Create new test synchronizer agent using registry's create_agent method
    try:
        agent = await registry.create_agent(
            agent_type="test_synchronizer",
            name="Test Synchronizer Agent",
            description="Autonomous test synchronization and repair agent. Detects mismatches between test expectations and actual implementations, generates corrected test files, and validates fixes.",
            capabilities=[
                "test_analysis",
                "signature_extraction",
                "mismatch_detection",
                "test_correction",
                "test_validation",
                "coverage_analysis",
                "python_ast_parsing",
                "test_generation"
            ],
            domain="testing",
            config={
                "auto_correct_safe_fixes": False,
                "require_approval": True,
                "test_directory": "tests",
                "source_directory": "app",
                "backup_before_changes": True,
                "run_tests_after_fix": True,
                "max_corrections_per_run": 10,
            }
        )
        logger.info(f"Test synchronizer agent created and registered: {agent.name}")
        return agent
    except ValueError as e:
        # Likely duplicate name (race condition) - try to fetch again
        existing_agent = await registry.get_agent_by_name("Test Synchronizer Agent")
        if existing_agent:
            logger.info(f"Test synchronizer agent registered after race condition: {existing_agent.name}")
            return existing_agent
        raise e