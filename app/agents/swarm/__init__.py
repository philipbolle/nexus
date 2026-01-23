"""
NEXUS Swarm Communication Layer

Redis Pub/Sub integration, event bus system, consensus protocols (RAFT),
and conflict resolution voting mechanisms for elite coding swarms.
"""

__version__ = "1.0.0"

# Pub/Sub system
from .pubsub import SwarmPubSub, swarm_pubsub, initialize_swarm_pubsub, close_swarm_pubsub

# Event bus system
from .event_bus import SwarmEventBus, swarm_event_bus, initialize_event_bus, close_event_bus

# RAFT consensus
from .raft import RaftNode, RaftConsensus, RaftState

# Voting system
from .voting import VotingSystem, VotingStrategy, VotingStatus

# Swarm agent
from .agent import SwarmAgent, create_swarm_agent

# Swarm orchestrator
from .swarm_orchestrator import SwarmOrchestratorAgent, create_swarm_orchestrator

__all__ = [
    # Pub/Sub
    "SwarmPubSub", "swarm_pubsub", "initialize_swarm_pubsub", "close_swarm_pubsub",
    # Event bus
    "SwarmEventBus", "swarm_event_bus", "initialize_event_bus", "close_event_bus",
    # RAFT consensus
    "RaftNode", "RaftConsensus", "RaftState",
    # Voting system
    "VotingSystem", "VotingStrategy", "VotingStatus",
    # Swarm agent
    "SwarmAgent", "create_swarm_agent",
    # Swarm orchestrator
    "SwarmOrchestratorAgent", "create_swarm_orchestrator",
]