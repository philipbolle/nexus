"""
NEXUS Swarm Communication Layer - RAFT Consensus Algorithm

Simplified RAFT consensus implementation for swarm decision-making.
Based on the RAFT consensus algorithm with Redis Pub/Sub for RPC communication.
"""

import asyncio
import json
import logging
import random
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import uuid

from .pubsub import swarm_pubsub
from ...database import db

logger = logging.getLogger(__name__)


class RaftState:
    """RAFT node states."""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class RaftNode:
    """
    RAFT consensus node representing a single agent in a consensus group.

    Each node maintains its own state and participates in leader election,
    log replication, and state machine application.
    """

    def __init__(
        self,
        consensus_group_id: str,
        agent_id: str,
        agent_name: str,
        swarm_id: str,
        node_address: str = None
    ):
        """
        Initialize a RAFT node.

        Args:
            consensus_group_id: ID of consensus group
            agent_id: Agent ID of this node
            agent_name: Agent name for logging
            swarm_id: Swarm ID this group belongs to
            node_address: Network address (optional, uses agent_id as default)
        """
        self.consensus_group_id = consensus_group_id
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.swarm_id = swarm_id
        self.node_address = node_address or agent_id

        # Persistent state (should be stored to stable storage)
        self.current_term: int = 0
        self.voted_for: Optional[str] = None  # candidateId that received vote in current term
        self.log: List[Dict[str, Any]] = []  # log entries

        # Volatile state
        self.commit_index: int = 0
        self.last_applied: int = 0
        self.state: str = RaftState.FOLLOWER

        # Volatile leader state (reinitialized after election)
        self.next_index: Dict[str, int] = {}  # for each server, index of next log entry to send
        self.match_index: Dict[str, int] = {}  # for each server, index of highest log entry known to be replicated

        # Election timeout (randomized between 150-300ms)
        self.election_timeout_ms: int = random.randint(150, 300)
        self.heartbeat_interval_ms: int = 50  # 50ms heartbeats

        # Timers
        self.last_heartbeat_received: Optional[datetime] = None
        self.election_timer_start: Optional[datetime] = None
        self.heartbeat_timer_start: Optional[datetime] = None

        # Runtime
        self._running = False
        self._election_timer_task: Optional[asyncio.Task] = None
        self._heartbeat_timer_task: Optional[asyncio.Task] = None
        self._message_listener_task: Optional[asyncio.Task] = None

        logger.debug(f"RAFT node created: {agent_name} in group {consensus_group_id}")

    async def initialize(self) -> None:
        """Initialize node and load persistent state from database."""
        # Load persistent state from database
        await self._load_persistent_state()

        self._running = True

        # Start timers
        self._reset_election_timer()
        self._election_timer_task = asyncio.create_task(self._election_timer())

        # Start message listener
        self._message_listener_task = asyncio.create_task(self._listen_for_messages())

        logger.info(f"RAFT node initialized: {self.agent_name} (term: {self.current_term})")

    async def close(self) -> None:
        """Close node and cleanup."""
        self._running = False

        # Cancel tasks
        tasks = [self._election_timer_task, self._heartbeat_timer_task, self._message_listener_task]
        for task in tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Save state
        await self._save_persistent_state()

        logger.info(f"RAFT node closed: {self.agent_name}")

    async def _load_persistent_state(self) -> None:
        """Load persistent state from database."""
        try:
            # Load consensus group state
            group = await db.fetch_one(
                """
                SELECT current_term, voted_for, leader_id, state
                FROM consensus_groups
                WHERE id = $1
                """,
                self.consensus_group_id
            )

            if group:
                self.current_term = group["current_term"] or 0
                self.voted_for = group["voted_for"]
                # Note: leader_id and state are group-level, not node-level

            # Load log entries
            entries = await db.fetch_all(
                """
                SELECT term, index, command_type, command_data, applied
                FROM consensus_log_entries
                WHERE consensus_group_id = $1
                ORDER BY index
                """,
                self.consensus_group_id
            )

            self.log = []
            for entry in entries:
                self.log.append({
                    "term": entry["term"],
                    "index": entry["index"],
                    "command_type": entry["command_type"],
                    "command_data": entry["command_data"],
                    "applied": entry["applied"]
                })

                # Update commit_index and last_applied
                if entry["applied"]:
                    self.last_applied = max(self.last_applied, entry["index"])

            logger.debug(f"Loaded {len(self.log)} log entries for node {self.agent_name}")

        except Exception as e:
            logger.error(f"Failed to load persistent state for node {self.agent_name}: {e}")

    async def _save_persistent_state(self) -> None:
        """Save persistent state to database."""
        try:
            # Update consensus group (node-specific state not stored at group level)
            # For simplicity, we store node state in a separate table or metadata
            # For now, just update the group's current_term if we're leader
            pass

            # Save log entries (new entries only)
            for entry in self.log:
                # Check if entry already exists
                existing = await db.fetch_one(
                    """
                    SELECT id FROM consensus_log_entries
                    WHERE consensus_group_id = $1 AND term = $2 AND index = $3
                    """,
                    self.consensus_group_id,
                    entry["term"],
                    entry["index"]
                )

                if not existing:
                    await db.execute(
                        """
                        INSERT INTO consensus_log_entries
                        (consensus_group_id, term, index, command_type, command_data, applied)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        self.consensus_group_id,
                        entry["term"],
                        entry["index"],
                        entry["command_type"],
                        json.dumps(entry["command_data"]),
                        entry.get("applied", False)
                    )

            logger.debug(f"Saved persistent state for node {self.agent_name}")

        except Exception as e:
            logger.error(f"Failed to save persistent state for node {self.agent_name}: {e}")

    # ===== Timer Management =====

    def _reset_election_timer(self) -> None:
        """Reset election timer with random timeout."""
        self.election_timer_start = datetime.now()
        self.election_timeout_ms = random.randint(150, 300)

    async def _election_timer(self) -> None:
        """Election timer task."""
        while self._running:
            try:
                await asyncio.sleep(self.election_timeout_ms / 1000.0)

                if not self._running:
                    break

                # Check if we've received a heartbeat recently
                if self.last_heartbeat_received:
                    time_since_heartbeat = (datetime.now() - self.last_heartbeat_received).total_seconds() * 1000
                    if time_since_heartbeat < self.election_timeout_ms:
                        self._reset_election_timer()
                        continue

                # Start election if follower or candidate
                if self.state in [RaftState.FOLLOWER, RaftState.CANDIDATE]:
                    await self._start_election()

                self._reset_election_timer()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in election timer for {self.agent_name}: {e}")
                await asyncio.sleep(1)

    async def _start_election(self) -> None:
        """Start leader election."""
        logger.info(f"Node {self.agent_name} starting election for term {self.current_term + 1}")

        # Transition to candidate
        self.state = RaftState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.agent_id

        # Save term update
        await self._save_persistent_state()

        # Reset election timer
        self._reset_election_timer()

        # Send RequestVote RPC to all other nodes
        await self._send_request_vote_rpc()

    async def _send_request_vote_rpc(self) -> None:
        """Send RequestVote RPC to all nodes in consensus group."""
        rpc_message = {
            "rpc_type": "RequestVote",
            "term": self.current_term,
            "candidate_id": self.agent_id,
            "last_log_index": len(self.log),
            "last_log_term": self.log[-1]["term"] if self.log else 0,
            "timestamp": datetime.now().isoformat()
        }

        # Publish to consensus group channel
        channel = f"swarm:{self.swarm_id}:consensus:{self.consensus_group_id}:rpc"
        await swarm_pubsub.publish(channel, rpc_message)

        logger.debug(f"Node {self.agent_name} sent RequestVote RPC for term {self.current_term}")

    # ===== Message Handling =====

    async def _listen_for_messages(self) -> None:
        """Listen for RAFT RPC messages."""
        # Subscribe to consensus group channel
        channel = f"swarm:{self.swarm_id}:consensus:{self.consensus_group_id}:rpc"
        try:
            await swarm_pubsub.subscribe(channel)
        except Exception as e:
            logger.error(f"Failed to subscribe to channel {channel}: {e}")
            return

        try:
            async for message in swarm_pubsub.listen():
                if not self._running:
                    break

                # Filter messages for this consensus group
                if "rpc_type" in message:
                    await self._handle_rpc_message(message)

        except asyncio.CancelledError:
            logger.debug(f"RAFT message listener cancelled for {self.agent_name}")
        except Exception as e:
            logger.error(f"Error in RAFT message listener for {self.agent_name}: {e}")

    async def _handle_rpc_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming RAFT RPC message."""
        try:
            rpc_type = message["rpc_type"]
            term = message["term"]

            # If RPC request or response contains term > currentTerm, update currentTerm
            if term > self.current_term:
                self.current_term = term
                self.state = RaftState.FOLLOWER
                self.voted_for = None
                await self._save_persistent_state()

            if rpc_type == "RequestVote":
                await self._handle_request_vote(message)
            elif rpc_type == "RequestVoteResponse":
                await self._handle_request_vote_response(message)
            elif rpc_type == "AppendEntries":
                await self._handle_append_entries(message)
            elif rpc_type == "AppendEntriesResponse":
                await self._handle_append_entries_response(message)
            else:
                logger.warning(f"Unknown RPC type: {rpc_type}")

        except Exception as e:
            logger.error(f"Failed to handle RPC message: {e}")

    async def _handle_request_vote(self, message: Dict[str, Any]) -> None:
        """Handle RequestVote RPC."""
        candidate_id = message["candidate_id"]
        last_log_index = message["last_log_index"]
        last_log_term = message["last_log_term"]

        # Determine if we grant vote
        grant_vote = False

        # Check if candidate's log is at least as up-to-date as ours
        our_last_log_term = self.log[-1]["term"] if self.log else 0
        our_last_log_index = len(self.log)

        log_ok = (last_log_term > our_last_log_term) or \
                 (last_log_term == our_last_log_term and last_log_index >= our_last_log_index)

        if log_ok and (self.voted_for is None or self.voted_for == candidate_id):
            grant_vote = True
            self.voted_for = candidate_id
            await self._save_persistent_state()

        # Send response
        response = {
            "rpc_type": "RequestVoteResponse",
            "term": self.current_term,
            "vote_granted": grant_vote,
            "voter_id": self.agent_id,
            "timestamp": datetime.now().isoformat()
        }

        channel = f"swarm:{self.swarm_id}:consensus:{self.consensus_group_id}:rpc"
        await swarm_pubsub.publish(channel, response)

        logger.debug(f"Node {self.agent_name} voted {'for' if grant_vote else 'against'} {candidate_id}")

    async def _handle_request_vote_response(self, message: Dict[str, Any]) -> None:
        """Handle RequestVoteResponse RPC."""
        if self.state != RaftState.CANDIDATE:
            return

        vote_granted = message["vote_granted"]
        voter_id = message["voter_id"]

        # In a full implementation, we'd track votes and become leader if majority
        # Simplified: if we receive any vote, consider ourselves leader
        if vote_granted:
            logger.info(f"Node {self.agent_name} received vote from {voter_id}")

            # Transition to leader
            self.state = RaftState.LEADER
            self._start_heartbeat_timer()

            # Announce leadership
            await self._announce_leadership()

    async def _announce_leadership(self) -> None:
        """Announce new leadership to swarm."""
        announcement = {
            "event_type": "leader_elected",
            "consensus_group_id": self.consensus_group_id,
            "leader_id": self.agent_id,
            "leader_name": self.agent_name,
            "term": self.current_term,
            "timestamp": datetime.now().isoformat()
        }

        channel = f"swarm:{self.swarm_id}:events"
        await swarm_pubsub.publish(channel, announcement)

        logger.info(f"Node {self.agent_name} elected leader for term {self.current_term}")

    async def _handle_append_entries(self, message: Dict[str, Any]) -> None:
        """Handle AppendEntries RPC (heartbeat or log replication)."""
        leader_id = message["leader_id"]
        prev_log_index = message.get("prev_log_index", 0)
        prev_log_term = message.get("prev_log_term", 0)
        entries = message.get("entries", [])
        leader_commit = message.get("leader_commit", 0)

        # Reset election timer since we received communication from leader
        self.last_heartbeat_received = datetime.now()

        success = False

        # Check log consistency
        if prev_log_index > 0:
            if len(self.log) >= prev_log_index:
                if self.log[prev_log_index - 1]["term"] != prev_log_term:
                    # Log inconsistency
                    success = False
                else:
                    success = True
                    # Append entries (simplified)
                    for entry in entries:
                        # Check if entry already exists
                        if entry["index"] > len(self.log):
                            self.log.append(entry)
            else:
                success = False
        else:
            success = True
            for entry in entries:
                if entry["index"] > len(self.log):
                    self.log.append(entry)

        # Update commit index
        if success and leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.log))

        # Send response
        response = {
            "rpc_type": "AppendEntriesResponse",
            "term": self.current_term,
            "success": success,
            "follower_id": self.agent_id,
            "match_index": len(self.log),
            "timestamp": datetime.now().isoformat()
        }

        channel = f"swarm:{self.swarm_id}:consensus:{self.consensus_group_id}:rpc"
        await swarm_pubsub.publish(channel, response)

    async def _handle_append_entries_response(self, message: Dict[str, Any]) -> None:
        """Handle AppendEntriesResponse RPC."""
        if self.state != RaftState.LEADER:
            return

        follower_id = message["follower_id"]
        success = message["success"]
        match_index = message["match_index"]

        # Update next_index and match_index for follower
        if success:
            self.next_index[follower_id] = match_index + 1
            self.match_index[follower_id] = match_index
        else:
            # Decrement next_index and retry
            if follower_id in self.next_index:
                self.next_index[follower_id] = max(1, self.next_index[follower_id] - 1)

        # Check if we can commit entries
        await self._update_commit_index()

    def _start_heartbeat_timer(self) -> None:
        """Start heartbeat timer (leader only)."""
        if self._heartbeat_timer_task:
            self._heartbeat_timer_task.cancel()

        self.heartbeat_timer_start = datetime.now()
        self._heartbeat_timer_task = asyncio.create_task(self._heartbeat_timer())

    async def _heartbeat_timer(self) -> None:
        """Heartbeat timer task (leader only)."""
        while self._running and self.state == RaftState.LEADER:
            try:
                await asyncio.sleep(self.heartbeat_interval_ms / 1000.0)

                if not self._running or self.state != RaftState.LEADER:
                    break

                # Send heartbeat to all followers
                await self._send_heartbeat()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat timer for {self.agent_name}: {e}")
                await asyncio.sleep(1)

    async def _send_heartbeat(self) -> None:
        """Send heartbeat (AppendEntries RPC with no entries) to followers."""
        heartbeat = {
            "rpc_type": "AppendEntries",
            "term": self.current_term,
            "leader_id": self.agent_id,
            "prev_log_index": len(self.log),
            "prev_log_term": self.log[-1]["term"] if self.log else 0,
            "entries": [],
            "leader_commit": self.commit_index,
            "timestamp": datetime.now().isoformat()
        }

        channel = f"swarm:{self.swarm_id}:consensus:{self.consensus_group_id}:rpc"
        await swarm_pubsub.publish(channel, heartbeat)

        logger.debug(f"Leader {self.agent_name} sent heartbeat")

    async def _update_commit_index(self) -> None:
        """Update commit index based on match_index of followers."""
        if self.state != RaftState.LEADER:
            return

        # Sort match indices
        match_indices = list(self.match_index.values())
        match_indices.append(len(self.log))  # Include leader's own log
        match_indices.sort()

        # Majority index
        majority_index = match_indices[len(match_indices) // 2]

        # Check if log entry at majority_index can be committed
        if majority_index > self.commit_index:
            if self.log[majority_index - 1]["term"] == self.current_term:
                self.commit_index = majority_index

                # Apply committed entries
                await self._apply_committed_entries()

    async def _apply_committed_entries(self) -> None:
        """Apply committed entries to state machine."""
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied - 1]

            # Apply entry (simplified)
            logger.info(f"Applying log entry {self.last_applied}: {entry['command_type']}")

            # Mark as applied in database
            await db.execute(
                """
                UPDATE consensus_log_entries
                SET applied = true, applied_at = NOW()
                WHERE consensus_group_id = $1 AND term = $2 AND index = $3
                """,
                self.consensus_group_id,
                entry["term"],
                entry["index"]
            )

            entry["applied"] = True

    # ===== Client API =====

    async def propose_command(self, command_type: str, command_data: Dict[str, Any]) -> str:
        """
        Propose a new command for consensus (client API).

        Args:
            command_type: Type of command
            command_data: Command data

        Returns:
            Command ID (log index)
        """
        if self.state != RaftState.LEADER:
            raise ValueError("Not leader")

        # Create log entry
        entry_index = len(self.log) + 1
        log_entry = {
            "term": self.current_term,
            "index": entry_index,
            "command_type": command_type,
            "command_data": command_data,
            "applied": False
        }

        # Append to local log
        self.log.append(log_entry)

        # Replicate to followers
        await self._replicate_log()

        # Return command ID
        return str(entry_index)

    async def _replicate_log(self) -> None:
        """Replicate log entries to followers."""
        if self.state != RaftState.LEADER:
            return

        # For each follower, send AppendEntries RPC
        # Simplified: just broadcast new entries
        new_entries = self.log[-1:] if self.log else []

        if new_entries:
            replication_message = {
                "rpc_type": "AppendEntries",
                "term": self.current_term,
                "leader_id": self.agent_id,
                "prev_log_index": len(self.log) - 1,
                "prev_log_term": self.log[-2]["term"] if len(self.log) > 1 else 0,
                "entries": new_entries,
                "leader_commit": self.commit_index,
                "timestamp": datetime.now().isoformat()
            }

            channel = f"swarm:{self.swarm_id}:consensus:{self.consensus_group_id}:rpc"
            await swarm_pubsub.publish(channel, replication_message)

    async def get_committed_commands(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get committed commands from log."""
        committed = []
        for entry in self.log:
            if entry["index"] <= self.commit_index:
                committed.append({
                    "index": entry["index"],
                    "term": entry["term"],
                    "command_type": entry["command_type"],
                    "command_data": entry["command_data"],
                    "applied": entry.get("applied", False)
                })
            if len(committed) >= limit:
                break
        return committed

    async def health_check(self) -> Dict[str, Any]:
        """Get node health status."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "state": self.state,
            "current_term": self.current_term,
            "commit_index": self.commit_index,
            "last_applied": self.last_applied,
            "log_length": len(self.log),
            "last_heartbeat": self.last_heartbeat_received.isoformat() if self.last_heartbeat_received else None,
            "running": self._running
        }


