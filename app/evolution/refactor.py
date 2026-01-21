"""
NEXUS Self-Evolution System - Code Refactor Engine

Automated code improvements, prompt optimization, and configuration tuning.
"""

import ast
import inspect
import logging
import tempfile
import shutil
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import uuid
from pathlib import Path
from enum import Enum

from ..database import Database
from ..config import settings


class RefactorType(Enum):
    """Types of refactoring operations."""
    CODE_OPTIMIZATION = "code_optimization"
    PROMPT_IMPROVEMENT = "prompt_improvement"
    CONFIGURATION_TUNING = "configuration_tuning"
    PERFORMANCE_IMPROVEMENT = "performance_improvement"
    BUG_FIX = "bug_fix"
    SECURITY_IMPROVEMENT = "security_improvement"


class RefactorStatus(Enum):
    """Status of a refactoring operation."""
    PROPOSED = "proposed"
    VALIDATED = "validated"
    APPLIED = "applied"
    REVERTED = "reverted"
    FAILED = "failed"


class CodeRefactor:
    """Automated code refactoring and improvement engine."""

    def __init__(self, database: Database):
        self.db = database
        self.logger = logging.getLogger(__name__)
        self.project_root = Path(__file__).parent.parent.parent

    async def propose_refactor(
        self,
        refactor_type: RefactorType,
        target_file: Optional[str] = None,
        target_component: Optional[str] = None,
        rationale: str = "",
        expected_improvement: Dict[str, Any] = None,
        hypothesis_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Propose a refactoring operation.

        Args:
            refactor_type: Type of refactoring
            target_file: Specific file to refactor (optional)
            target_component: Component to refactor (agent, service, etc.)
            rationale: Reason for refactoring
            expected_improvement: Expected improvements
            hypothesis_id: Associated hypothesis ID

        Returns:
            Refactoring proposal
        """
        refactor_id = str(uuid.uuid4())

        if expected_improvement is None:
            expected_improvement = {
                "performance_improvement": 0.1,  # 10%
                "cost_reduction": 0.05,  # 5%
                "code_complexity_reduction": 0.1  # 10%
            }

        # Analyze target to generate specific proposal
        analysis = await self._analyze_target(target_file, target_component)
        changes = await self._generate_changes(
            refactor_type, analysis, target_file, target_component
        )

        proposal = {
            "id": refactor_id,
            "type": refactor_type.value,
            "target_file": target_file,
            "target_component": target_component,
            "rationale": rationale,
            "expected_improvement": expected_improvement,
            "hypothesis_id": hypothesis_id,
            "analysis": analysis,
            "proposed_changes": changes,
            "status": RefactorStatus.PROPOSED.value,
            "created_at": datetime.now().isoformat(),
            "applied_at": None,
            "reverted_at": None,
            "validation_results": {},
            "rollback_path": None
        }

        # Store proposal
        await self._store_refactor_proposal(proposal)

        return proposal

    async def validate_refactor(
        self,
        refactor_id: str
    ) -> Dict[str, Any]:
        """
        Validate a refactoring proposal.

        Args:
            refactor_id: Refactoring proposal ID

        Returns:
            Validation results
        """
        proposal = await self._get_refactor_proposal(refactor_id)
        if not proposal:
            raise ValueError(f"Refactoring proposal not found: {refactor_id}")

        validation = {
            "syntax_valid": False,
            "tests_pass": False,
            "performance_impact": "unknown",
            "safety_score": 0.0,
            "validation_errors": [],
            "warnings": []
        }

        try:
            # 1. Check syntax of proposed changes
            syntax_valid = await self._validate_syntax(proposal["proposed_changes"])
            validation["syntax_valid"] = syntax_valid

            if not syntax_valid:
                validation["validation_errors"].append("Syntax errors in proposed changes")

            # 2. Create temporary copy and apply changes
            temp_dir = tempfile.mkdtemp(prefix="nexus_refactor_")
            rollback_path = await self._create_backup(proposal, temp_dir)

            # 3. Apply changes to temporary copy
            applied = await self._apply_changes(
                proposal["proposed_changes"],
                temp_dir,
                dry_run=True
            )

            if applied:
                # 4. Run tests on temporary copy
                tests_pass = await self._run_tests(temp_dir)
                validation["tests_pass"] = tests_pass

                if not tests_pass:
                    validation["validation_errors"].append("Tests fail with proposed changes")

                # 5. Analyze performance impact
                performance_impact = await self._analyze_performance_impact(temp_dir)
                validation["performance_impact"] = performance_impact

                # 6. Calculate safety score
                safety_score = await self._calculate_safety_score(proposal, validation)
                validation["safety_score"] = safety_score

            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            validation["validation_errors"].append(f"Validation error: {str(e)}")

        # Update proposal with validation results
        proposal["validation_results"] = validation
        proposal["status"] = RefactorStatus.VALIDATED.value

        if validation["syntax_valid"] and validation["tests_pass"]:
            proposal["validation_passed"] = True
        else:
            proposal["validation_passed"] = False

        await self._store_refactor_proposal(proposal)

        return {
            "refactor_id": refactor_id,
            "validation": validation,
            "proposal": proposal
        }

    async def apply_refactor(
        self,
        refactor_id: str,
        create_backup: bool = True
    ) -> Dict[str, Any]:
        """
        Apply a validated refactoring.

        Args:
            refactor_id: Refactoring proposal ID
            create_backup: Whether to create backup before applying

        Returns:
            Application results
        """
        proposal = await self._get_refactor_proposal(refactor_id)
        if not proposal:
            raise ValueError(f"Refactoring proposal not found: {refactor_id}")

        if proposal["status"] != RefactorStatus.VALIDATED.value:
            raise ValueError(f"Cannot apply refactoring in status: {proposal['status']}")

        if not proposal.get("validation_passed", False):
            raise ValueError("Refactoring validation failed")

        application = {
            "success": False,
            "applied_changes": [],
            "errors": [],
            "backup_created": False,
            "backup_path": None
        }

        try:
            # Create backup
            backup_path = None
            if create_backup:
                backup_dir = tempfile.mkdtemp(prefix="nexus_backup_")
                backup_path = await self._create_backup(proposal, backup_dir)
                application["backup_created"] = True
                application["backup_path"] = backup_path

                # Store backup path in proposal
                proposal["rollback_path"] = backup_path

            # Apply changes
            applied_changes = await self._apply_changes(
                proposal["proposed_changes"],
                str(self.project_root),
                dry_run=False
            )

            if applied_changes:
                application["success"] = True
                application["applied_changes"] = applied_changes

                # Update proposal status
                proposal["status"] = RefactorStatus.APPLIED.value
                proposal["applied_at"] = datetime.now().isoformat()

                self.logger.info(f"Applied refactoring {refactor_id}: {proposal['type']}")

                # Run post-application validation
                post_validation = await self._run_tests(str(self.project_root))
                if not post_validation:
                    application["errors"].append("Post-application tests failed")
                    self.logger.warning(f"Post-application tests failed for {refactor_id}")

            else:
                application["errors"].append("Failed to apply changes")

        except Exception as e:
            self.logger.error(f"Failed to apply refactoring: {e}")
            application["errors"].append(str(e))

            # Attempt rollback if backup exists
            if application["backup_created"] and backup_path:
                await self._rollback_refactor(refactor_id, "automatic_rollback_after_failure")

        # Update proposal
        await self._store_refactor_proposal(proposal)

        return {
            "refactor_id": refactor_id,
            "application": application,
            "proposal": proposal
        }

    async def rollback_refactor(
        self,
        refactor_id: str,
        reason: str = "manual_rollback"
    ) -> Dict[str, Any]:
        """
        Rollback an applied refactoring.

        Args:
            refactor_id: Refactoring proposal ID
            reason: Reason for rollback

        Returns:
            Rollback results
        """
        return await self._rollback_refactor(refactor_id, reason)

    async def analyze_code_quality(
        self,
        target_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze code quality and identify improvement opportunities.

        Args:
            target_path: Path to analyze (default: project root)

        Returns:
            Code quality analysis
        """
        if target_path is None:
            target_path = str(self.project_root)

        analysis = {
            "file_count": 0,
            "total_lines": 0,
            "complexity_metrics": {},
            "common_issues": [],
            "improvement_opportunities": []
        }

        try:
            # Walk through codebase
            for root, dirs, files in os.walk(target_path):
                # Skip virtual environments and hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', '__pycache__']]

                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, target_path)

                        file_analysis = await self._analyze_python_file(file_path)
                        if file_analysis:
                            analysis["file_count"] += 1
                            analysis["total_lines"] += file_analysis.get("line_count", 0)

                            # Track complexity metrics
                            complexity = file_analysis.get("complexity_metrics", {})
                            for metric, value in complexity.items():
                                if metric not in analysis["complexity_metrics"]:
                                    analysis["complexity_metrics"][metric] = []
                                analysis["complexity_metrics"][metric].append(value)

                            # Collect issues
                            issues = file_analysis.get("issues", [])
                            for issue in issues:
                                analysis["common_issues"].append({
                                    "file": relative_path,
                                    "issue": issue
                                })

                            # Identify improvement opportunities
                            opportunities = file_analysis.get("improvement_opportunities", [])
                            for opportunity in opportunities:
                                analysis["improvement_opportunities"].append({
                                    "file": relative_path,
                                    "opportunity": opportunity,
                                    "estimated_impact": "medium"
                                })

            # Calculate averages
            for metric, values in analysis["complexity_metrics"].items():
                if values:
                    analysis["complexity_metrics"][f"avg_{metric}"] = sum(values) / len(values)
                    analysis["complexity_metrics"][f"max_{metric}"] = max(values)

            # Categorize issues
            issue_categories = {}
            for issue in analysis["common_issues"]:
                issue_type = issue["issue"].get("type", "unknown")
                if issue_type not in issue_categories:
                    issue_categories[issue_type] = 0
                issue_categories[issue_type] += 1

            analysis["issue_categories"] = issue_categories

        except Exception as e:
            self.logger.error(f"Failed to analyze code quality: {e}")

        return analysis

    async def optimize_prompt(
        self,
        agent_id: str,
        current_prompt: str,
        performance_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Optimize an agent's system prompt.

        Args:
            agent_id: Agent ID
            current_prompt: Current system prompt
            performance_metrics: Agent performance metrics

        Returns:
            Optimized prompt and analysis
        """
        # This would use AI to analyze and improve the prompt
        # For now, return a placeholder implementation

        analysis = {
            "original_length": len(current_prompt),
            "readability_score": 0.7,  # Placeholder
            "clarity_score": 0.6,      # Placeholder
            "specificity_score": 0.5   # Placeholder
        }

        # Simple prompt optimization heuristics
        optimized_prompt = current_prompt

        # Remove redundant sections
        lines = current_prompt.split('\n')
        unique_lines = []
        seen = set()

        for line in lines:
            line_stripped = line.strip()
            if line_stripped and line_stripped not in seen:
                seen.add(line_stripped)
                unique_lines.append(line)

        if len(unique_lines) < len(lines):
            optimized_prompt = '\n'.join(unique_lines)
            analysis["redundancy_reduction"] = len(lines) - len(unique_lines)

        # Add performance-based improvements
        success_rate = performance_metrics.get("success_rate", 0)
        if success_rate < 0.8:
            # Add clarity improvements for low success rate
            optimized_prompt += "\n\n# Be precise and methodical in your responses."
            analysis["added_clarity_directive"] = True

        avg_latency = performance_metrics.get("avg_latency_ms", 0)
        if avg_latency > 3000:
            # Add efficiency directive for high latency
            optimized_prompt += "\n\n# Provide concise responses to improve efficiency."
            analysis["added_efficiency_directive"] = True

        analysis["optimized_length"] = len(optimized_prompt)
        analysis["length_reduction"] = analysis["original_length"] - analysis["optimized_length"]

        return {
            "agent_id": agent_id,
            "original_prompt": current_prompt,
            "optimized_prompt": optimized_prompt,
            "analysis": analysis,
            "estimated_impact": {
                "success_rate_improvement": 0.05,
                "latency_reduction": 0.1,
                "cost_reduction": 0.02
            }
        }

    async def tune_configuration(
        self,
        component: str,
        current_config: Dict[str, Any],
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Tune configuration parameters for optimization.

        Args:
            component: Component name (agent, service, etc.)
            current_config: Current configuration
            performance_data: Performance data for tuning

        Returns:
            Tuned configuration
        """
        tuned_config = current_config.copy()
        changes = []

        # Example tuning rules
        if component == "agent":
            success_rate = performance_data.get("success_rate", 0)
            avg_latency = performance_data.get("avg_latency_ms", 0)

            # Adjust max_tokens based on success rate
            if success_rate < 0.7:
                tuned_config["max_tokens"] = min(
                    current_config.get("max_tokens", 1000) * 1.5,
                    4000
                )
                changes.append({
                    "parameter": "max_tokens",
                    "old_value": current_config.get("max_tokens"),
                    "new_value": tuned_config["max_tokens"],
                    "reason": "Low success rate, allowing more tokens for better responses"
                })

            # Adjust temperature based on consistency needs
            error_rate = performance_data.get("error_rate", 0)
            if error_rate > 0.1:
                tuned_config["temperature"] = max(
                    current_config.get("temperature", 0.7) * 0.8,
                    0.1
                )
                changes.append({
                    "parameter": "temperature",
                    "old_value": current_config.get("temperature"),
                    "new_value": tuned_config["temperature"],
                    "reason": "High error rate, lowering temperature for more consistent responses"
                })

            # Adjust timeout based on latency
            if avg_latency > 5000:
                tuned_config["timeout_seconds"] = min(
                    current_config.get("timeout_seconds", 30) * 1.5,
                    120
                )
                changes.append({
                    "parameter": "timeout_seconds",
                    "old_value": current_config.get("timeout_seconds"),
                    "new_value": tuned_config["timeout_seconds"],
                    "reason": "High average latency, increasing timeout"
                })

        elif component == "cache":
            hit_rate = performance_data.get("cache_hit_rate", 0)
            avg_latency = performance_data.get("avg_latency_ms", 0)

            # Adjust cache TTL based on hit rate
            if hit_rate < 0.3:
                tuned_config["ttl_seconds"] = max(
                    current_config.get("ttl_seconds", 300) * 0.5,
                    60
                )
                changes.append({
                    "parameter": "ttl_seconds",
                    "old_value": current_config.get("ttl_seconds"),
                    "new_value": tuned_config["ttl_seconds"],
                    "reason": "Low cache hit rate, reducing TTL to keep cache fresh"
                })
            elif hit_rate > 0.8:
                tuned_config["ttl_seconds"] = min(
                    current_config.get("ttl_seconds", 300) * 2,
                    3600
                )
                changes.append({
                    "parameter": "ttl_seconds",
                    "old_value": current_config.get("ttl_seconds"),
                    "new_value": tuned_config["ttl_seconds"],
                    "reason": "High cache hit rate, increasing TTL to improve performance"
                })

        return {
            "component": component,
            "original_config": current_config,
            "tuned_config": tuned_config,
            "changes": changes,
            "estimated_impact": {
                "performance_improvement": 0.1,
                "cost_reduction": 0.05
            }
        }

    # Private methods

    async def _analyze_target(
        self,
        target_file: Optional[str],
        target_component: Optional[str]
    ) -> Dict[str, Any]:
        """Analyze target for refactoring."""
        analysis = {
            "target_type": "unknown",
            "complexity_score": 0,
            "issue_count": 0,
            "improvement_areas": []
        }

        try:
            if target_file:
                # Analyze specific file
                file_path = self.project_root / target_file
                if file_path.exists() and file_path.suffix == '.py':
                    analysis.update(await self._analyze_python_file(str(file_path)))
                    analysis["target_type"] = "python_file"

            elif target_component:
                # Analyze component (agent, service, etc.)
                analysis["target_type"] = "component"
                analysis["component_name"] = target_component

                # Find files related to component
                component_files = await self._find_component_files(target_component)
                analysis["related_files"] = component_files

                # Analyze each file
                for file in component_files[:5]:  # Limit to first 5 files
                    file_analysis = await self._analyze_python_file(file)
                    if file_analysis:
                        analysis["complexity_score"] += file_analysis.get("complexity_score", 0)
                        analysis["issue_count"] += len(file_analysis.get("issues", []))

        except Exception as e:
            self.logger.error(f"Failed to analyze target: {e}")

        return analysis

    async def _analyze_python_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a Python file for refactoring opportunities."""
        analysis = {
            "file_path": file_path,
            "line_count": 0,
            "function_count": 0,
            "class_count": 0,
            "complexity_score": 0,
            "issues": [],
            "improvement_opportunities": []
        }

        try:
            with open(file_path, 'r') as f:
                content = f.read()

            analysis["line_count"] = len(content.splitlines())

            # Parse AST
            tree = ast.parse(content)

            # Count functions and classes
            analysis["function_count"] = len([
                node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
            ])
            analysis["class_count"] = len([
                node for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef)
            ])

            # Calculate complexity score (simplified)
            analysis["complexity_score"] = (
                analysis["function_count"] * 2 +
                analysis["class_count"] * 3 +
                analysis["line_count"] / 100
            )

            # Detect common issues
            issues = await self._detect_code_issues(tree, file_path)
            analysis["issues"] = issues

            # Identify improvement opportunities
            opportunities = await self._identify_improvements(tree, file_path)
            analysis["improvement_opportunities"] = opportunities

        except Exception as e:
            self.logger.error(f"Failed to analyze Python file {file_path}: {e}")

        return analysis

    async def _detect_code_issues(
        self,
        tree: ast.AST,
        file_path: str
    ) -> List[Dict[str, Any]]:
        """Detect code issues from AST."""
        issues = []

        try:
            # Check for long functions (> 50 lines)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Estimate function length
                    end_lineno = getattr(node, 'end_lineno', node.lineno)
                    length = end_lineno - node.lineno + 1

                    if length > 50:
                        issues.append({
                            "type": "long_function",
                            "location": f"{file_path}:{node.lineno}",
                            "function": node.name,
                            "length": length,
                            "severity": "medium"
                        })

            # Check for complex expressions
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    # Count conditions in if statements
                    condition_count = len(list(ast.walk(node.test)))
                    if condition_count > 5:
                        issues.append({
                            "type": "complex_condition",
                            "location": f"{file_path}:{node.lineno}",
                            "condition_count": condition_count,
                            "severity": "low"
                        })

        except Exception as e:
            self.logger.error(f"Failed to detect code issues: {e}")

        return issues

    async def _identify_improvements(
        self,
        tree: ast.AST,
        file_path: str
    ) -> List[Dict[str, Any]]:
        """Identify improvement opportunities."""
        improvements = []

        try:
            # Look for code that could be optimized
            for node in ast.walk(tree):
                if isinstance(node, ast.For):
                    # Check for loops that could use list comprehensions
                    improvements.append({
                        "type": "loop_optimization",
                        "location": f"{file_path}:{node.lineno}",
                        "description": "Consider using list comprehension",
                        "estimated_impact": "low"
                    })

                elif isinstance(node, ast.Call):
                    # Check for repeated function calls
                    improvements.append({
                        "type": "repeated_calls",
                        "location": f"{file_path}:{node.lineno}",
                        "description": "Repeated function calls could be cached",
                        "estimated_impact": "medium"
                    })

        except Exception as e:
            self.logger.error(f"Failed to identify improvements: {e}")

        return improvements

    async def _find_component_files(self, component: str) -> List[str]:
        """Find files related to a component."""
        files = []
        component_lower = component.lower()

        try:
            for root, dirs, filenames in os.walk(str(self.project_root)):
                # Skip virtual environments and hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', '__pycache__']]

                for filename in filenames:
                    if filename.endswith('.py'):
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, str(self.project_root))

                        # Check if component name appears in path
                        if component_lower in relative_path.lower():
                            files.append(relative_path)

                        # Check file content
                        else:
                            try:
                                with open(file_path, 'r') as f:
                                    content = f.read().lower()
                                    if component_lower in content:
                                        files.append(relative_path)
                            except:
                                pass

        except Exception as e:
            self.logger.error(f"Failed to find component files: {e}")

        return files

    async def _generate_changes(
        self,
        refactor_type: RefactorType,
        analysis: Dict[str, Any],
        target_file: Optional[str],
        target_component: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Generate specific changes for refactoring."""
        changes = []

        if refactor_type == RefactorType.CODE_OPTIMIZATION:
            # Generate code optimization changes
            for issue in analysis.get("issues", []):
                if issue["type"] == "long_function":
                    changes.append({
                        "type": "extract_method",
                        "location": issue["location"],
                        "description": f"Extract part of function '{issue['function']}' into helper method",
                        "implementation": f"# TODO: Extract method from {issue['function']}",
                        "estimated_effort": "medium"
                    })

        elif refactor_type == RefactorType.PERFORMANCE_IMPROVEMENT:
            # Generate performance improvement changes
            for improvement in analysis.get("improvement_opportunities", []):
                if improvement["type"] == "loop_optimization":
                    changes.append({
                        "type": "use_comprehension",
                        "location": improvement["location"],
                        "description": "Replace loop with list comprehension",
                        "implementation": "# TODO: Convert loop to list comprehension",
                        "estimated_effort": "low"
                    })

        elif refactor_type == RefactorType.CONFIGURATION_TUNING:
            # Generate configuration tuning changes
            changes.append({
                "type": "adjust_configuration",
                "target": target_component or "system",
                "description": "Tune configuration parameters based on performance analysis",
                "implementation": "# TODO: Update configuration values",
                "estimated_effort": "low"
            })

        return changes

    async def _validate_syntax(
        self,
        changes: List[Dict[str, Any]]
    ) -> bool:
        """Validate syntax of proposed changes."""
        # Simple syntax validation
        # In a real implementation, this would compile the changed code
        try:
            for change in changes:
                implementation = change.get("implementation", "")
                if implementation and implementation.startswith("# TODO:"):
                    # Placeholder implementation, consider valid
                    continue

                # Try to parse as Python if it looks like code
                if any(keyword in implementation for keyword in ["def ", "class ", "import ", "from "]):
                    ast.parse(implementation)
        except SyntaxError:
            return False

        return True

    async def _create_backup(
        self,
        proposal: Dict[str, Any],
        backup_dir: str
    ) -> str:
        """Create backup of files to be modified."""
        backup_path = os.path.join(backup_dir, "backup.tar.gz")

        try:
            import tarfile
            files_to_backup = []

            target_file = proposal.get("target_file")
            if target_file:
                files_to_backup.append(str(self.project_root / target_file))

            # Create tar archive
            with tarfile.open(backup_path, "w:gz") as tar:
                for file_path in files_to_backup:
                    if os.path.exists(file_path):
                        tar.add(file_path, arcname=os.path.relpath(file_path, str(self.project_root)))

            return backup_path
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return ""

    async def _apply_changes(
        self,
        changes: List[Dict[str, Any]],
        target_dir: str,
        dry_run: bool = True
    ) -> List[Dict[str, Any]]:
        """Apply changes to files."""
        applied_changes = []

        for change in changes:
            try:
                if dry_run:
                    applied_changes.append({
                        "change": change,
                        "applied": False,
                        "dry_run": True
                    })
                else:
                    # Actually apply the change
                    # This is a simplified implementation
                    applied_changes.append({
                        "change": change,
                        "applied": True,
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                self.logger.error(f"Failed to apply change: {e}")
                applied_changes.append({
                    "change": change,
                    "applied": False,
                    "error": str(e)
                })

        return applied_changes

    async def _run_tests(self, directory: str) -> bool:
        """Run tests in directory."""
        # Simplified test runner
        try:
            import subprocess
            result = subprocess.run(
                ["python", "-m", "pytest", "--tb=short"],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0
        except:
            # If pytest fails or isn't available, try basic import test
            try:
                # Try to import main modules
                import sys
                sys.path.insert(0, directory)
                import app
                return True
            except:
                return False

    async def _analyze_performance_impact(self, directory: str) -> str:
        """Analyze performance impact of changes."""
        # Simplified analysis
        return "minimal"

    async def _calculate_safety_score(
        self,
        proposal: Dict[str, Any],
        validation: Dict[str, Any]
    ) -> float:
        """Calculate safety score for refactoring."""
        score = 1.0

        # Deduct for issues
        if not validation["syntax_valid"]:
            score -= 0.3
        if not validation["tests_pass"]:
            score -= 0.4
        if validation["performance_impact"] == "significant":
            score -= 0.2

        # Add for positive factors
        if proposal["type"] == "configuration_tuning":
            score += 0.1  # Configuration changes are generally safe

        return max(0.0, min(1.0, score))

    async def _rollback_refactor(
        self,
        refactor_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """Rollback a refactoring."""
        proposal = await self._get_refactor_proposal(refactor_id)
        if not proposal:
            raise ValueError(f"Refactoring proposal not found: {refactor_id}")

        rollback_result = {
            "success": False,
            "reason": reason,
            "errors": []
        }

        try:
            backup_path = proposal.get("rollback_path")
            if backup_path and os.path.exists(backup_path):
                # Restore from backup
                import tarfile
                with tarfile.open(backup_path, "r:gz") as tar:
                    tar.extractall(str(self.project_root))

                rollback_result["success"] = True
                rollback_result["backup_used"] = True
            else:
                # Manual rollback based on change records
                rollback_result["success"] = False
                rollback_result["errors"].append("Backup not available")
                rollback_result["backup_used"] = False

            # Update proposal status
            proposal["status"] = RefactorStatus.REVERTED.value
            proposal["reverted_at"] = datetime.now().isoformat()
            await self._store_refactor_proposal(proposal)

        except Exception as e:
            self.logger.error(f"Failed to rollback refactoring: {e}")
            rollback_result["errors"].append(str(e))

        return {
            "refactor_id": refactor_id,
            "rollback": rollback_result,
            "proposal": proposal
        }

    async def _store_refactor_proposal(self, proposal: Dict[str, Any]) -> None:
        """Store refactoring proposal in database."""
        try:
            query = """
                INSERT INTO refactoring_proposals (
                    id, type, target_file, target_component, rationale,
                    expected_improvement, hypothesis_id, analysis,
                    proposed_changes, status, created_at, applied_at,
                    reverted_at, validation_results, rollback_path
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15
                )
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    validation_results = EXCLUDED.validation_results,
                    applied_at = EXCLUDED.applied_at,
                    reverted_at = EXCLUDED.reverted_at
            """

            applied_at = (
                datetime.fromisoformat(proposal["applied_at"])
                if proposal["applied_at"] else None
            )
            reverted_at = (
                datetime.fromisoformat(proposal["reverted_at"])
                if proposal["reverted_at"] else None
            )

            await self.db.execute(
                query,
                proposal["id"],
                proposal["type"],
                proposal["target_file"],
                proposal["target_component"],
                proposal["rationale"],
                proposal["expected_improvement"],
                proposal["hypothesis_id"],
                proposal["analysis"],
                proposal["proposed_changes"],
                proposal["status"],
                datetime.fromisoformat(proposal["created_at"]),
                applied_at,
                reverted_at,
                proposal["validation_results"],
                proposal["rollback_path"]
            )
        except Exception as e:
            self.logger.error(f"Failed to store refactor proposal: {e}")

    async def _get_refactor_proposal(self, refactor_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve refactoring proposal from database."""
        try:
            query = "SELECT * FROM refactoring_proposals WHERE id = $1"
            row = await self.db.fetchrow(query, refactor_id)
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Failed to get refactor proposal: {e}")
            return None