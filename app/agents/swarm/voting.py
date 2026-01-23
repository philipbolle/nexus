"""
NEXUS Swarm Communication Layer - Voting Conflict Resolution

Advanced voting system for swarm conflict resolution with multiple voting strategies,
quorum enforcement, and automated decision execution.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
import uuid

from .pubsub import swarm_pubsub
from ...database import db

logger = logging.getLogger(__name__)


class VotingStrategy:
    """Voting strategy constants."""
    SIMPLE_MAJORITY = "simple_majority"  # >50% of votes
    SUPER_MAJORITY = "super_majority"    # >66% of votes
    WEIGHTED = "weighted"                # Weighted by agent contribution
    CONSENSUS = "consensus"              # 100% agreement (for critical decisions)


class VotingStatus:
    """Vote status constants."""
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    EXECUTED = "executed"
    EXPIRED = "expired"


class VotingSystem:
    """
    Advanced voting system for swarm conflict resolution.

    Manages vote lifecycle, calculates results, and executes decisions.
    """

    def __init__(self, swarm_id: str):
        """
        Initialize voting system for a swarm.

        Args:
            swarm_id: Swarm ID
        """
        self.swarm_id = swarm_id
        self._active_votes: Dict[str, Dict[str, Any]] = {}  # vote_id -> vote data
        self._vote_results: Dict[str, Dict[str, Any]] = {}  # vote_id -> results
        self._running = False
        self._expiry_checker_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize voting system and start background tasks."""
        self._running = True
        self._expiry_checker_task = asyncio.create_task(self._check_vote_expiry())

        logger.info(f"Voting system initialized for swarm {self.swarm_id}")

    async def close(self) -> None:
        """Close voting system and cleanup."""
        self._running = False

        if self._expiry_checker_task:
            self._expiry_checker_task.cancel()
            try:
                await self._expiry_checker_task
            except asyncio.CancelledError:
                pass

        logger.info(f"Voting system closed for swarm {self.swarm_id}")

    # ===== Vote Creation =====

    async def create_vote(
        self,
        vote_type: str,
        subject: str,
        description: str,
        options: List[str],
        created_by_agent_id: str,
        voting_strategy: str = VotingStrategy.SIMPLE_MAJORITY,
        required_quorum: float = 0.51,
        expires_in_hours: int = 24,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new vote.

        Args:
            vote_type: Type of vote ('leader_election', 'task_assignment', 'conflict_resolution', 'config_change')
            subject: What is being voted on
            description: Detailed description
            options: List of vote options
            created_by_agent_id: ID of agent creating the vote
            voting_strategy: Voting strategy
            required_quorum: Minimum participation (0.0-1.0)
            expires_in_hours: Hours until vote expires
            metadata: Additional metadata

        Returns:
            Vote ID
        """
        vote_id = str(uuid.uuid4())
        now = datetime.now()
        expires_at = now + timedelta(hours=expires_in_hours) if expires_in_hours > 0 else None

        # Validate voting strategy
        if voting_strategy not in [VotingStrategy.SIMPLE_MAJORITY,
                                   VotingStrategy.SUPER_MAJORITY,
                                   VotingStrategy.WEIGHTED,
                                   VotingStrategy.CONSENSUS]:
            raise ValueError(f"Invalid voting strategy: {voting_strategy}")

        # Validate quorum
        if not 0.0 <= required_quorum <= 1.0:
            raise ValueError("Required quorum must be between 0.0 and 1.0")

        # Create vote record
        vote_data = {
            "id": vote_id,
            "swarm_id": self.swarm_id,
            "vote_type": vote_type,
            "subject": subject,
            "description": description,
            "options": options,
            "voting_strategy": voting_strategy,
            "required_quorum": required_quorum,
            "status": VotingStatus.OPEN,
            "created_by_agent_id": created_by_agent_id,
            "created_at": now,
            "expires_at": expires_at,
            "metadata": metadata or {},
            "total_voters": 0,
            "votes_received": 0,
            "option_counts": {option: 0 for option in options},
            "weighted_counts": {option: 0.0 for option in options}
        }

        # Store in database
        await db.execute(
            """
            INSERT INTO votes
            (id, swarm_id, consensus_group_id, vote_type, subject, description,
             options, voting_strategy, required_quorum, status, created_by_agent_id,
             created_at, expires_at, metadata)
            VALUES ($1, $2, NULL, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
            vote_id,
            self.swarm_id,
            vote_type,
            subject,
            description,
            json.dumps(options),
            voting_strategy,
            required_quorum,
            VotingStatus.OPEN,
            created_by_agent_id,
            now,
            expires_at,
            json.dumps(metadata or {})
        )

        # Cache in memory
        self._active_votes[vote_id] = vote_data

        logger.info(f"Created vote {vote_id}: {subject} (strategy: {voting_strategy})")

        # Announce vote creation
        await self._announce_vote_created(vote_data)

        return vote_id

    async def _announce_vote_created(self, vote_data: Dict[str, Any]) -> None:
        """Announce new vote to swarm."""
        announcement = {
            "event_type": "vote_created",
            "vote_id": vote_data["id"],
            "subject": vote_data["subject"],
            "description": vote_data["description"],
            "options": vote_data["options"],
            "voting_strategy": vote_data["voting_strategy"],
            "required_quorum": vote_data["required_quorum"],
            "created_by": vote_data["created_by_agent_id"],
            "expires_at": vote_data["expires_at"].isoformat() if vote_data["expires_at"] else None
        }

        channel = f"swarm:{self.swarm_id}:votes"
        await swarm_pubsub.publish(channel, announcement)

    # ===== Vote Participation =====

    async def cast_vote(
        self,
        vote_id: str,
        agent_id: str,
        option: str,
        confidence: float = 1.0,
        rationale: str = "",
        vote_weight: float = 1.0
    ) -> Dict[str, Any]:
        """
        Cast a vote in an open vote.

        Args:
            vote_id: ID of vote to participate in
            agent_id: ID of voting agent
            option: Selected option
            confidence: Confidence in vote (0.0-1.0)
            rationale: Explanation for vote
            vote_weight: Weight of agent's vote (default 1.0)

        Returns:
            Vote confirmation with updated vote status
        """
        # Get vote data
        vote_data = await self._get_vote_data(vote_id)
        if not vote_data:
            raise ValueError(f"Vote {vote_id} not found")

        # Check if vote is open
        if vote_data["status"] != VotingStatus.OPEN:
            raise ValueError(f"Vote {vote_id} is not open (status: {vote_data['status']})")

        # Validate option
        if option not in vote_data["options"]:
            raise ValueError(f"Invalid option '{option}'. Valid options: {vote_data['options']}")

        # Check if agent has already voted
        existing_vote = await db.fetch_one(
            "SELECT id FROM vote_responses WHERE vote_id = $1 AND agent_id = $2",
            vote_id, agent_id
        )

        if existing_vote:
            # Update existing vote
            await db.execute(
                """
                UPDATE vote_responses SET
                    option_selected = $1,
                    confidence_score = $2,
                    rationale = $3,
                    voted_at = NOW(),
                    metadata = jsonb_set(metadata, '{vote_weight}', $4::jsonb)
                WHERE vote_id = $5 AND agent_id = $6
                """,
                option,
                confidence,
                rationale,
                json.dumps(vote_weight),
                vote_id,
                agent_id
            )
        else:
            # Create new vote response
            await db.execute(
                """
                INSERT INTO vote_responses
                (id, vote_id, agent_id, swarm_id, option_selected,
                 confidence_score, rationale, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                str(uuid.uuid4()),
                vote_id,
                agent_id,
                self.swarm_id,
                option,
                confidence,
                rationale,
                json.dumps({"vote_weight": vote_weight})
            )

        # Update vote counts
        await self._update_vote_counts(vote_id)

        # Announce vote cast
        await self._announce_vote_cast(vote_id, agent_id, option, confidence)

        # Check if vote can be closed
        vote_result = await self._calculate_vote_result(vote_id)
        if vote_result["can_close"]:
            await self._close_vote(vote_id, vote_result)

        logger.info(f"Agent {agent_id} cast vote for option '{option}' in vote {vote_id}")

        return {
            "vote_id": vote_id,
            "option": option,
            "confidence": confidence,
            "vote_weight": vote_weight,
            "voted_at": datetime.now().isoformat(),
            "vote_status": vote_data["status"]
        }

    async def _update_vote_counts(self, vote_id: str) -> None:
        """Update vote counts in memory and database."""
        # Get vote responses
        responses = await db.fetch_all(
            """
            SELECT option_selected, confidence_score, metadata
            FROM vote_responses
            WHERE vote_id = $1
            """,
            vote_id
        )

        # Get total number of agents in swarm (eligible voters)
        total_agents = await db.fetch_one(
            """
            SELECT COUNT(*) as count FROM swarm_memberships
            WHERE swarm_id = $1 AND status = 'active'
            """,
            self.swarm_id
        )

        total_voters = total_agents["count"] if total_agents else 0
        votes_received = len(responses)

        # Count options
        option_counts = {}
        weighted_counts = {}

        # Initialize with zero
        vote_data = await self._get_vote_data(vote_id)
        if not vote_data:
            return

        for option in vote_data["options"]:
            option_counts[option] = 0
            weighted_counts[option] = 0.0

        # Calculate counts
        for response in responses:
            option = response["option_selected"]
            confidence = response["confidence_score"]
            metadata = json.loads(response["metadata"]) if response["metadata"] else {}
            weight = metadata.get("vote_weight", 1.0)

            # Convert weight and confidence to float (handles Decimal from JSON numeric and DB numeric)
            weight_float = float(weight)
            confidence_float = float(confidence)

            option_counts[option] += 1
            weighted_counts[option] += weight_float * confidence_float

        # Update database
        await db.execute(
            """
            UPDATE votes SET
                total_voters = $2,
                votes_received = $3,
                option_counts = $4,
                weighted_counts = $5,
                updated_at = NOW()
            WHERE id = $1
            """,
            vote_id,
            total_voters,
            votes_received,
            json.dumps(option_counts),
            json.dumps(weighted_counts)
        )

        # Update memory cache
        if vote_id in self._active_votes:
            self._active_votes[vote_id].update({
                "total_voters": total_voters,
                "votes_received": votes_received,
                "option_counts": option_counts,
                "weighted_counts": weighted_counts
            })

    async def _announce_vote_cast(self, vote_id: str, agent_id: str, option: str, confidence: float) -> None:
        """Announce vote cast to swarm."""
        announcement = {
            "event_type": "vote_cast",
            "vote_id": vote_id,
            "agent_id": agent_id,
            "option": option,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }

        channel = f"swarm:{self.swarm_id}:votes"
        await swarm_pubsub.publish(channel, announcement)

    # ===== Vote Result Calculation =====

    async def _calculate_vote_result(self, vote_id: str) -> Dict[str, Any]:
        """
        Calculate vote result and determine if vote can be closed.

        Returns:
            Result dictionary with winner, status, and can_close flag
        """
        vote_data = await self._get_vote_data(vote_id)
        if not vote_data:
            return {"can_close": False, "error": "Vote not found"}

        # Check if vote is already closed
        if vote_data["status"] != VotingStatus.OPEN:
            return {"can_close": False, "status": vote_data["status"]}

        # Check quorum
        participation_rate = vote_data["votes_received"] / vote_data["total_voters"] if vote_data["total_voters"] > 0 else 0
        quorum_met = participation_rate >= vote_data["required_quorum"]

        if not quorum_met:
            return {
                "can_close": False,
                "quorum_met": False,
                "participation_rate": participation_rate,
                "required_quorum": vote_data["required_quorum"]
            }

        # Calculate winner based on voting strategy
        winner = None
        winner_details = {}

        if vote_data["voting_strategy"] == VotingStrategy.SIMPLE_MAJORITY:
            winner = self._calculate_simple_majority(vote_data)
        elif vote_data["voting_strategy"] == VotingStrategy.SUPER_MAJORITY:
            winner = self._calculate_super_majority(vote_data)
        elif vote_data["voting_strategy"] == VotingStrategy.WEIGHTED:
            winner = self._calculate_weighted_majority(vote_data)
        elif vote_data["voting_strategy"] == VotingStrategy.CONSENSUS:
            winner = self._calculate_consensus(vote_data)

        if winner:
            winner_details = {
                "option": winner,
                "count": vote_data["option_counts"][winner],
                "weighted_score": vote_data["weighted_counts"].get(winner, 0)
            }

            return {
                "can_close": True,
                "quorum_met": True,
                "winner": winner,
                "winner_details": winner_details,
                "participation_rate": participation_rate,
                "vote_strategy": vote_data["voting_strategy"]
            }
        else:
            # No clear winner
            return {
                "can_close": False,
                "quorum_met": True,
                "no_winner": True,
                "participation_rate": participation_rate
            }

    def _calculate_simple_majority(self, vote_data: Dict[str, Any]) -> Optional[str]:
        """Calculate simple majority winner (>50% of votes)."""
        total_votes = vote_data["votes_received"]
        if total_votes == 0:
            return None

        for option, count in vote_data["option_counts"].items():
            if count > total_votes / 2:
                return option

        return None

    def _calculate_super_majority(self, vote_data: Dict[str, Any]) -> Optional[str]:
        """Calculate super majority winner (>66% of votes)."""
        total_votes = vote_data["votes_received"]
        if total_votes == 0:
            return None

        for option, count in vote_data["option_counts"].items():
            if count > total_votes * 2 / 3:  # >66.6%
                return option

        return None

    def _calculate_weighted_majority(self, vote_data: Dict[str, Any]) -> Optional[str]:
        """Calculate weighted majority winner (highest weighted score)."""
        if not vote_data["weighted_counts"]:
            return self._calculate_simple_majority(vote_data)

        # Find option with highest weighted score
        max_score = -1
        winner = None

        for option, score in vote_data["weighted_counts"].items():
            if score > max_score:
                max_score = score
                winner = option

        # Check if winner has majority of weighted votes
        total_weight = sum(vote_data["weighted_counts"].values())
        if total_weight > 0 and max_score > total_weight / 2:
            return winner

        return None

    def _calculate_consensus(self, vote_data: Dict[str, Any]) -> Optional[str]:
        """Calculate consensus winner (100% agreement)."""
        total_votes = vote_data["votes_received"]
        if total_votes == 0:
            return None

        # Check if all votes are for the same option
        non_zero_options = [opt for opt, count in vote_data["option_counts"].items() if count > 0]

        if len(non_zero_options) == 1:
            return non_zero_options[0]

        return None

    # ===== Vote Closing & Execution =====

    async def _close_vote(self, vote_id: str, result: Dict[str, Any]) -> None:
        """Close vote and execute decision."""
        now = datetime.now()

        # Update vote status
        await db.execute(
            """
            UPDATE votes SET
                status = $2,
                executed_at = $3,
                result = $4
            WHERE id = $1
            """,
            vote_id,
            VotingStatus.CLOSED,
            now,
            json.dumps(result)
        )

        # Update memory cache
        if vote_id in self._active_votes:
            self._active_votes[vote_id]["status"] = VotingStatus.CLOSED
            self._active_votes[vote_id]["result"] = result

        # Announce vote closed
        await self._announce_vote_closed(vote_id, result)

        # Execute decision
        await self._execute_vote_decision(vote_id, result)

        logger.info(f"Vote {vote_id} closed. Winner: {result.get('winner', 'none')}")

    async def _announce_vote_closed(self, vote_id: str, result: Dict[str, Any]) -> None:
        """Announce vote closure to swarm."""
        announcement = {
            "event_type": "vote_closed",
            "vote_id": vote_id,
            "winner": result.get("winner"),
            "winner_details": result.get("winner_details"),
            "participation_rate": result.get("participation_rate"),
            "quorum_met": result.get("quorum_met", False),
            "timestamp": datetime.now().isoformat()
        }

        channel = f"swarm:{self.swarm_id}:votes"
        await swarm_pubsub.publish(channel, announcement)

    async def _execute_vote_decision(self, vote_id: str, result: Dict[str, Any]) -> None:
        """Execute the decision from a closed vote."""
        vote_data = await self._get_vote_data(vote_id)
        if not vote_data or not result.get("winner"):
            return

        winner = result["winner"]
        vote_type = vote_data["vote_type"]
        subject = vote_data["subject"]

        # Different execution based on vote type
        if vote_type == "conflict_resolution":
            await self._execute_conflict_resolution(vote_data, winner)
        elif vote_type == "task_assignment":
            await self._execute_task_assignment(vote_data, winner)
        elif vote_type == "config_change":
            await self._execute_config_change(vote_data, winner)
        elif vote_type == "leader_election":
            await self._execute_leader_election(vote_data, winner)

        logger.info(f"Executed vote {vote_id} decision: {winner} for {subject}")

    async def _execute_conflict_resolution(self, vote_data: Dict[str, Any], winner: str) -> None:
        """Execute conflict resolution decision."""
        # Log the resolution
        await db.execute(
            """
            INSERT INTO conflict_resolutions
            (swarm_id, conflict_type, resolution, vote_id, resolved_by_agent_id, resolved_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            """,
            self.swarm_id,
            vote_data["subject"],
            winner,
            vote_data["id"],
            vote_data["created_by_agent_id"]
        )

        # Announce resolution
        announcement = {
            "event_type": "conflict_resolved",
            "conflict_type": vote_data["subject"],
            "resolution": winner,
            "vote_id": vote_data["id"],
            "timestamp": datetime.now().isoformat()
        }

        channel = f"swarm:{self.swarm_id}:events"
        await swarm_pubsub.publish(channel, announcement)

    async def _execute_task_assignment(self, vote_data: Dict[str, Any], winner: str) -> None:
        """Execute task assignment decision."""
        # In a real implementation, this would assign the task to the winner agent
        # For now, just log
        logger.info(f"Task '{vote_data['subject']}' assigned to option '{winner}'")

    async def _execute_config_change(self, vote_data: Dict[str, Any], winner: str) -> None:
        """Execute configuration change decision."""
        # Update swarm configuration based on winner
        logger.info(f"Swarm configuration '{vote_data['subject']}' changed to '{winner}'")

    async def _execute_leader_election(self, vote_data: Dict[str, Any], winner: str) -> None:
        """Execute leader election decision."""
        # Update swarm leader in database
        await db.execute(
            """
            UPDATE swarms SET
                metadata = jsonb_set(
                    metadata,
                    '{elected_leader}',
                    $2::jsonb
                )
            WHERE id = $1
            """,
            self.swarm_id,
            json.dumps({"agent_id": winner, "elected_at": datetime.now().isoformat()})
        )

        # Announce new leader
        announcement = {
            "event_type": "leader_elected_by_vote",
            "swarm_id": self.swarm_id,
            "leader_agent_id": winner,
            "vote_id": vote_data["id"],
            "timestamp": datetime.now().isoformat()
        }

        channel = f"swarm:{self.swarm_id}:events"
        await swarm_pubsub.publish(channel, announcement)

    # ===== Vote Management =====

    async def _check_vote_expiry(self) -> None:
        """Background task to check for expired votes."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute

                # Find expired votes
                expired_votes = await db.fetch_all(
                    """
                    SELECT id FROM votes
                    WHERE swarm_id = $1
                    AND status = 'open'
                    AND expires_at IS NOT NULL
                    AND expires_at < NOW()
                    """,
                    self.swarm_id
                )

                for row in expired_votes:
                    vote_id = row["id"]
                    await self._expire_vote(vote_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in vote expiry checker: {e}")
                await asyncio.sleep(10)

    async def _expire_vote(self, vote_id: str) -> None:
        """Expire a vote that has passed its expiry time."""
        await db.execute(
            "UPDATE votes SET status = 'expired' WHERE id = $1",
            vote_id
        )

        # Update memory cache
        if vote_id in self._active_votes:
            self._active_votes[vote_id]["status"] = VotingStatus.EXPIRED

        # Announce expiry
        announcement = {
            "event_type": "vote_expired",
            "vote_id": vote_id,
            "timestamp": datetime.now().isoformat()
        }

        channel = f"swarm:{self.swarm_id}:votes"
        await swarm_pubsub.publish(channel, announcement)

        logger.info(f"Vote {vote_id} expired")

    async def cancel_vote(self, vote_id: str, cancelled_by_agent_id: str, reason: str = "") -> None:
        """Cancel an open vote."""
        vote_data = await self._get_vote_data(vote_id)
        if not vote_data:
            raise ValueError(f"Vote {vote_id} not found")

        if vote_data["status"] != VotingStatus.OPEN:
            raise ValueError(f"Cannot cancel vote with status {vote_data['status']}")

        await db.execute(
            """
            UPDATE votes SET
                status = 'cancelled',
                result = jsonb_set(
                    COALESCE(result, '{}'::jsonb),
                    '{cancellation}',
                    $2::jsonb
                )
            WHERE id = $1
            """,
            vote_id,
            json.dumps({
                "cancelled_by": cancelled_by_agent_id,
                "reason": reason,
                "cancelled_at": datetime.now().isoformat()
            })
        )

        # Update memory cache
        if vote_id in self._active_votes:
            self._active_votes[vote_id]["status"] = VotingStatus.CANCELLED

        # Announce cancellation
        announcement = {
            "event_type": "vote_cancelled",
            "vote_id": vote_id,
            "cancelled_by": cancelled_by_agent_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }

        channel = f"swarm:{self.swarm_id}:votes"
        await swarm_pubsub.publish(channel, announcement)

        logger.info(f"Vote {vote_id} cancelled by {cancelled_by_agent_id}")

    # ===== Query Methods =====

    async def _get_vote_data(self, vote_id: str) -> Optional[Dict[str, Any]]:
        """Get vote data from cache or database."""
        # Check memory cache first
        if vote_id in self._active_votes:
            return self._active_votes[vote_id]

        # Load from database
        row = await db.fetch_one(
            """
            SELECT id, swarm_id, vote_type, subject, description, options,
                   voting_strategy, required_quorum, status, created_by_agent_id,
                   created_at, expires_at, metadata, total_voters, votes_received,
                   option_counts, weighted_counts, result
            FROM votes WHERE id = $1
            """,
            vote_id
        )

        if not row:
            return None

        vote_data = dict(row)
        vote_data["options"] = json.loads(vote_data["options"]) if isinstance(vote_data["options"], str) else vote_data["options"]
        vote_data["metadata"] = json.loads(vote_data["metadata"]) if isinstance(vote_data["metadata"], str) else vote_data["metadata"]
        vote_data["option_counts"] = json.loads(vote_data["option_counts"]) if isinstance(vote_data["option_counts"], str) else vote_data["option_counts"]
        vote_data["weighted_counts"] = json.loads(vote_data["weighted_counts"]) if isinstance(vote_data["weighted_counts"], str) else vote_data["weighted_counts"]
        vote_data["result"] = json.loads(vote_data["result"]) if isinstance(vote_data["result"], str) else vote_data["result"]

        # Cache in memory
        self._active_votes[vote_id] = vote_data

        return vote_data

    async def get_vote(self, vote_id: str) -> Optional[Dict[str, Any]]:
        """Get vote details."""
        return await self._get_vote_data(vote_id)

    async def get_active_votes(self) -> List[Dict[str, Any]]:
        """Get all active votes for this swarm."""
        rows = await db.fetch_all(
            """
            SELECT id, subject, description, vote_type, status, created_at, expires_at,
                   votes_received, total_voters
            FROM votes
            WHERE swarm_id = $1 AND status = 'open'
            ORDER BY created_at DESC
            """,
            self.swarm_id
        )
        return [dict(row) for row in rows]

    async def get_vote_results(self, vote_id: str) -> Dict[str, Any]:
        """Get detailed vote results."""
        vote_data = await self._get_vote_data(vote_id)
        if not vote_data:
            raise ValueError(f"Vote {vote_id} not found")

        # Get individual votes
        responses = await db.fetch_all(
            """
            SELECT agent_id, option_selected, confidence_score, rationale, voted_at
            FROM vote_responses
            WHERE vote_id = $1
            ORDER BY voted_at
            """,
            vote_id
        )

        result = {
            "vote": vote_data,
            "responses": [dict(r) for r in responses],
            "participation_rate": vote_data["votes_received"] / vote_data["total_voters"] if vote_data["total_voters"] > 0 else 0,
            "quorum_met": vote_data["votes_received"] >= vote_data["total_voters"] * vote_data["required_quorum"]
        }

        return result

    async def health_check(self) -> Dict[str, Any]:
        """Get voting system health status."""
        active_votes = await self.get_active_votes()

        return {
            "status": "healthy" if self._running else "stopped",
            "swarm_id": self.swarm_id,
            "active_votes_count": len(active_votes),
            "active_votes": [v["id"] for v in active_votes[:5]],  # First 5
            "memory_cache_size": len(self._active_votes)
        }