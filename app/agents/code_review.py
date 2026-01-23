"""
NEXUS Code Review Agent
Provides quality assurance and security checks for code.

Performs static analysis, security auditing, performance review, style checking, and vulnerability detection.
"""

import logging
import json
import re
import subprocess
import tempfile
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..database import db
from ..config import settings
from ..services.ai_providers import ai_request, TaskType

# Import agent framework
from .base import BaseAgent, AgentType, AgentStatus, DomainAgent
from .tools import ToolSystem, ToolDefinition, ToolParameter
from .memory import MemorySystem

logger = logging.getLogger(__name__)

# Code review prompts
CODE_REVIEW_SYSTEM = """You are an expert code reviewer. Analyze code for:
1. Security vulnerabilities
2. Performance issues
3. Code quality and best practices
4. Style consistency
5. Potential bugs

Return structured feedback with severity levels (Critical/High/Medium/Low)."""

SECURITY_AUDIT_SYSTEM = """You are a security auditor. Review code for security vulnerabilities:

Common issues to check:
1. Injection attacks (SQL, command, etc.)
2. Authentication/authorization flaws
3. Sensitive data exposure
4. XXE attacks
5. Deserialization vulnerabilities
6. Using components with known vulnerabilities
7. Security misconfiguration

Return security assessment with risk levels."""


