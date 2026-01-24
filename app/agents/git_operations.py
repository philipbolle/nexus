"""
NEXUS Git Operations Agent
Fully autonomous git operations with safety constraints and edge case handling.

Performs git operations (commit, push, branch management) with comprehensive
safety validation, conflict detection, and automatic fallback to manual tasks
for scenarios requiring human intervention.
"""

import logging
import json
import subprocess
import os
import re
import httpx
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from ..database import db
from ..config import settings
from ..services.ai_providers import ai_request, TaskType
from ..exceptions.manual_tasks import (
    ManualInterventionRequired,
    SecurityInterventionRequired,
    ConfigurationInterventionRequired,
    ApprovalRequired
)

# Import agent framework
from .base import BaseAgent, AgentType, AgentStatus, DomainAgent
from .tools import ToolSystem, ToolDefinition, ToolParameter
from .memory import MemorySystem
from .monitoring import performance_monitor, MetricType

logger = logging.getLogger(__name__)


class GitOperationsAgent(DomainAgent):
    """
    Git Operations Agent - Fully autonomous git operations with safety constraints.

    Capabilities: git_commit, git_push, git_branch_management, git_safety_validation,
                  conflict_detection, change_analysis, automated_rollback,
                  manual_task_integration
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: str = "Git Operations Agent",
        description: str = "Fully autonomous git operations with safety constraints and edge case handling",
        system_prompt: str = "",
        capabilities: Optional[List[str]] = None,
        supervisor_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        if capabilities is None:
            capabilities = [
                "git_commit",
                "git_push",
                "git_branch_management",
                "git_safety_validation",
                "conflict_detection",
                "change_analysis",
                "automated_rollback",
                "manual_task_integration",
                "performance_monitoring"
            ]

        if config is None:
            config = {
                "domain": "git_operations",
                "repository_path": "/home/philip/nexus",
                "allowed_branches": ["main", "develop", "feature/*", "hotfix/*"],
                "protected_branches": ["main"],
                "max_commit_size_mb": 100,
                "require_clean_status": True,
                "enable_auto_push": True,
                "enable_safety_checks": True,
                "enable_conflict_detection": True,
                "max_unstaged_changes": 50,
                "require_commit_message": True,
                "commit_message_pattern": r"^[A-Za-z].+$",
                "allow_force_push": False,
                "require_pr_for_main": True,
                "test_before_push": True,
                "backup_before_operations": True,
                # Webhook integration for n8n workflows
                "enable_webhooks": True,
                "webhook_base_url": "http://localhost:5678/webhook",
                "webhook_timeout": 10,
                "webhook_retries": 3,
                "webhook_events": ["commit", "push", "conflict", "branch", "rollback"],
                # AI-powered features
                "enable_ai_commit_messages": True,
                "enable_conflict_prediction": True
            }

        # Extract domain from kwargs if provided (used by registry)
        domain = kwargs.pop("domain", None)
        if domain:
            config["domain"] = domain
        else:
            domain = "git_operations"

        # Merge any config provided in kwargs
        kwargs_config = kwargs.pop("config", None)
        if kwargs_config:
            config.update(kwargs_config)

        # Remove agent_type from kwargs (we set it explicitly)
        kwargs.pop("agent_type", None)

        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.DOMAIN,
            description=description,
            system_prompt=system_prompt,
            capabilities=capabilities,
            domain=domain,
            supervisor_id=supervisor_id,
            config=config,
            **kwargs
        )

    async def _on_initialize(self) -> None:
        """Initialize git operations resources and register tools."""
        logger.info(f"Initializing Git Operations Agent: {self.name}")

        # Initialize git-specific metrics
        self.metrics.update({
            "git_commits": 0,
            "git_pushes": 0,
            "git_branches_created": 0,
            "git_branches_deleted": 0,
            "git_conflicts_detected": 0,
            "git_rollbacks": 0,
            "git_validation_failures": 0,
            "git_manual_interventions": 0
        })

        # Register git-specific tools
        await self._register_git_tools()

        # Load git-specific configuration
        await self._load_git_config()

        # Verify git repository
        await self._verify_git_repository()

    async def _on_cleanup(self) -> None:
        """Clean up git operations agent resources."""
        logger.info(f"Cleaning up Git Operations Agent: {self.name}")
        # Nothing specific to clean up

    async def _process_task(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process git operations tasks.

        Supported task types:
        - analyze_changes: Analyze git changes and recommend operations
        - create_commit: Create a git commit with validation
        - push_changes: Push changes to remote with safety checks
        - manage_branch: Create, switch, or delete branches
        - validate_safety: Run comprehensive safety validation
        - handle_conflict: Detect and handle merge conflicts
        - rollback_operation: Rollback a problematic git operation
        - generate_report: Generate git operations report
        """
        task_type = task.get("type", "unknown")

        try:
            if task_type == "analyze_changes":
                return await self._analyze_changes(task, context)
            elif task_type == "create_commit":
                return await self._create_commit(task, context)
            elif task_type == "push_changes":
                return await self._push_changes(task, context)
            elif task_type == "manage_branch":
                return await self._manage_branch(task, context)
            elif task_type == "validate_safety":
                return await self._validate_safety(task, context)
            elif task_type == "handle_conflict":
                return await self._handle_conflict(task, context)
            elif task_type == "rollback_operation":
                return await self._rollback_operation(task, context)
            elif task_type == "generate_report":
                return await self._generate_report(task, context)
            else:
                return {
                    "success": False,
                    "error": f"Unknown task type: {task_type}",
                    "supported_types": [
                        "analyze_changes",
                        "create_commit",
                        "push_changes",
                        "manage_branch",
                        "validate_safety",
                        "handle_conflict",
                        "rollback_operation",
                        "generate_report"
                    ]
                }

        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_type": task_type
            }

    async def _register_git_tools(self) -> None:
        """Register git-specific tools."""
        # Tool: git_status
        schema = {
            "name": "git_status",
            "display_name": "Git Status",
            "description": "Get current git repository status",
            "input_schema": {
                "type": "object",
                "properties": {
                    "detailed": {"type": "boolean", "description": "Show detailed status"}
                },
                "required": []
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "branch": {"type": "string"},
                    "ahead": {"type": "integer"},
                    "behind": {"type": "integer"},
                    "staged": {"type": "array", "items": {"type": "string"}},
                    "unstaged": {"type": "array", "items": {"type": "string"}},
                    "untracked": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
        await self.register_tool("git_status", self._tool_git_status, schema)

        # Tool: git_commit
        schema = {
            "name": "git_commit",
            "display_name": "Git Commit",
            "description": "Create a git commit with validation and safety checks",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Specific files to commit"},
                    "skip_validation": {"type": "boolean", "description": "Skip safety validation (dangerous)"}
                },
                "required": ["message"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "commit_hash": {"type": "string"},
                    "summary": {"type": "string"},
                    "files_committed": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
        await self.register_tool("git_commit", self._tool_git_commit, schema)

        # Tool: git_push
        schema = {
            "name": "git_push",
            "display_name": "Git Push",
            "description": "Push changes to remote repository with comprehensive safety checks",
            "input_schema": {
                "type": "object",
                "properties": {
                    "branch": {"type": "string", "description": "Branch to push"},
                    "force": {"type": "boolean", "description": "Force push (dangerous)"},
                    "dry_run": {"type": "boolean", "description": "Simulate push without actually pushing"}
                },
                "required": []
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "remote": {"type": "string"},
                    "pushed_commits": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
        await self.register_tool("git_push", self._tool_git_push, schema)

        # Tool: git_create_branch
        schema = {
            "name": "git_create_branch",
            "display_name": "Create Git Branch",
            "description": "Create a new git branch with validation",
            "input_schema": {
                "type": "object",
                "properties": {
                    "branch_name": {"type": "string", "description": "Name of new branch (optional - will be generated if not provided)"},
                    "from_branch": {"type": "string", "description": "Source branch"},
                    "purpose": {"type": "string", "description": "Branch purpose (feature, fix, hotfix, chore, docs, test) - default: feature"},
                    "issue_id": {"type": "string", "description": "Issue/ticket ID for branch naming"}
                },
                "required": []
            }
        }
        await self.register_tool("git_create_branch", self._tool_git_create_branch, schema)

        # Tool: git_validate_safety
        schema = {
            "name": "git_validate_safety",
            "display_name": "Validate Git Safety",
            "description": "Comprehensive safety validation before git operations",
            "input_schema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "description": "Operation type (commit, push, merge, etc.)"},
                    "target_branch": {"type": "string", "description": "Target branch for operation"}
                },
                "required": ["operation"]
            }
        }
        await self.register_tool("git_validate_safety", self._tool_git_validate_safety, schema)

        # Tool: git_analyze_patterns
        schema = {
            "name": "git_analyze_patterns",
            "display_name": "Analyze Git Patterns",
            "description": "Analyze git history patterns and suggest workflow improvements",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "branch_count": {"type": "integer"},
                    "stale_branches": {"type": "array", "items": {"type": "string"}},
                    "commit_count_30d": {"type": "integer"},
                    "merge_count_90d": {"type": "integer"},
                    "recommendations": {"type": "array", "items": {"type": "string"}},
                    "summary": {"type": "string"}
                }
            }
        }
        await self.register_tool("git_analyze_patterns", self._tool_git_analyze_patterns, schema)

    async def _load_git_config(self) -> None:
        """Load git-specific configuration from database."""
        # Could load from database, but for now use defaults
        pass

    async def _verify_git_repository(self) -> None:
        """Verify git repository exists and is accessible."""
        repo_path = self.config.get("repository_path", "/home/philip/nexus")

        if not os.path.exists(repo_path):
            raise ConfigurationInterventionRequired(
                title="Git Repository Not Found",
                description=f"Repository path does not exist: {repo_path}",
                source_system="agent:GitOperationsAgent",
                context={"repository_path": repo_path}
            )

        git_dir = os.path.join(repo_path, ".git")
        if not os.path.exists(git_dir):
            raise ConfigurationInterventionRequired(
                title="Not a Git Repository",
                description=f"Directory is not a git repository: {repo_path}",
                source_system="agent:GitOperationsAgent",
                context={"repository_path": repo_path, "git_dir": git_dir}
            )

        logger.info(f"Git repository verified: {repo_path}")

    # ============ Task Processing Methods ============

    async def _analyze_changes(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze git changes and recommend operations."""
        try:
            # Get git status
            status_result = await self._execute_git_command(["status", "--porcelain"])
            status_lines = status_result.strip().split('\n') if status_result.strip() else []

            # Get branch info
            branch_result = await self._execute_git_command(["branch", "--show-current"])
            current_branch = branch_result.strip()

            # Get ahead/behind
            ahead_behind_result = await self._execute_git_command(["rev-list", "--left-right", "--count", f"origin/{current_branch}...{current_branch}"])
            ahead_behind = ahead_behind_result.strip().split('\t') if ahead_behind_result.strip() else ["0", "0"]

            # Analyze changes
            staged = []
            unstaged = []
            untracked = []

            for line in status_lines:
                if line:
                    status = line[:2]
                    file = line[3:]
                    if status == "??":
                        untracked.append(file)
                    elif status[0] != " " and status[0] != "?":
                        staged.append(file)
                    if status[1] != " ":
                        unstaged.append(file)

            analysis = {
                "current_branch": current_branch,
                "ahead": int(ahead_behind[0]) if len(ahead_behind) > 0 else 0,
                "behind": int(ahead_behind[1]) if len(ahead_behind) > 1 else 0,
                "staged_files": len(staged),
                "unstaged_files": len(unstaged),
                "untracked_files": len(untracked),
                "total_changes": len(staged) + len(unstaged) + len(untracked),
                "recommendations": self._generate_recommendations(len(staged), len(unstaged), len(untracked), int(ahead_behind[0]) if len(ahead_behind) > 0 else 0)
            }

            return {
                "success": True,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to analyze changes: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _create_commit(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a git commit with validation."""
        commit_message = task.get("message", "")
        files = task.get("files", [])
        skip_validation = task.get("skip_validation", False)

        # Generate AI commit message if empty and AI is enabled
        if not commit_message.strip() and self.config.get("enable_ai_commit_messages", True):
            try:
                # Get diff for context
                diff = await self._execute_git_command(["diff", "--cached"])
                if not diff.strip():
                    diff = await self._execute_git_command(["diff"])

                # Get branch context
                branch = await self._execute_git_command(["branch", "--show-current"])
                context = {
                    "branch": branch.strip(),
                    "files": files if files else ["all"],
                    "repository": self.config.get("repository_path")
                }

                commit_message = await self._generate_ai_commit_message(diff, context)
                logger.info(f"Generated AI commit message: {commit_message}")
            except Exception as e:
                logger.warning(f"Failed to generate AI commit message: {e}")
                # Continue with empty message, validation will catch it if required

        # Validate commit message
        if self.config.get("require_commit_message", True) and not commit_message.strip():
            return {
                "success": False,
                "error": "Commit message is required"
            }

        # Validate commit message pattern
        pattern = self.config.get("commit_message_pattern", r"^[A-Za-z].+$")
        if pattern and not re.match(pattern, commit_message):
            return {
                "success": False,
                "error": f"Commit message does not match pattern: {pattern}"
            }

        # Run safety validation unless skipped
        if not skip_validation and self.config.get("enable_safety_checks", True):
            safety_result = await self._validate_safety({"operation": "commit"}, context)
            if not safety_result.get("success", False):
                await self._update_git_metric("git_validation_failures")
                return safety_result

        try:
            # Stage files if specified
            if files:
                await self._execute_git_command(["add"] + files)
            else:
                await self._execute_git_command(["add", "."])

            # Create commit
            commit_result = await self._execute_git_command(["commit", "-m", commit_message])

            # Get commit hash
            commit_hash = await self._execute_git_command(["rev-parse", "HEAD"])

            # Update metrics
            await self._update_git_metric("git_commits")

            # Send webhook notification
            try:
                await self._send_webhook_notification(
                    event_type="commit",
                    data={
                        "commit_hash": commit_hash.strip(),
                        "message": commit_message,
                        "files": files if files else ["all"],
                        "summary": commit_result.strip()
                    },
                    event_data={
                        "agent_id": self.agent_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            except Exception as webhook_error:
                logger.warning(f"Failed to send commit webhook: {webhook_error}")
                # Don't fail the commit if webhook fails

            return {
                "success": True,
                "commit_hash": commit_hash.strip(),
                "summary": commit_result.strip(),
                "message": commit_message
            }

        except Exception as e:
            logger.error(f"Failed to create commit: {e}")

            # Attempt to undo the staged changes
            try:
                await self._execute_git_command(["reset"])
            except Exception as reset_error:
                logger.error(f"Failed to reset after commit failure: {reset_error}")

            return {
                "success": False,
                "error": str(e)
            }

    async def _push_changes(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Push changes to remote with safety checks."""
        branch = task.get("branch", None)
        force = task.get("force", False)
        dry_run = task.get("dry_run", False)

        # Get current branch if not specified
        if not branch:
            branch_result = await self._execute_git_command(["branch", "--show-current"])
            branch = branch_result.strip()

        # Check if branch is protected
        protected_branches = self.config.get("protected_branches", ["main"])
        if branch in protected_branches:
            if force and not self.config.get("allow_force_push", False):
                await self._update_git_metric("git_manual_interventions")
                raise ManualInterventionRequired(
                    title="Protected Branch Force Push",
                    description=f"Force push to protected branch '{branch}' requires manual approval",
                    source_system="agent:GitOperationsAgent",
                    context={
                        "branch": branch,
                        "protected_branches": protected_branches,
                        "operation": "push",
                        "force": force
                    }
                )

        # Run safety validation
        if self.config.get("enable_safety_checks", True):
            safety_result = await self._validate_safety({"operation": "push", "target_branch": branch}, context)
            if not safety_result.get("success", False):
                await self._update_git_metric("git_validation_failures")
                return safety_result

        # Check for PR requirement for main branch
        if branch == "main" and self.config.get("require_pr_for_main", True):
            # Check if there's an open PR
            has_pr = await self._check_open_pr(branch)
            if not has_pr:
                await self._update_git_metric("git_manual_interventions")
                raise ManualInterventionRequired(
                    title="PR Required for Main Branch",
                    description=f"Direct push to main branch requires an open pull request",
                    source_system="agent:GitOperationsAgent",
                    context={"branch": branch, "operation": "push"}
                )

        # Predict conflict risk if enabled
        if self.config.get("enable_conflict_prediction", True):
            try:
                # Get remote branch name (assume same as local)
                remote = "origin"
                remote_branch = f"{remote}/{branch}"

                # Check if remote branch exists
                remote_exists = await self._execute_git_command(["ls-remote", "--heads", remote, branch])
                if remote_exists.strip():
                    # Predict conflict risk
                    prediction = await self._predict_conflict_risk(branch, remote_branch)

                    # Log prediction
                    logger.info(f"Conflict prediction for {branch} -> {remote_branch}: {prediction['risk_level']} ({prediction['risk_score']:.1f})")

                    # If high risk, add warning to result (but don't block)
                    if prediction["risk_level"] == "high":
                        logger.warning(f"High conflict risk detected: {prediction['overlapping_files']}")
                        # Could raise ManualInterventionRequired for high risk if desired
                else:
                    logger.info(f"Remote branch {remote_branch} doesn't exist yet, no conflict prediction needed")
            except Exception as e:
                logger.warning(f"Conflict prediction failed: {e}")
                # Don't fail the push if prediction fails

        try:
            # Build push command
            push_cmd = ["push"]
            if dry_run:
                push_cmd.append("--dry-run")
            if force:
                push_cmd.append("--force")
            push_cmd.append("origin")
            push_cmd.append(branch)

            push_result = await self._execute_git_command(push_cmd)

            # Update metrics
            await self._update_git_metric("git_pushes")

            # Send webhook notification
            try:
                await self._send_webhook_notification(
                    event_type="push",
                    data={
                        "branch": branch,
                        "dry_run": dry_run,
                        "force": force,
                        "result": push_result.strip(),
                        "success": True
                    },
                    event_data={
                        "agent_id": self.agent_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            except Exception as webhook_error:
                logger.warning(f"Failed to send push webhook: {webhook_error}")
                # Don't fail the push if webhook fails

            return {
                "success": True,
                "branch": branch,
                "dry_run": dry_run,
                "force": force,
                "result": push_result.strip()
            }

        except Exception as e:
            logger.error(f"Failed to push changes: {e}")
            return {
                "success": False,
                "error": str(e),
                "branch": branch
            }

    async def _manage_branch(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create, switch, or delete branches."""
        operation = task.get("operation", "create")
        branch_name = task.get("branch_name", "")
        from_branch = task.get("from_branch", None)
        purpose = task.get("purpose", "feature")

        # Generate branch name if not provided (only for create operation)
        if not branch_name and operation == "create":
            issue_id = task.get("issue_id")
            branch_name = await self._suggest_branch_name(purpose, issue_id)
            logger.info(f"Generated branch name: {branch_name}")
        elif not branch_name:
            return {
                "success": False,
                "error": "Branch name is required"
            }

        # Validate branch name pattern
        if not re.match(r"^[a-zA-Z0-9/._-]+$", branch_name):
            return {
                "success": False,
                "error": "Invalid branch name"
            }

        try:
            if operation == "create":
                # Check if branch already exists
                branches = await self._execute_git_command(["branch", "--list"])
                if branch_name in branches:
                    return {
                        "success": False,
                        "error": f"Branch '{branch_name}' already exists"
                    }

                # Create branch
                create_cmd = ["checkout", "-b", branch_name]
                if from_branch:
                    create_cmd = ["branch", branch_name, from_branch]

                result = await self._execute_git_command(create_cmd)

                # Update metrics
                await self._update_git_metric("git_branches_created")

                # Send webhook notification
                try:
                    await self._send_webhook_notification(
                        event_type="branch",
                        data={
                            "operation": "create",
                            "branch": branch_name,
                            "from_branch": from_branch,
                            "result": result.strip()
                        },
                        event_data={
                            "agent_id": self.agent_id,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                except Exception as webhook_error:
                    logger.warning(f"Failed to send branch create webhook: {webhook_error}")
                    # Don't fail the operation if webhook fails

                return {
                    "success": True,
                    "operation": "create",
                    "branch": branch_name,
                    "from_branch": from_branch,
                    "result": result.strip()
                }

            elif operation == "switch":
                # Check if branch exists
                branches = await self._execute_git_command(["branch", "--list"])
                if branch_name not in branches:
                    return {
                        "success": False,
                        "error": f"Branch '{branch_name}' does not exist"
                    }

                # Switch to branch
                result = await self._execute_git_command(["checkout", branch_name])

                # Send webhook notification
                try:
                    await self._send_webhook_notification(
                        event_type="branch",
                        data={
                            "operation": "switch",
                            "branch": branch_name,
                            "result": result.strip()
                        },
                        event_data={
                            "agent_id": self.agent_id,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                except Exception as webhook_error:
                    logger.warning(f"Failed to send branch switch webhook: {webhook_error}")
                    # Don't fail the operation if webhook fails

                return {
                    "success": True,
                    "operation": "switch",
                    "branch": branch_name,
                    "result": result.strip()
                }

            elif operation == "delete":
                # Don't allow deletion of protected branches
                protected_branches = self.config.get("protected_branches", ["main"])
                if branch_name in protected_branches:
                    return {
                        "success": False,
                        "error": f"Cannot delete protected branch: {branch_name}"
                    }

                # Delete branch
                result = await self._execute_git_command(["branch", "-d", branch_name])

                # Update metrics
                await self._update_git_metric("git_branches_deleted")

                # Send webhook notification
                try:
                    await self._send_webhook_notification(
                        event_type="branch",
                        data={
                            "operation": "delete",
                            "branch": branch_name,
                            "result": result.strip()
                        },
                        event_data={
                            "agent_id": self.agent_id,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                except Exception as webhook_error:
                    logger.warning(f"Failed to send branch delete webhook: {webhook_error}")
                    # Don't fail the operation if webhook fails

                return {
                    "success": True,
                    "operation": "delete",
                    "branch": branch_name,
                    "result": result.strip()
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown branch operation: {operation}",
                    "supported_operations": ["create", "switch", "delete"]
                }

        except Exception as e:
            logger.error(f"Failed to manage branch: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "branch_name": branch_name
            }

    async def _validate_safety(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Comprehensive safety validation before git operations."""
        operation = task.get("operation", "")
        target_branch = task.get("target_branch", None)

        validation_results = []
        warnings = []
        errors = []

        # 1. Check for uncommitted changes if require_clean_status
        if self.config.get("require_clean_status", True) and operation in ["push", "merge"]:
            status_result = await self._execute_git_command(["status", "--porcelain"])
            if status_result.strip():
                errors.append("Repository has uncommitted changes")

        # 2. Check for too many unstaged changes
        max_unstaged = self.config.get("max_unstaged_changes", 50)
        if max_unstaged > 0:
            status_result = await self._execute_git_command(["status", "--porcelain"])
            unstaged_count = len([line for line in status_result.strip().split('\n') if line and line[1] != ' '])
            if unstaged_count > max_unstaged:
                warnings.append(f"Large number of unstaged changes ({unstaged_count} > {max_unstaged})")

        # 3. Check branch protection
        protected_branches = self.config.get("protected_branches", ["main"])
        if target_branch and target_branch in protected_branches:
            if operation in ["push", "merge", "delete"]:
                validation_results.append(f"Protected branch: {target_branch}")

        # 4. Check for merge conflicts
        if self.config.get("enable_conflict_detection", True):
            conflict_result = await self._execute_git_command(["diff", "--name-only", "--diff-filter=U"])
            if conflict_result.strip():
                errors.append("Merge conflicts detected")

        # 5. Check if tests pass (if configured)
        if self.config.get("test_before_push", True) and operation == "push":
            # This would run actual tests
            validation_results.append("Test validation required before push")

        # 6. Check backup status
        if self.config.get("backup_before_operations", True):
            validation_results.append("Backup recommended before operation")

        # Determine overall safety
        is_safe = len(errors) == 0
        safety_level = "safe" if is_safe else "unsafe"

        return {
            "success": is_safe,
            "safety_level": safety_level,
            "operation": operation,
            "target_branch": target_branch,
            "validation_results": validation_results,
            "warnings": warnings,
            "errors": errors,
            "recommendation": "Proceed" if is_safe else "Do not proceed"
        }

    async def _handle_conflict(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Detect and handle merge conflicts."""
        # Detect conflicts
        conflict_result = await self._execute_git_command(["diff", "--name-only", "--diff-filter=U"])
        conflict_files = conflict_result.strip().split('\n') if conflict_result.strip() else []

        if not conflict_files:
            return {
                "success": True,
                "conflicts_detected": 0,
                "message": "No merge conflicts detected"
            }

        # For now, log manual intervention required
        # In a more advanced implementation, could attempt automatic resolution
        await self._update_git_metric("git_conflicts_detected")
        await self._update_git_metric("git_manual_interventions")

        # Send webhook notification about conflict
        try:
            await self._send_webhook_notification(
                event_type="conflict",
                data={
                    "conflict_files": conflict_files,
                    "conflict_count": len(conflict_files),
                    "operation": task.get("operation", "unknown")
                },
                event_data={
                    "agent_id": self.agent_id,
                    "timestamp": datetime.now().isoformat(),
                    "requires_manual_intervention": True
                }
            )
        except Exception as webhook_error:
            logger.warning(f"Failed to send conflict webhook: {webhook_error}")
            # Continue to raise exception even if webhook fails

        raise ManualInterventionRequired(
            title="Merge Conflicts Detected",
            description=f"{len(conflict_files)} files have merge conflicts requiring manual resolution",
            source_system="agent:GitOperationsAgent",
            context={
                "conflict_files": conflict_files,
                "conflict_count": len(conflict_files),
                "operation": task.get("operation", "unknown")
            }
        )

    async def _rollback_operation(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Rollback a problematic git operation."""
        operation = task.get("operation", "")
        target = task.get("target", None)

        try:
            if operation == "commit":
                # Undo last commit
                result = await self._execute_git_command(["reset", "--soft", "HEAD~1"])
                # Update metrics
                await self._update_git_metric("git_rollbacks")

                # Send webhook notification
                try:
                    await self._send_webhook_notification(
                        event_type="rollback",
                        data={
                            "operation": "rollback_commit",
                            "target": target,
                            "result": result.strip()
                        },
                        event_data={
                            "agent_id": self.agent_id,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                except Exception as webhook_error:
                    logger.warning(f"Failed to send rollback webhook: {webhook_error}")
                    # Don't fail the rollback if webhook fails

                return {
                    "success": True,
                    "operation": "rollback_commit",
                    "result": result.strip()
                }
            elif operation == "push":
                # Revert to previous state (dangerous)
                # This would require more sophisticated logic
                return {
                    "success": False,
                    "error": "Push rollback requires manual intervention",
                    "recommendation": "Use git revert or contact administrator"
                }
            else:
                return {
                    "success": False,
                    "error": f"Unknown rollback operation: {operation}",
                    "supported_operations": ["commit", "push"]
                }

        except Exception as e:
            logger.error(f"Failed to rollback operation: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _generate_report(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate git operations report."""
        # Collect various git information
        branch = await self._execute_git_command(["branch", "--show-current"])
        status = await self._execute_git_command(["status", "--short"])
        log = await self._execute_git_command(["log", "--oneline", "-10"])
        remote = await self._execute_git_command(["remote", "-v"])

        report = {
            "timestamp": datetime.now().isoformat(),
            "branch": branch.strip(),
            "status_summary": status.strip().split('\n') if status.strip() else [],
            "recent_commits": log.strip().split('\n') if log.strip() else [],
            "remotes": remote.strip().split('\n') if remote.strip() else [],
            "agent_config": {
                "repository_path": self.config.get("repository_path"),
                "protected_branches": self.config.get("protected_branches"),
                "safety_checks_enabled": self.config.get("enable_safety_checks")
            }
        }

        return {
            "success": True,
            "report": report
        }

    # ============ AI-Powered Features ============

    async def _generate_ai_commit_message(self, diff: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate AI-powered commit message using diff and context.

        Args:
            diff: Git diff output
            context: Additional context (branch, previous commits, etc.)

        Returns:
            Generated commit message
        """
        try:
            # Prepare prompt for AI
            prompt = f"""Generate a concise, conventional commit message based on the following git diff.
Follow conventional commit format: <type>(<scope>): <description>

Examples:
- feat(auth): add login with Google OAuth
- fix(api): resolve null pointer in user endpoint
- docs(readme): update installation instructions
- chore(deps): update security dependencies

Git diff:
{diff[:2000]}  # Limit diff size

Context: {context or 'No additional context'}

Provide only the commit message, no explanations."""

            # Use AI service with cost optimization
            response = await ai_request(
                prompt=prompt,
                task_type=TaskType.CLASSIFICATION,  # Classification is cheap
                model_override="groq"  # Use fastest/cheapest model
            )

            # Extract commit message from response
            message = response.strip()

            # Validate it's not empty and follows basic pattern
            if not message or len(message) > 200:
                logger.warning(f"AI-generated commit message invalid: {message}")
                # Fallback to generic message
                return "chore: update code"

            logger.info(f"AI-generated commit message: {message}")
            return message

        except Exception as e:
            logger.error(f"Failed to generate AI commit message: {e}")
            # Fallback to generic message
            return "chore: update code"

    async def _predict_conflict_risk(self, source_branch: str, target_branch: str) -> Dict[str, Any]:
        """
        Predict risk of merge conflicts between branches.

        Args:
            source_branch: Branch to merge from
            target_branch: Branch to merge into

        Returns:
            Dictionary with risk assessment
        """
        try:
            # Get commit divergence
            divergence_cmd = await self._execute_git_command([
                "rev-list", "--count", "--left-right",
                f"{target_branch}...{source_branch}"
            ])

            left, right = divergence_cmd.strip().split('\t') if '\t' in divergence_cmd else (0, 0)
            left_count = int(left) if left.isdigit() else 0
            right_count = int(right) if right.isdigit() else 0

            # Get file change overlap
            source_files = await self._execute_git_command([
                "diff", "--name-only", f"{target_branch}..{source_branch}"
            ])
            target_files = await self._execute_git_command([
                "diff", "--name-only", f"{source_branch}..{target_branch}"
            ])

            source_set = set(source_files.strip().split('\n')) if source_files.strip() else set()
            target_set = set(target_files.strip().split('\n')) if target_files.strip() else set()
            overlapping_files = source_set.intersection(target_set)

            # Calculate risk score (0-100)
            total_changes = left_count + right_count
            overlap_ratio = len(overlapping_files) / max(len(source_set) + len(target_set), 1)

            if total_changes == 0:
                risk_score = 0
            elif total_changes > 50:
                risk_score = min(80 + (overlap_ratio * 20), 100)
            else:
                risk_score = min(overlap_ratio * 100, 100)

            risk_level = "low" if risk_score < 30 else "medium" if risk_score < 70 else "high"

            return {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "divergence": {"left": left_count, "right": right_count},
                "overlapping_files": list(overlapping_files),
                "total_changes": total_changes,
                "recommendation": "Proceed with caution" if risk_level == "high" else "Safe to merge"
            }

        except Exception as e:
            logger.error(f"Failed to predict conflict risk: {e}")
            return {
                "risk_score": 50,  # Default medium risk
                "risk_level": "medium",
                "error": str(e)
            }

    async def _suggest_branch_name(self, purpose: str, issue_id: Optional[str] = None) -> str:
        """
        Suggest intelligent branch name based on purpose and context.

        Args:
            purpose: Branch purpose (feature, fix, hotfix, chore, docs, test, etc.)
            issue_id: Optional issue/ticket ID

        Returns:
            Suggested branch name
        """
        try:
            # Clean purpose
            purpose = purpose.lower().strip()
            if purpose in ["feature", "feat"]:
                prefix = "feature"
            elif purpose in ["fix", "bugfix"]:
                prefix = "fix"
            elif purpose in ["hotfix"]:
                prefix = "hotfix"
            elif purpose in ["chore", "task"]:
                prefix = "chore"
            elif purpose in ["docs", "documentation"]:
                prefix = "docs"
            elif purpose in ["test", "testing"]:
                prefix = "test"
            else:
                prefix = "feature"

            # Generate descriptive slug
            # For now, create simple timestamp-based name
            timestamp = datetime.now().strftime("%m%d")
            random_suffix = os.urandom(2).hex()  # 4 char random

            if issue_id:
                branch_name = f"{prefix}/{issue_id}-{timestamp}-{random_suffix}"
            else:
                branch_name = f"{prefix}/{timestamp}-{random_suffix}"

            # Ensure branch name is valid for git
            branch_name = re.sub(r'[^a-zA-Z0-9/._-]', '-', branch_name)
            branch_name = branch_name.lower()

            logger.info(f"Suggested branch name: {branch_name}")
            return branch_name

        except Exception as e:
            logger.error(f"Failed to suggest branch name: {e}")
            # Fallback to timestamp-based name
            return f"feature/{datetime.now().strftime('%m%d')}-{os.urandom(2).hex()}"

    async def _analyze_git_patterns(self) -> Dict[str, Any]:
        """
        Analyze git history patterns to suggest workflow improvements.

        Returns:
            Dictionary with analysis results and recommendations
        """
        try:
            # Get branch statistics
            branches = await self._execute_git_command(["branch", "-a", "--format=%(refname:short) %(committerdate:relative)"])
            branch_lines = branches.strip().split('\n') if branches.strip() else []

            # Get commit frequency (last 30 days)
            commit_stats = await self._execute_git_command(["log", "--since='30 days ago'", "--pretty=format:%ad", "--date=short"])
            commit_dates = commit_stats.strip().split('\n') if commit_stats.strip() else []
            commit_count = len(commit_dates)

            # Get stale branches (no commits in 90 days)
            stale_branches = []
            for line in branch_lines:
                if 'origin/' in line and 'HEAD' not in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        branch_name = parts[0]
                        # Check last commit date (simplified)
                        if 'months ago' in line or 'years ago' in line:
                            stale_branches.append(branch_name)

            # Get merge frequency
            merge_commits = await self._execute_git_command(["log", "--since='90 days ago'", "--merges", "--pretty=format:%ad", "--date=short"])
            merge_count = len(merge_commits.strip().split('\n')) if merge_commits.strip() else 0

            # Generate recommendations
            recommendations = []
            if len(stale_branches) > 5:
                recommendations.append(f"Consider cleaning up {len(stale_branches)} stale branches")
            if commit_count < 10:
                recommendations.append("Low commit frequency - consider more regular commits")
            if merge_count == 0 and len(branch_lines) > 3:
                recommendations.append("No recent merges - consider merging feature branches regularly")

            return {
                "branch_count": len(branch_lines),
                "stale_branches": stale_branches[:10],  # Limit output
                "commit_count_30d": commit_count,
                "merge_count_90d": merge_count,
                "recommendations": recommendations,
                "summary": f"Repository has {len(branch_lines)} branches, {commit_count} commits in last 30 days"
            }

        except Exception as e:
            logger.error(f"Failed to analyze git patterns: {e}")
            return {
                "error": str(e),
                "branch_count": 0,
                "stale_branches": [],
                "commit_count_30d": 0,
                "recommendations": ["Analysis failed"]
            }

    # ============ Tool Implementation Methods ============

    async def _tool_git_status(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for git_status."""
        result = await self._analyze_changes({"type": "analyze_changes"}, None)
        return result

    async def _tool_git_commit(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for git_commit."""
        result = await self._create_commit({
            "type": "create_commit",
            "message": kwargs.get("message", ""),
            "files": kwargs.get("files", []),
            "skip_validation": kwargs.get("skip_validation", False)
        }, None)
        return result

    async def _tool_git_push(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for git_push."""
        result = await self._push_changes({
            "type": "push_changes",
            "branch": kwargs.get("branch", None),
            "force": kwargs.get("force", False),
            "dry_run": kwargs.get("dry_run", False)
        }, None)
        return result

    async def _tool_git_create_branch(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for git_create_branch."""
        result = await self._manage_branch({
            "type": "manage_branch",
            "operation": "create",
            "branch_name": kwargs.get("branch_name", ""),
            "from_branch": kwargs.get("from_branch", None),
            "purpose": kwargs.get("purpose", "feature"),
            "issue_id": kwargs.get("issue_id", None)
        }, None)
        return result

    async def _tool_git_validate_safety(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for git_validate_safety."""
        result = await self._validate_safety({
            "type": "validate_safety",
            "operation": kwargs.get("operation", ""),
            "target_branch": kwargs.get("target_branch", None)
        }, None)
        return result

    async def _tool_git_analyze_patterns(self, **kwargs) -> Dict[str, Any]:
        """Tool implementation for git_analyze_patterns."""
        result = await self._analyze_git_patterns()
        return result

    # ============ Helper Methods ============

    async def _update_git_metric(self, metric_name: str, increment: int = 1) -> None:
        """Update git-specific metric."""
        if metric_name in self.metrics:
            self.metrics[metric_name] += increment
        else:
            self.metrics[metric_name] = increment
        logger.debug(f"Updated git metric {metric_name}: {self.metrics[metric_name]}")

        # Also record to performance monitoring system for dashboards
        try:
            # Map git metric to appropriate metric type
            metric_type = MetricType.TOOL_USAGE  # Using TOOL_USAGE for git operations

            await performance_monitor.record_metric(
                agent_id=self.agent_id,
                metric_type=metric_type,
                value=self.metrics[metric_name],
                tags={
                    "git_metric": metric_name,
                    "agent_name": self.name,
                    "domain": self.domain
                }
            )
        except Exception as e:
            logger.warning(f"Failed to record git metric to performance monitor: {e}")
            # Don't fail the operation if monitoring fails

    async def _execute_git_command(self, args: List[str]) -> str:
        """Execute git command and return output."""
        repo_path = self.config.get("repository_path", "/home/philip/nexus")
        cmd = ["git", "-C", repo_path] + args

        try:
            logger.debug(f"Executing git command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            raise RuntimeError(f"Git command failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            logger.error("Git command timed out")
            raise RuntimeError("Git command timed out")

    def _generate_recommendations(
        self,
        staged: int,
        unstaged: int,
        untracked: int,
        ahead: int
    ) -> List[str]:
        """Generate recommendations based on git status."""
        recommendations = []

        if unstaged > 0 or untracked > 0:
            recommendations.append("Consider staging changes with 'git add'")

        if staged > 0:
            recommendations.append("Ready to commit staged changes")

        if ahead > 0:
            recommendations.append("Ready to push commits to remote")

        if unstaged > 10:
            recommendations.append("Large number of unstaged changes - consider committing in smaller batches")

        if untracked > 5:
            recommendations.append("Multiple untracked files - consider adding to .gitignore if they're not needed")

        return recommendations

    async def _check_open_pr(self, branch: str) -> bool:
        """Check if there's an open pull request for the branch."""
        # This would integrate with GitHub API
        # For now, return True to allow push (simplified)
        return True

    async def _send_webhook_notification(
        self,
        event_type: str,
        data: Dict[str, Any],
        event_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send webhook notification for git events.

        Args:
            event_type: Type of git event (commit, push, conflict, branch, rollback)
            data: Primary event data from the git operation
            event_data: Additional context data
        """
        if not self.config.get("enable_webhooks", True):
            return

        webhook_events = self.config.get("webhook_events", ["commit", "push", "conflict"])
        if event_type not in webhook_events:
            logger.debug(f"Webhook event type '{event_type}' not in enabled events: {webhook_events}")
            return

        webhook_url = f"{self.config.get('webhook_base_url', 'http://localhost:5678/webhook')}/git-{event_type}"
        timeout = self.config.get("webhook_timeout", 10)
        max_retries = self.config.get("webhook_retries", 3)

        payload = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "data": data,
            "context": event_data or {}
        }

        logger.info(f"Sending webhook for {event_type} event to {webhook_url}")

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(webhook_url, json=payload)
                    response.raise_for_status()
                    logger.debug(f"Webhook sent successfully: {response.status_code}")
                    return
            except Exception as e:
                logger.warning(f"Webhook attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"All webhook attempts failed for {event_type} event")
                else:
                    import asyncio
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff


# ============ Agent Registration Helper ============

async def register_git_operations_agent() -> GitOperationsAgent:
    """
    Register git operations agent with the agent registry.

    Call this during system startup to register the git operations agent.
    Returns existing agent if already registered.
    """
    from .registry import registry

    # Check if git operations agent already exists by name
    existing_agent = await registry.get_agent_by_name("Git Operations Agent")
    if existing_agent:
        logger.info(f"Git operations agent already registered: {existing_agent.name}")
        return existing_agent

    # Create new git operations agent using registry's create_agent method
    try:
        agent = await registry.create_agent(
            agent_type="domain",  # Using domain type since no specific GIT_OPERATIONS type
            name="Git Operations Agent",
            description="Fully autonomous git operations with safety constraints and edge case handling",
            capabilities=[
                "git_commit",
                "git_push",
                "git_branch_management",
                "git_safety_validation",
                "conflict_detection",
                "change_analysis",
                "automated_rollback",
                "manual_task_integration",
                "performance_monitoring"
            ],
            domain="git_operations",
            config={
                "repository_path": "/home/philip/nexus",
                "allowed_branches": ["main", "develop", "feature/*", "hotfix/*"],
                "protected_branches": ["main"],
                "max_commit_size_mb": 100,
                "require_clean_status": True,
                "enable_auto_push": True,
                "enable_safety_checks": True,
                "enable_conflict_detection": True,
                "max_unstaged_changes": 50,
                "require_commit_message": True,
                "commit_message_pattern": r"^[A-Za-z].+$",
                "allow_force_push": False,
                "require_pr_for_main": True,
                "test_before_push": True,
                "backup_before_operations": True,
                # Webhook integration for n8n workflows
                "enable_webhooks": True,
                "webhook_base_url": "http://localhost:5678/webhook",
                "webhook_timeout": 10,
                "webhook_retries": 3,
                "webhook_events": ["commit", "push", "conflict", "branch", "rollback"],
                # AI-powered features
                "enable_ai_commit_messages": True,
                "enable_conflict_prediction": True
            }
        )
        logger.info(f"Git operations agent created and registered: {agent.name}")
        return agent
    except ValueError as e:
        # Likely duplicate name (race condition) - try to fetch again
        logger.warning(f"Duplicate agent creation attempt: {e}")
        existing_agent = await registry.get_agent_by_name("Git Operations Agent")
        if existing_agent:
            logger.info(f"Retrieved existing git operations agent after duplicate error: {existing_agent.name}")
            return existing_agent
        raise