class RaftConsensus:
    """
    Manager for RAFT consensus groups within a swarm.

    Creates and manages RAFT nodes for agents participating in consensus.
    """

    def __init__(self, swarm_id: str):
        """
        Initialize consensus manager for a swarm.

        Args:
            swarm_id: Swarm ID
        """
        self.swarm_id = swarm_id
        self.nodes: Dict[str, RaftNode] = {}  # agent_id -> RaftNode
        self._running = False

    async def add_agent_to_consensus(self, agent_id: str, agent_name: str, consensus_group_id: str) -> RaftNode:
        """
        Add an agent to a consensus group.

        Args:
            agent_id: Agent ID
            agent_name: Agent name
            consensus_group_id: Consensus group ID

        Returns:
            RaftNode instance for the agent
        """
        # Create or get consensus group
        await self._ensure_consensus_group_exists(consensus_group_id)

        # Create RAFT node
        node = RaftNode(
            consensus_group_id=consensus_group_id,
            agent_id=agent_id,
            agent_name=agent_name,
            swarm_id=self.swarm_id
        )

        self.nodes[agent_id] = node

        # Initialize node
        await node.initialize()

        logger.info(f"Added agent {agent_name} to consensus group {consensus_group_id}")

        return node

    async def remove_agent_from_consensus(self, agent_id: str) -> None:
        """Remove agent from consensus group."""
        if agent_id in self.nodes:
            node = self.nodes[agent_id]
            await node.close()
            del self.nodes[agent_id]
            logger.info(f"Removed agent {agent_id} from consensus")

    async def _ensure_consensus_group_exists(self, consensus_group_id: str) -> None:
        """Ensure consensus group exists in database."""
        existing = await db.fetch_one(
            "SELECT id FROM consensus_groups WHERE id = $1",
            consensus_group_id
        )

        if not existing:
            # Create new consensus group
            await db.execute(
                """
                INSERT INTO consensus_groups
                (id, swarm_id, group_name, current_term, state)
                VALUES ($1, $2, $3, 0, 'follower')
                """,
                consensus_group_id,
                self.swarm_id,
                f"consensus_group_{consensus_group_id[:8]}"
            )
            logger.debug(f"Created consensus group {consensus_group_id}")

    async def close(self) -> None:
        """Close all nodes and cleanup."""
        self._running = False

        for node in self.nodes.values():
            await node.close()

        self.nodes.clear()
        logger.info(f"RAFT consensus manager closed for swarm {self.swarm_id}")