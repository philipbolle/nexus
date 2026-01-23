"""
NEXUS Swarm Communication Layer - API Endpoints

FastAPI endpoints for swarm management, communication, and coordination.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
import uuid
import json
import asyncpg
import logging
import traceback
from datetime import datetime

from ..database import db
from ..models.schemas import (
    SwarmCreate, SwarmUpdate, SwarmResponse,
    SwarmMembershipCreate, SwarmMembershipResponse,
    ConsensusGroupCreate, ConsensusGroupResponse,
    VoteCreate, VoteResponse, VoteCast,
    SwarmMessageSend, SwarmMessageResponse,
    SwarmEventQuery, SwarmEventResponse
)

router = APIRouter(prefix="/swarm", tags=["swarm"])


# ===== Swarm Management =====

@router.post("/", response_model=SwarmResponse)
async def create_swarm(swarm: SwarmCreate):
    """
    Create a new swarm.
    """
    swarm_id = str(uuid.uuid4())
    logger = logging.getLogger(__name__)

    try:
        await db.execute(
            """
            INSERT INTO swarms
            (id, name, description, purpose, swarm_type, max_members, auto_scaling, health_check_interval_seconds, is_active, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            swarm_id,
            swarm.name,
            swarm.description,
            swarm.purpose,
            swarm.swarm_type,
            swarm.max_members,
            swarm.auto_scaling,
            swarm.health_check_interval_seconds,
            True,
            json.dumps(swarm.metadata or {})
        )
    except Exception as e:
        logger.error(f"Failed to create swarm: {e}", exc_info=True)
        raise

    # Return created swarm
    row = await db.fetch_one(
        "SELECT * FROM swarms WHERE id = $1",
        swarm_id
    )

    data = dict(row)
    if isinstance(data.get('metadata'), str):
        try:
            data['metadata'] = json.loads(data['metadata'])
        except json.JSONDecodeError:
            data['metadata'] = {}
    return data


@router.get("/", response_model=List[SwarmResponse])
async def list_swarms(
    active_only: bool = True,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return")
):
    """
    List all swarms.
    """
    query = "SELECT * FROM swarms"
    params = []
    if active_only:
        query += " WHERE is_active = true"
    query += " ORDER BY created_at DESC LIMIT $1 OFFSET $2"
    params = [limit, skip]

    rows = await db.fetch_all(query, *params)
    result = []
    for row in rows:
        data = dict(row)
        metadata = data.get("metadata")
        
        if metadata is None:
            data["metadata"] = {}
        elif isinstance(metadata, str):
            try:
                data["metadata"] = json.loads(metadata)
            except json.JSONDecodeError:
                data["metadata"] = {}
        elif not isinstance(metadata, dict):
            # If it's not a dict or string, make it an empty dict
            data["metadata"] = {}
        
        result.append(data)
    return result


@router.get("/{swarm_id}", response_model=SwarmResponse)
async def get_swarm(swarm_id: uuid.UUID):
    """
    Get swarm details.
    """
    row = await db.fetch_one(
        "SELECT * FROM swarms WHERE id = $1",
        str(swarm_id)
    )

    if not row:
        raise HTTPException(status_code=404, detail="Swarm not found")

    data = dict(row)
    if isinstance(data.get('metadata'), str):
        try:
            data['metadata'] = json.loads(data['metadata'])
        except json.JSONDecodeError:
            data['metadata'] = {}
    return data


