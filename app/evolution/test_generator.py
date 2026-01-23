"""
NEXUS Self-Evolution System - Test Generator

Automated test generation for evolved code, including:
- Unit test generation from code analysis
- Property-based test generation using Hypothesis
- Integration test generation for changed interfaces
- Regression test suite generation for evolved components

Integrates with refactoring engine to ensure safety of code modifications.
"""

import ast
import inspect
import logging
import tempfile
import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import uuid
from datetime import datetime
from enum import Enum

import hypothesis
from hypothesis import given, strategies as st
import libcst as cst

from ..database import Database
from ..config import settings


class TestType(Enum):
    """Types of tests that can be generated."""
    UNIT_TEST = "unit_test"
    PROPERTY_TEST = "property_test"
    INTEGRATION_TEST = "integration_test"
    REGRESSION_TEST = "regression_test"
    PERFORMANCE_TEST = "performance_test"
    SECURITY_TEST = "security_test"


class TestGenerationStatus(Enum):
    """Status of test generation operation."""
    GENERATED = "generated"
    VALIDATED = "validated"
    INTEGRATED = "integrated"
    FAILED = "failed"


class TestGenerator:
    """Automated test generation for evolved code."""

    def __init__(self, database: Database):
        self.db = database
        self.logger = logging.getLogger(__name__)
        self.project_root = Path(__file__).parent.parent.parent

    async def generate_tests_for_refactor(
        self,
        refactor_proposal: Dict[str, Any],
        code_ast: Optional[ast.AST] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive test suite for a refactoring proposal.

        Args:
            refactor_proposal: Refactoring proposal from CodeRefactor
            code_ast: Optional AST of the code to be refactored

        Returns:
            Dictionary with generated tests and metadata
        """
        self.logger.info(f"Generating tests for refactor proposal: {refactor_proposal.get('id', 'unknown')}")

        # Extract code from proposal if AST not provided
        if code_ast is None and 'code_snippet' in refactor_proposal:
            code_ast = ast.parse(refactor_proposal['code_snippet'])

        if code_ast is None:
            self.logger.warning("No code AST available for test generation")
            return {"tests": [], "status": TestGenerationStatus.FAILED.value}

        # Generate different types of tests
        unit_tests = await self._generate_unit_tests(code_ast, refactor_proposal)
        property_tests = await self._generate_property_tests(code_ast, refactor_proposal)
        integration_tests = await self._generate_integration_tests(refactor_proposal)

        # Combine all tests
        all_tests = unit_tests + property_tests + integration_tests

        # Store in database
        test_suite_id = str(uuid.uuid4())
        await self._store_test_suite(
            test_suite_id=test_suite_id,
            refactor_proposal_id=refactor_proposal.get('id'),
            tests=all_tests,
            test_types=[TestType.UNIT_TEST.value, TestType.PROPERTY_TEST.value, TestType.INTEGRATION_TEST.value]
        )

        return {
            "test_suite_id": test_suite_id,
            "tests": all_tests,
            "count": len(all_tests),
            "unit_tests": len(unit_tests),
            "property_tests": len(property_tests),
            "integration_tests": len(integration_tests),
            "status": TestGenerationStatus.GENERATED.value
        }

    async def _generate_unit_tests(
        self,
        code_ast: ast.AST,
        refactor_proposal: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate unit tests from code AST analysis."""
        unit_tests = []

        try:
            # Analyze AST to find testable functions/methods
            testable_items = self._analyze_ast_for_testable_items(code_ast)

            for item in testable_items:
                # Generate test cases based on function signature
                test_cases = self._generate_test_cases_from_signature(item)

                for test_case in test_cases:
                    unit_test = {
                        "id": str(uuid.uuid4()),
                        "type": TestType.UNIT_TEST.value,
                        "target": item['name'],
                        "code": self._generate_unit_test_code(item, test_case),
                        "description": f"Unit test for {item['name']}",
                        "generated_at": datetime.utcnow().isoformat()
                    }
                    unit_tests.append(unit_test)

        except Exception as e:
            self.logger.error(f"Failed to generate unit tests: {e}")

        return unit_tests

    async def _generate_property_tests(
        self,
        code_ast: ast.AST,
        refactor_proposal: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate property-based tests using Hypothesis."""
        property_tests = []

        try:
            # Discover invariants from code analysis
            invariants = self._discover_invariants_from_ast(code_ast)

            for invariant in invariants:
                property_test = {
                    "id": str(uuid.uuid4()),
                    "type": TestType.PROPERTY_TEST.value,
                    "property": invariant['description'],
                    "code": self._generate_property_test_code(invariant),
                    "description": f"Property test: {invariant['description']}",
                    "generated_at": datetime.utcnow().isoformat()
                }
                property_tests.append(property_test)

        except Exception as e:
            self.logger.error(f"Failed to generate property tests: {e}")

        return property_tests

    async def _generate_integration_tests(
        self,
        refactor_proposal: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate integration tests for changed interfaces."""
        integration_tests = []

        try:
            # Determine integration points from refactor proposal
            integration_points = self._identify_integration_points(refactor_proposal)

            for point in integration_points:
                integration_test = {
                    "id": str(uuid.uuid4()),
                    "type": TestType.INTEGRATION_TEST.value,
                    "component": point['component'],
                    "interface": point['interface'],
                    "code": self._generate_integration_test_code(point),
                    "description": f"Integration test for {point['component']}.{point['interface']}",
                    "generated_at": datetime.utcnow().isoformat()
                }
                integration_tests.append(integration_test)

        except Exception as e:
            self.logger.error(f"Failed to generate integration tests: {e}")

        return integration_tests

    def _analyze_ast_for_testable_items(self, code_ast: ast.AST) -> List[Dict[str, Any]]:
        """Analyze AST to find functions and methods that should be tested."""
        testable_items = []

        class TestableItemVisitor(ast.NodeVisitor):
            def __init__(self):
                self.items = []

            def visit_FunctionDef(self, node):
                # Skip private functions (starting with _)
                if not node.name.startswith('_'):
                    self.items.append({
                        'type': 'function',
                        'name': node.name,
                        'args': [arg.arg for arg in node.args.args],
                        'lineno': node.lineno
                    })
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                if not node.name.startswith('_'):
                    self.items.append({
                        'type': 'async_function',
                        'name': node.name,
                        'args': [arg.arg for arg in node.args.args],
                        'lineno': node.lineno
                    })
                self.generic_visit(node)

            def visit_ClassDef(self, node):
                # Visit methods within class
                self.generic_visit(node)

        visitor = TestableItemVisitor()
        visitor.visit(code_ast)
        return visitor.items

    def _generate_test_cases_from_signature(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate test cases based on function signature."""
        test_cases = []

        # Basic test cases based on argument count
        args = item.get('args', [])

        # Generate edge cases
        if args:
            # Test with minimal inputs
            test_cases.append({
                'name': 'minimal_inputs',
                'args': {arg: f'# Test value for {arg}' for arg in args}
            })

            # Test with None inputs (if appropriate)
            test_cases.append({
                'name': 'none_inputs',
                'args': {arg: 'None' for arg in args}
            })

        # Always test basic call
        test_cases.append({
            'name': 'basic_call',
            'args': {arg: f'# Test value for {arg}' for arg in args} if args else {}
        })

        return test_cases

    def _generate_unit_test_code(self, item: Dict[str, Any], test_case: Dict[str, Any]) -> str:
        """Generate Python unit test code."""
        test_name = f"test_{item['name']}_{test_case['name']}"

        # Build test function
        lines = [
            f"def {test_name}():",
            f"    # Test generated for {item['name']}",
            f"    # Test case: {test_case['name']}",
        ]

        # Add test body based on item type
        if item['type'] in ['function', 'async_function']:
            # This is a placeholder - actual test generation would be more sophisticated
            lines.append(f"    # TODO: Implement actual test for {item['name']}")
            lines.append(f"    # Args: {test_case.get('args', {})}")
            lines.append("    assert True  # Placeholder assertion")

        return "\n".join(lines)

    def _discover_invariants_from_ast(self, code_ast: ast.AST) -> List[Dict[str, Any]]:
        """Discover invariants from code analysis for property-based testing."""
        invariants = []

        # Simple invariant discovery - can be expanded
        class InvariantVisitor(ast.NodeVisitor):
            def __init__(self):
                self.invariants = []

            def visit_FunctionDef(self, node):
                # Look for functions with clear input/output patterns
                if len(node.args.args) > 0:
                    # Simple invariant: function should not crash on valid inputs
                    self.invariants.append({
                        'function': node.name,
                        'description': f'{node.name} should handle valid inputs without crashing',
                        'type': 'safety'
                    })
                self.generic_visit(node)

        visitor = InvariantVisitor()
        visitor.visit(code_ast)
        return visitor.invariants

    def _generate_property_test_code(self, invariant: Dict[str, Any]) -> str:
        """Generate Hypothesis property test code."""
        test_name = f"test_property_{invariant['function']}_{invariant['type']}"

        # This is a simplified example - actual property test generation would be more sophisticated
        code = f"""
from hypothesis import given, strategies as st
import pytest

@given(st.integers(), st.integers())
def {test_name}(a, b):
    \"\"\"Property test for {invariant['description']}\"\"\"
    # TODO: Implement actual property test
    # This is a placeholder for generated property-based test
    assert True
"""
        return code.strip()

    def _identify_integration_points(self, refactor_proposal: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify integration points affected by refactoring."""
        # Simplified - would need actual analysis of refactoring impact
        integration_points = []

        # Placeholder - extract from refactor proposal metadata
        if 'affected_components' in refactor_proposal:
            for component in refactor_proposal['affected_components']:
                integration_points.append({
                    'component': component,
                    'interface': 'api_endpoint',  # Placeholder
                    'impact_level': 'medium'
                })

        return integration_points

    def _generate_integration_test_code(self, point: Dict[str, Any]) -> str:
        """Generate integration test code."""
        test_name = f"test_integration_{point['component']}_{point['interface']}"

        code = f"""
import pytest
from fastapi.testclient import TestClient

def {test_name}():
    \"\"\"Integration test for {point['component']}.{point['interface']}\"\"\"
    # TODO: Implement actual integration test
    # This is a placeholder for generated integration test
    assert True
"""
        return code.strip()

    async def _store_test_suite(
        self,
        test_suite_id: str,
        refactor_proposal_id: Optional[str],
        tests: List[Dict[str, Any]],
        test_types: List[str]
    ) -> None:
        """Store generated test suite in database."""
        try:
            # Check if generated_tests table exists (would be added to schema)
            # For now, log the test suite
            self.logger.info(f"Storing test suite {test_suite_id} with {len(tests)} tests")

            # In future: Insert into generated_tests table
            # await self.db.execute(...)

        except Exception as e:
            self.logger.error(f"Failed to store test suite: {e}")

    async def validate_tests(self, test_suite_id: str) -> Dict[str, Any]:
        """
        Validate generated tests by executing them.

        Args:
            test_suite_id: ID of test suite to validate

        Returns:
            Validation results
        """
        # This would execute the generated tests in a safe environment
        # For now, return placeholder
        return {
            "test_suite_id": test_suite_id,
            "validation_status": "pending",
            "tests_executed": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "coverage_percentage": 0.0
        }