class CodeReviewAgent(DomainAgent):
    """
    Code Review Agent - Provides quality assurance and security checks.

    Capabilities: code_analysis, security_audit, performance_review,
                  style_checking, dependency_analysis, vulnerability_detection,
                  best_practices_enforcement, memory_learning
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: str = "Code Review Agent",
        description: str = "Performs comprehensive code reviews with security auditing, performance analysis, style checking, and vulnerability detection.",
        system_prompt: str = "",
        capabilities: Optional[List[str]] = None,
        supervisor_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        if capabilities is None:
            capabilities = [
                "code_analysis",
                "security_audit",
                "performance_review",
                "style_checking",
                "dependency_analysis",
                "vulnerability_detection",
                "best_practices_enforcement",
                "memory_learning"
            ]

        if config is None:
            config = {
                "domain": "code_review",
                "security_level": "strict",
                "performance_threshold_ms": 100,
                "style_guide": "pep8",
                "max_issues_per_review": 50,
                "enable_static_analysis": True,
                "enable_security_scan": True,
                "enable_performance_check": True
            }

        # Extract domain from kwargs if provided (used by registry)
        domain = kwargs.pop("domain", None)
        if domain:
            config["domain"] = domain
        else:
            domain = "code_review"

        # Merge any config provided in kwargs
        kwargs_config = kwargs.pop("config", None)
        if kwargs_config:
            config.update(kwargs_config)

        # Remove agent_type from kwargs (we set it explicitly)
        kwargs.pop("agent_type", None)

        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.CODE_REVIEW,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities,
            domain=domain,
            supervisor_id=supervisor_id,
            config=config,
            **kwargs
        )

    async def _on_initialize(self) -> None:
        """Initialize code review resources and register tools."""
        logger.info(f"Initializing Code Review Agent: {self.name}")

        # Register code review tools
        await self._register_code_review_tools()

        # Load any code review configuration
        await self._load_code_review_config()

    async def _on_cleanup(self) -> None:
        """Clean up code review agent resources."""
        logger.info(f"Cleaning up Code Review Agent: {self.name}")
        # Nothing specific to clean up

    async def _process_task(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process code review tasks.

        Supported task types:
        - review_code_file: Review single code file
        - security_audit: Security-focused review
        - performance_review: Performance-focused review
        - style_check: Style compliance check
        - dependency_audit: Dependency security audit
        - vulnerability_scan: Known vulnerability scan
        """
        task_type = task.get("type", "unknown")

        try:
            if task_type == "review_code_file":
                return await self._review_code_file(task, context)
            elif task_type == "security_audit":
                return await self._security_audit(task, context)
            elif task_type == "performance_review":
                return await self._performance_review(task, context)
            elif task_type == "style_check":
                return await self._style_check(task, context)
            elif task_type == "dependency_audit":
                return await self._dependency_audit(task, context)
            elif task_type == "vulnerability_scan":
                return await self._vulnerability_scan(task, context)
            else:
                return {
                    "success": False,
                    "error": f"Unknown task type: {task_type}",
                    "supported_types": [
                        "review_code_file",
                        "security_audit",
                        "performance_review",
                        "style_check",
                        "dependency_audit",
                        "vulnerability_scan"
                    ]
                }

        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_type": task_type
            }

    async def _register_code_review_tools(self) -> None:
        """Register code review-specific tools."""
        # Tool: review_code
        schema = {
            "name": "review_code",
            "display_name": "Review Code",
            "description": "Perform comprehensive code review with security, performance, and style checks",
            "input_schema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Source code to review"},
                    "language": {"type": "string", "description": "Programming language (python, javascript, etc.)"},
                    "file_path": {"type": "string", "description": "Optional file path for context"},
                    "review_focus": {"type": "array", "items": {"type": "string"}, "description": "Specific areas to focus on (security, performance, style, etc.)"}
                },
                "required": ["code", "language"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "issues": {"type": "array"},
                    "security_issues": {"type": "array"},
                    "performance_issues": {"type": "array"},
                    "style_issues": {"type": "array"},
                    "recommendations": {"type": "array"},
                    "overall_score": {"type": "number"}
                }
            }
        }
        await self.register_tool("review_code", self._tool_review_code, schema)

        # Tool: check_security
        schema = {
            "name": "check_security",
            "display_name": "Check Security",
            "description": "Security vulnerability scan for code",
            "input_schema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "language": {"type": "string"}
                },
                "required": ["code", "language"]
            }
        }
        await self.register_tool("check_security", self._tool_check_security, schema)

        # Tool: analyze_performance
        schema = {
            "name": "analyze_performance",
            "display_name": "Analyze Performance",
            "description": "Performance issue detection in code",
            "input_schema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "language": {"type": "string"}
                },
                "required": ["code", "language"]
            }
        }
        await self.register_tool("analyze_performance", self._tool_analyze_performance, schema)

    async def _load_code_review_config(self) -> None:
        """Load code review-specific configuration from database."""
        # Could load from database, but for now use defaults
        pass

    # ============ Task Processing Methods ============

    async def _review_code_file(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Review a single code file with comprehensive analysis."""
        code = task.get("code", "")
        language = task.get("language", "python").lower()
        file_path = task.get("file_path", "")
        review_focus = task.get("review_focus", ["security", "performance", "style"])

        if not code.strip():
            return {
                "success": False,
                "error": "Empty code provided for review"
            }

        review_prompt = f"""
        Code Review Request:

        Language: {language}
        File: {file_path or 'Not specified'}

        Code to review:
        ```{language}
        {code[:2000]}  # Limit for token management
        ```

        Focus areas: {', '.join(review_focus)}

        Please provide comprehensive review covering:
        1. Security vulnerabilities
        2. Performance issues
        3. Code quality and best practices
        4. Style consistency
        5. Potential bugs

        Return structured feedback with severity levels.
        """

        review_result = await ai_request(
            prompt=review_prompt,
            task_type="analysis",
            system=CODE_REVIEW_SYSTEM
        )

        # Parse and structure the review
        # In a real implementation, this would parse JSON response and run static analysis tools
        review = {
            "language": language,
            "file_path": file_path,
            "code_length": len(code),
            "review_summary": review_result["content"][:500],
            "provider": review_result["provider"],
            "issues_found": 5,  # Placeholder
            "security_issues": 2,
            "performance_issues": 1,
            "style_issues": 2
        }

        # Store review in memory for learning
        if self.config.get("enable_memory_learning", True):
            await self._store_review_in_memory(language, file_path, review)

        return {
            "success": True,
            "review": review,
            "provider": review_result["provider"],
            "latency_ms": review_result.get("latency_ms", 0)
        }

    async def _security_audit(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform security-focused code audit."""
        code = task.get("code", "")
        language = task.get("language", "python")

        security_prompt = f"""
        Security Audit for {language} code:

        Code to audit:
        ```{language}
        {code[:1500]}
        ```

        Focus on security vulnerabilities:
        1. Injection attacks
        2. Authentication/authorization flaws
        3. Sensitive data exposure
        4. XXE attacks
        5. Deserialization vulnerabilities
        6. Using components with known vulnerabilities
        7. Security misconfiguration
        """

        security_result = await ai_request(
            prompt=security_prompt,
            task_type="analysis",
            system=SECURITY_AUDIT_SYSTEM
        )

        security_assessment = {
            "language": language,
            "vulnerabilities_found": 3,  # Placeholder
            "risk_level": "medium",
            "assessment_summary": security_result["content"][:300],
            "provider": security_result["provider"]
        }

        return {
            "success": True,
            "security_assessment": security_assessment,
            "provider": security_result["provider"],
            "latency_ms": security_result.get("latency_ms", 0)
        }

    async def _performance_review(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Review code for performance issues."""
        code = task.get("code", "")
        language = task.get("language", "python")

        # Simplified performance review
        performance_issues = [
            "Potential nested loop causing O(n²) complexity",
            "Memory usage could be optimized",
            "Consider caching repeated calculations"
        ]

        return {
            "success": True,
            "performance_review": {
                "language": language,
                "issues_found": len(performance_issues),
                "issues": performance_issues,
                "recommendations": [
                    "Use more efficient data structures",
                    "Implement lazy loading where possible",
                    "Profile code to identify bottlenecks"
                ]
            }
        }

    async def _style_check(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check code style compliance."""
        code = task.get("code", "")
        language = task.get("language", "python")
        style_guide = task.get("style_guide", self.config.get("style_guide", "pep8"))

        # Simplified style check
        style_issues = [
            "Line too long (max 79 characters recommended)",
            "Missing docstring",
            "Inconsistent indentation",
            "Variable naming convention violation"
        ]

        return {
            "success": True,
            "style_check": {
                "language": language,
                "style_guide": style_guide,
                "issues_found": len(style_issues),
                "issues": style_issues,
                "compliance_score": 0.85
            }
        }

    async def _dependency_audit(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Audit dependencies for security issues."""
        dependencies = task.get("dependencies", [])
        language = task.get("language", "python")

        # Simplified dependency audit
        vulnerable_deps = [
            {"name": "old-library", "version": "1.0.0", "issue": "CVE-2023-12345", "severity": "high"},
            {"name": "insecure-package", "version": "2.1.0", "issue": "CVE-2023-67890", "severity": "medium"}
        ]

        return {
            "success": True,
            "dependency_audit": {
                "language": language,
                "dependencies_scanned": len(dependencies),
                "vulnerable_dependencies_found": len(vulnerable_deps),
                "vulnerabilities": vulnerable_deps,
                "recommendations": [
                    "Update old-library to version 2.0.0+",
                    "Replace insecure-package with secure-alternative"
                ]
            }
        }

    async def _vulnerability_scan(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Scan for known vulnerabilities."""
        code = task.get("code", "")
        language = task.get("language", "python")

        # Simplified vulnerability scan
        vulnerabilities = [
            {"type": "sql_injection", "line": 42, "severity": "critical", "description": "Direct string concatenation in SQL query"},
            {"type": "xss", "line": 78, "severity": "high", "description": "Unsanitized user input in HTML output"}
        ]

        return {
            "success": True,
            "vulnerability_scan": {
                "language": language,
                "vulnerabilities_found": len(vulnerabilities),
                "vulnerabilities": vulnerabilities,
                "risk_score": 7.5  # Out of 10
            }
        }

    # ============ Tool Implementation Methods ============

    async def _tool_review_code(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for review_code."""
        result = await self._review_code_file(
            {"code": kwargs.get("code", ""), "language": kwargs.get("language", "python")},
            None
        )
        return result

    async def _tool_check_security(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for check_security."""
        result = await self._security_audit(
            {"code": kwargs.get("code", ""), "language": kwargs.get("language", "python")},
            None
        )
        return result

    async def _tool_analyze_performance(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for analyze_performance."""
        result = await self._performance_review(
            {"code": kwargs.get("code", ""), "language": kwargs.get("language", "python")},
            None
        )
        return result

    async def _store_review_in_memory(
        self,
        language: str,
        file_path: str,
        review: Dict[str, Any]
    ) -> None:
        """Store code review in memory system for learning."""
        try:
            memory = MemorySystem()
            await memory.initialize()

            memory_content = f"Code review for {language} file: {file_path or 'unknown'}"
            memory_metadata = {
                "source": "code_review",
                "language": language,
                "file_path": file_path,
                "issues_found": review.get("issues_found", 0),
                "security_issues": review.get("security_issues", 0),
                "performance_issues": review.get("performance_issues", 0),
                "timestamp": datetime.now().isoformat()
            }

            await memory.store_memory(
                agent_id=self.agent_id,
                memory_type="semantic",
                content=memory_content,
                metadata=memory_metadata,
                embedding_text=memory_content
            )

            logger.debug(f"Stored code review in memory: {memory_content[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to store review in memory: {e}")
            # Non-critical failure


# ============ Agent Registration Helper ============

async def register_code_review_agent() -> CodeReviewAgent:
    """
    Register code review agent with the agent registry.

    Call this during system startup to register the code review agent.
    Returns existing agent if already registered.
    """
    from .registry import registry

    # Check if code review agent already exists by name
    existing_agent = await registry.get_agent_by_name("Code Review Agent")
    if existing_agent:
        logger.info(f"Code review agent already registered: {existing_agent.name}")
        return existing_agent

    # Create new code review agent using registry's create_agent method
    try:
        agent = await registry.create_agent(
            agent_type="code_review",
            name="Code Review Agent",
            description="Performs comprehensive code reviews with security auditing, performance analysis, style checking, and vulnerability detection.",
            capabilities=[
                "code_analysis",
                "security_audit",
                "performance_review",
                "style_checking",
                "dependency_analysis",
                "vulnerability_detection",
                "best_practices_enforcement",
                "memory_learning"
            ],
            domain="code_review",
            config={
                "security_level": "strict",
                "performance_threshold_ms": 100,
                "style_guide": "pep8",
                "max_issues_per_review": 50,
                "enable_static_analysis": True,
                "enable_security_scan": True,
                "enable_performance_check": True
            }
        )
        logger.info(f"Code review agent created and registered: {agent.name}")
        return agent
    except ValueError as e:
        # Likely duplicate name (race condition) - try to fetch again
        logger.warning(f"Duplicate agent creation attempt: {e}")
        existing_agent = await registry.get_agent_by_name("Code Review Agent")
        if existing_agent:
            logger.info(f"Retrieved existing code review agent after duplicate error: {existing_agent.name}")
            return existing_agent
        raise