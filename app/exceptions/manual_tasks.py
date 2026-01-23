"""
Manual Task Exceptions

Exception hierarchy for tasks requiring human intervention that cannot be automated
by AI agents, even with user approval. These exceptions are caught by the error
handling system and automatically logged to the manual_tasks table and philip-tasks
markdown file.
"""

from typing import Optional, Dict, Any


class ManualInterventionRequired(Exception):
    """
    Base exception for tasks requiring human intervention.

    Args:
        title: Short title of the task (e.g., "Add Gmail App Password")
        description: Detailed description of what needs to be done
        category: Task category (security, configuration, purchase, approval, physical, legal, personal, technical, general)
        priority: Task priority (low, medium, high, critical)
        source_system: System that created the task (e.g., "agent:EmailIntelligenceAgent")
        source_id: ID of the source entity (agent_id, tool_execution_id, etc.)
        context: Additional context about why task was created
    """

    def __init__(
        self,
        title: str,
        description: str,
        category: str = "general",
        priority: str = "medium",
        source_system: str = "unknown",
        source_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.title = title
        self.description = description
        self.category = category
        self.priority = priority
        self.source_system = source_system
        self.source_id = source_id
        self.context = context or {}
        super().__init__(f"Manual intervention required: {title}")


class SecurityInterventionRequired(ManualInterventionRequired):
    """
    Exception for security-related manual tasks requiring human intervention.

    Examples:
    - Adding API keys or passwords to .env file
    - Authorizing security-sensitive operations
    - Reviewing security permissions
    """

    def __init__(
        self,
        description: str,
        title: Optional[str] = None,
        priority: str = "high",
        source_system: str = "unknown",
        source_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            title=title or "Security Action Required",
            description=description,
            category="security",
            priority=priority,
            source_system=source_system,
            source_id=source_id,
            context=context
        )


class ConfigurationInterventionRequired(ManualInterventionRequired):
    """
    Exception for configuration-related manual tasks requiring human intervention.

    Examples:
    - Adding configuration to .env file
    - Setting up external service connections
    - Configuring API endpoints or webhooks
    """

    def __init__(
        self,
        description: str,
        title: Optional[str] = None,
        priority: str = "medium",
        source_system: str = "unknown",
        source_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            title=title or "Configuration Required",
            description=description,
            category="configuration",
            priority=priority,
            source_system=source_system,
            source_id=source_id,
            context=context
        )


class PhysicalInterventionRequired(ManualInterventionRequired):
    """
    Exception for physical device access tasks requiring human intervention.

    Examples:
    - Turning physical devices on/off
    - Plugging/unplugging cables
    - Pressing physical buttons
    """

    def __init__(
        self,
        description: str,
        title: Optional[str] = None,
        priority: str = "medium",
        source_system: str = "unknown",
        source_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            title=title or "Physical Action Required",
            description=description,
            category="physical",
            priority=priority,
            source_system=source_system,
            source_id=source_id,
            context=context
        )


class ApprovalRequired(ManualInterventionRequired):
    """
    Exception for tasks requiring explicit human approval.

    Examples:
    - Approving budget overrides
    - Confirming purchases
    - Authorizing legal agreements
    """

    def __init__(
        self,
        description: str,
        title: Optional[str] = None,
        priority: str = "medium",
        source_system: str = "unknown",
        source_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            title=title or "Approval Required",
            description=description,
            category="approval",
            priority=priority,
            source_system=source_system,
            source_id=source_id,
            context=context
        )


class PurchaseRequired(ManualInterventionRequired):
    """
    Exception for tasks requiring purchases or financial transactions.

    Examples:
    - Making purchases with real money
    - Authorizing payments
    - Providing credit card information
    """

    def __init__(
        self,
        description: str,
        title: Optional[str] = None,
        priority: str = "medium",
        source_system: str = "unknown",
        source_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            title=title or "Purchase Required",
            description=description,
            category="purchase",
            priority=priority,
            source_system=source_system,
            source_id=source_id,
            context=context
        )


class LegalInterventionRequired(ManualInterventionRequired):
    """
    Exception for legal/compliance tasks requiring human intervention.

    Examples:
    - Signing legal documents
    - Providing consent for data processing
    - Accepting terms of service
    """

    def __init__(
        self,
        description: str,
        title: Optional[str] = None,
        priority: str = "high",
        source_system: str = "unknown",
        source_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            title=title or "Legal Action Required",
            description=description,
            category="legal",
            priority=priority,
            source_system=source_system,
            source_id=source_id,
            context=context
        )


class PersonalDecisionRequired(ManualInterventionRequired):
    """
    Exception for personal decisions requiring human input.

    Examples:
    - Making life choices (career, relationships)
    - Providing personal preferences
    - Making ethical judgments
    """

    def __init__(
        self,
        description: str,
        title: Optional[str] = None,
        priority: str = "medium",
        source_system: str = "unknown",
        source_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            title=title or "Personal Decision Required",
            description=description,
            category="personal",
            priority=priority,
            source_system=source_system,
            source_id=source_id,
            context=context
        )


class TechnicalLimitationEncountered(ManualInterventionRequired):
    """
    Exception for technical limitations requiring human intervention.

    Examples:
    - Missing dependencies or libraries
    - Unsupported file formats or protocols
    - Hardware limitations
    """

    def __init__(
        self,
        description: str,
        title: Optional[str] = None,
        priority: str = "medium",
        source_system: str = "unknown",
        source_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            title=title or "Technical Limitation Encountered",
            description=description,
            category="technical",
            priority=priority,
            source_system=source_system,
            source_id=source_id,
            context=context
        )