@router.put("/{swarm_id}", response_model=SwarmResponse)
async def update_swarm(swarm_id: uuid.UUID, swarm: SwarmUpdate):
    """
    Update swarm configuration.
    """
    logger = logging.getLogger(__name__)
    # Check if swarm exists
    existing = await db.fetch_one(
        "SELECT id FROM swarms WHERE id = $1",
        str(swarm_id)
    )

    if not existing:
        raise HTTPException(status_code=404, detail="Swarm not found")

    # Build update query dynamically
    updates = []
    params = []
    param_count = 0

    if swarm.name is not None:
        param_count += 1
        updates.append(f"name = ${param_count}")
        params.append(swarm.name)

    if swarm.description is not None:
        param_count += 1
        updates.append(f"description = ${param_count}")
        params.append(swarm.description)

    if swarm.purpose is not None:
        param_count += 1
        updates.append(f"purpose = ${param_count}")
        params.append(swarm.purpose)

    if swarm.swarm_type is not None:
        param_count += 1
        updates.append(f"swarm_type = ${param_count}")
        params.append(swarm.swarm_type)


    if swarm.max_members is not None:
        param_count += 1
        updates.append(f"max_members = ${param_count}")
        params.append(swarm.max_members)

    if swarm.auto_scaling is not None:
        param_count += 1
        updates.append(f"auto_scaling = ${param_count}")
        params.append(swarm.auto_scaling)

    if swarm.health_check_interval_seconds is not None:
        param_count += 1
        updates.append(f"health_check_interval_seconds = ${param_count}")
        params.append(swarm.health_check_interval_seconds)


    if swarm.is_active is not None:
        param_count += 1
        updates.append(f"is_active = ${param_count}")
        params.append(swarm.is_active)

    if swarm.metadata is not None:
        param_count += 1
        updates.append(f"metadata = ${param_count}")
        params.append(json.dumps(swarm.metadata or {}))

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = NOW()")
    param_count += 1
    params.append(str(swarm_id))

    query = f"UPDATE swarms SET {', '.join(updates)} WHERE id = ${param_count}"

    try:
        await db.execute(query, *params)
    except Exception as e:
        logger.error(f"Failed to update swarm {swarm_id}: {e}")
        logger.error(f"Query: {query}")
        logger.error(f"Params: {params}")
        raise

    # Return updated swarm
    row = await db.fetch_one(
        "SELECT * FROM swarms WHERE id = $1",
        str(swarm_id)
    )

    data = dict(row)
    metadata = data.get("metadata")

    if metadata is None:
        data["metadata"] = {}
    elif isinstance(metadata, str):
        try:
            data["metadata"] = json.loads(metadata)
        except json.JSONDecodeError:
            data["metadata"] = {}
    elif not isinstance(metadata, dict):
        # If it's not a dict or string, make it an empty dict
        data["metadata"] = {}

    return data


@router.delete("/{swarm_id}")
async def delete_swarm(swarm_id: uuid.UUID):
    """
    Delete a swarm (soft delete).
    """
    await db.execute(
        "UPDATE swarms SET is_active = false, updated_at = NOW() WHERE id = $1",
        str(swarm_id)
    )

    return {"message": "Swarm deactivated"}


# ===== Swarm Membership Management =====

@router.post("/{swarm_id}/members", response_model=SwarmMembershipResponse)
async def add_member(swarm_id: uuid.UUID, membership: SwarmMembershipCreate):
    """
    Add an agent to a swarm.
    """
    try:
        logger = logging.getLogger(__name__)
        logger.info(f"Adding agent {membership.agent_id} to swarm {swarm_id}")
        # Check if swarm exists and is active
        swarm = await db.fetch_one(
            "SELECT id, max_members FROM swarms WHERE id = $1 AND is_active = true",
            str(swarm_id)
        )

        if not swarm:
            raise HTTPException(status_code=404, detail="Swarm not found or inactive")

        # Check if agent exists
        agent = await db.fetch_one(
            "SELECT id FROM agents WHERE id = $1",
            membership.agent_id
        )

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Check if already a member
        existing = await db.fetch_one(
            "SELECT id FROM swarm_memberships WHERE swarm_id = $1 AND agent_id = $2",
            str(swarm_id), membership.agent_id
        )

        if existing:
            # Update existing membership
            if membership.vote_weight is not None:
                await db.execute(
                    """
                    UPDATE swarm_memberships SET
                        role = $1,
                        status = 'active',
                        last_seen_at = NOW(),
                        vote_weight = $2,
                        metadata = $3
                    WHERE id = $4
                    """,
                    membership.role,
                    membership.vote_weight,
                    json.dumps(membership.metadata or {}),
                    existing["id"]
                )
            else:
                await db.execute(
                    """
                    UPDATE swarm_memberships SET
                        role = $1,
                        status = 'active',
                        last_seen_at = NOW(),
                        metadata = $2
                    WHERE id = $3
                    """,
                    membership.role,
                    json.dumps(membership.metadata or {}),
                    existing["id"]
                )
        else:
            # Check max members
            member_count = await db.fetch_one(
                "SELECT COUNT(*) as count FROM swarm_memberships WHERE swarm_id = $1 AND status = 'active'",
                str(swarm_id)
            )

            if member_count["count"] >= swarm["max_members"]:
                raise HTTPException(status_code=400, detail="Swarm has reached maximum members")

            # Create new membership
            vote_weight = membership.vote_weight if membership.vote_weight is not None else 1.0
            await db.execute(
                """
                INSERT INTO swarm_memberships
                (swarm_id, agent_id, role, status, contribution_score, vote_weight, metadata)
                VALUES ($1, $2, $3, 'active', 0.0, $4, $5)
                """,
                swarm_id,
                membership.agent_id,
                membership.role,
                vote_weight,
                json.dumps(membership.metadata or {})
            )

        # Return membership details
        row = await db.fetch_one(
            """
            SELECT sm.*, a.name as agent_name, a.agent_type
            FROM swarm_memberships sm
            JOIN agents a ON sm.agent_id = a.id
            WHERE sm.swarm_id = $1 AND sm.agent_id = $2
            """,
            str(swarm_id), membership.agent_id
        )

        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        error_logger = logging.getLogger(__name__)
        error_logger.error(f"Error adding agent to swarm: {e}")
        error_logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{swarm_id}/members", response_model=List[SwarmMembershipResponse])
