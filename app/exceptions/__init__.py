"""
Exception classes for the NEXUS system.
"""

from .manual_tasks import (
    ManualInterventionRequired,
    SecurityInterventionRequired,
    ConfigurationInterventionRequired,
    PhysicalInterventionRequired,
    ApprovalRequired,
    PurchaseRequired,
    LegalInterventionRequired,
    PersonalDecisionRequired,
    TechnicalLimitationEncountered
)

__all__ = [
    "ManualInterventionRequired",
    "SecurityInterventionRequired",
    "ConfigurationInterventionRequired",
    "PhysicalInterventionRequired",
    "ApprovalRequired",
    "PurchaseRequired",
    "LegalInterventionRequired",
    "PersonalDecisionRequired",
    "TechnicalLimitationEncountered"
]