async def list_members(
    swarm_id: uuid.UUID,
    status: Optional[str] = "active",
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return")
):
    """
    List swarm members.
    """
    query = """
        SELECT sm.*, a.name as agent_name, a.agent_type
        FROM swarm_memberships sm
        JOIN agents a ON sm.agent_id = a.id
        WHERE sm.swarm_id = $1
    """

    params = [str(swarm_id)]
    param_index = 2
    if status:
        query += f" AND sm.status = ${param_index}"
        params.append(status)
        param_index += 1

    query += f" ORDER BY sm.role, sm.contribution_score DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
    params.extend([limit, skip])

    rows = await db.fetch_all(query, *params)
    return [dict(row) for row in rows]


@router.delete("/{swarm_id}/members/{agent_id}")
async def remove_member(swarm_id: uuid.UUID, agent_id: uuid.UUID):
    """
    Remove an agent from a swarm.
    """
    await db.execute(
        "UPDATE swarm_memberships SET status = 'inactive', last_seen_at = NOW() WHERE swarm_id = $1 AND agent_id = $2",
        str(swarm_id), str(agent_id)
    )

    return {"message": "Member removed"}


# ===== Consensus Group Management =====

# DISABLED: @router.post("/{swarm_id}/consensus-groups", response_model=ConsensusGroupResponse)
async def create_consensus_group(swarm_id: str, group: ConsensusGroupCreate):
    """
    Create a consensus group within a swarm.
    """
    group_id = str(uuid.uuid4())

    await db.execute(
        """
        INSERT INTO consensus_groups
        (id, swarm_id, group_name, current_term, voted_for, commit_index,
         last_applied_index, leader_id, state)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        group_id,
        swarm_id,
        group.group_name,
        group.current_term or 0,
        group.voted_for,
        group.commit_index or 0,
        group.last_applied_index or 0,
        group.leader_id,
        group.state or "follower"
    )

    row = await db.fetch_one(
        "SELECT * FROM consensus_groups WHERE id = $1",
        group_id
    )

    return dict(row)


# DISABLED: @router.get("/{swarm_id}/consensus-groups", response_model=List[ConsensusGroupResponse])
async def list_consensus_groups(swarm_id: str):
    """
    List consensus groups in a swarm.
    """
    rows = await db.fetch_all(
        "SELECT * FROM consensus_groups WHERE swarm_id = $1 ORDER BY created_at",
        swarm_id
    )
    return [dict(row) for row in rows]


# ===== Voting Management =====

# DISABLED: @router.post("/{swarm_id}/votes", response_model=VoteResponse)
async def create_vote(swarm_id: str, vote: VoteCreate):
    """
    Create a new vote in a swarm.
    """
    vote_id = str(uuid.uuid4())

    await db.execute(
        """
        INSERT INTO votes
        (id, swarm_id, vote_type, subject, description, options, voting_strategy,
         required_quorum, status, created_by_agent_id, expires_at, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """,
        vote_id,
        swarm_id,
        vote.vote_type,
        vote.subject,
        vote.description,
        vote.options,
        vote.voting_strategy,
        vote.required_quorum,
        "open",
        vote.created_by_agent_id,
        vote.expires_at,
        json.dumps(vote.metadata or {})
    )

    row = await db.fetch_one(
        "SELECT * FROM votes WHERE id = $1",
        vote_id
    )

    return dict(row)


# DISABLED: @router.post("/{swarm_id}/votes/{vote_id}/cast", response_model=Dict[str, Any])
async def cast_vote(swarm_id: str, vote_id: str, vote_cast: VoteCast):
    """
    Cast a vote in a swarm vote.
    """
    # Check if vote exists and is open
    vote = await db.fetch_one(
        "SELECT id, options, status FROM votes WHERE id = $1 AND swarm_id = $2",
        vote_id, swarm_id
    )

    if not vote:
        raise HTTPException(status_code=404, detail="Vote not found")
    if vote["status"] != "open":
        raise HTTPException(status_code=400, detail="Vote is not open")

    # Validate option
    options = vote["options"]
    if vote_cast.option not in options:
        raise HTTPException(status_code=400, detail=f"Invalid option. Valid options: {options}")

    # Record vote
    await db.execute(
        """
        INSERT INTO vote_responses
        (id, vote_id, agent_id, swarm_id, option_selected, confidence_score, rationale, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (vote_id, agent_id) DO UPDATE SET
            option_selected = EXCLUDED.option_selected,
            confidence_score = EXCLUDED.confidence_score,
            rationale = EXCLUDED.rationale,
            voted_at = NOW()
        """,
        str(uuid.uuid4()),
        vote_id,
        vote_cast.agent_id,
        swarm_id,
        vote_cast.option,
        vote_cast.confidence,
        vote_cast.rationale,
        vote_cast.metadata or {}
    )

    return {"message": "Vote cast successfully", "vote_id": vote_id}


# DISABLED: @router.get("/{swarm_id}/votes", response_model=List[VoteResponse])
async def list_votes(
    swarm_id: str,
    status: Optional[str] = "open",
    skip: int = 0,
    limit: int = 100
):
    """
    List votes in a swarm.
    """
    query = "SELECT * FROM votes WHERE swarm_id = $1"
    params = [swarm_id]
    param_index = 2

    if status:
        query += f" AND status = ${param_index}"
        params.append(status)
        param_index += 1

    query += f" ORDER BY created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
    params.extend([limit, skip])

    rows = await db.fetch_all(query, *params)
    return [dict(row) for row in rows]


# ===== Swarm Messaging =====

@router.post("/{swarm_id}/messages")
async def send_swarm_message(swarm_id: str, message: SwarmMessageSend):
    """
    Send a message to a swarm (simulated - would use Redis Pub/Sub).
    """
    # In a real implementation, this would publish to Redis Pub/Sub
    # For now, just store in database
    message_id = str(uuid.uuid4())

    await db.execute(
        """
        INSERT INTO swarm_messages
        (id, swarm_id, sender_agent_id, recipient_agent_id, channel,
         message_type, content, priority, ttl_seconds, delivered)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
        message_id,
        swarm_id,
        message.sender_agent_id,
        message.recipient_agent_id,
        message.channel,
        message.message_type,
        message.content,
        message.priority,
        message.ttl_seconds,
        False  # Not delivered yet
    )

    return {"message_id": message_id, "status": "queued"}


@router.get("/{swarm_id}/messages", response_model=List[SwarmMessageResponse])
async def get_swarm_messages(
    swarm_id: str,
    channel: Optional[str] = None,
    delivered: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    Get swarm messages.
    """
    query = "SELECT * FROM swarm_messages WHERE swarm_id = $1"
    params = [swarm_id]

    if channel:
        params.append(channel)
        query += f" AND channel = ${len(params)}"

    if delivered is not None:
        params.append(delivered)
        query += f" AND delivered = ${len(params)}"

    query += f" ORDER BY created_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
    params.extend([limit, skip])

    rows = await db.fetch_all(query, *params)
    return [dict(row) for row in rows]


# ===== Swarm Events =====

# DISABLED: @router.get("/{swarm_id}/events", response_model=List[SwarmEventResponse])
async def get_swarm_events(
    swarm_id: str,
    event_type: Optional[str] = None,
    since: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    Get swarm events.
    """
    query = "SELECT * FROM swarm_events WHERE swarm_id = $1"
    params = [swarm_id]

    if event_type:
        params.append(event_type)
        query += f" AND event_type = ${len(params)}"

    if since:
        params.append(since)
        query += f" AND occurred_at >= ${len(params)}"

    query += f" ORDER BY occurred_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
    params.extend([limit, skip])

    rows = await db.fetch_all(query, *params)
    return [dict(row) for row in rows]


# ===== Swarm Health & Status =====

# DISABLED: @router.get("/{swarm_id}/health")
async def swarm_health(swarm_id: str):
    """
    Get swarm health status.
    """
    # Get swarm info
    swarm = await db.fetch_one(
        "SELECT name, purpose, swarm_type, is_active FROM swarms WHERE id = $1",
        swarm_id
    )

    if not swarm:
        raise HTTPException(status_code=404, detail="Swarm not found")

    # Get member count
    member_count = await db.fetch_one(
        "SELECT COUNT(*) as count FROM swarm_memberships WHERE swarm_id = $1 AND status = 'active'",
        swarm_id
    )

    # Get recent activity
    recent_messages = await db.fetch_one(
        "SELECT COUNT(*) as count FROM swarm_messages WHERE swarm_id = $1 AND created_at > NOW() - INTERVAL '1 hour'",
        swarm_id
    )

    # Get open votes
    open_votes = await db.fetch_one(
        "SELECT COUNT(*) as count FROM votes WHERE swarm_id = $1 AND status = 'open'",
        swarm_id
    )

    # Get consensus groups
    consensus_groups = await db.fetch_one(
        "SELECT COUNT(*) as count FROM consensus_groups WHERE swarm_id = $1",
        swarm_id
    )

    return {
        "swarm": {
            "id": swarm_id,
            "name": swarm["name"],
            "purpose": swarm["purpose"],
            "type": swarm["swarm_type"],
            "active": swarm["is_active"]
        },
        "members": {
            "active_count": member_count["count"] if member_count else 0
        },
        "activity": {
            "recent_messages": recent_messages["count"] if recent_messages else 0,
            "open_votes": open_votes["count"] if open_votes else 0,
            "consensus_groups": consensus_groups["count"] if consensus_groups else 0
        },
        "status": "healthy" if swarm["is_active"] else "inactive"
    }


# DISABLED: @router.get("/{swarm_id}/performance")
async def swarm_performance(swarm_id: str):
    """
    Get swarm performance metrics.
    """
    # Get latest performance metrics
    performance = await db.fetch_one(
        """
        SELECT total_messages, total_votes, consensus_decisions,
               conflicts_detected, conflicts_resolved, avg_decision_time_ms,
               message_delivery_success_rate, consensus_success_rate,
               member_activity_rate
        FROM swarm_performance
        WHERE swarm_id = $1
        ORDER BY date DESC
        LIMIT 1
        """,
        swarm_id
    )

    if not performance:
        # Return empty metrics
        return {
            "swarm_id": swarm_id,
            "metrics": {},
            "message": "No performance data available"
        }

    return {
        "swarm_id": swarm_id,
        "metrics": dict(performance)
    }


# ===== Swarm Initialization =====

# DISABLED: @router.post("/{swarm_id}/initialize")
async def initialize_swarm(swarm_id: str, background_tasks: BackgroundTasks):
    """
    Initialize swarm communication layer.
    """
    # In a real implementation, this would initialize Redis Pub/Sub connections
    # For now, just mark as initialized
    await db.execute(
        "UPDATE swarms SET metadata = jsonb_set(metadata, '{initialized}', 'true'::jsonb) WHERE id = $1",
        swarm_id
    )

    return {"message": "Swarm initialization requested", "swarm_id": swarm_id}