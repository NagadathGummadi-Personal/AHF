"""
Voice Agent Checkpointer

Uses DynamoDBCheckpointer from core.memory with voice agent defaults.

Version: 1.1.0
"""

from core.memory import (
    DynamoDBCheckpointer,
    create_dynamodb_checkpointer,
    DEFAULT_TTL_DAYS,
    MAX_TTL_DAYS,
)

from app.config import get_settings


# Re-export core checkpointer for convenience
VoiceAgentCheckpointer = DynamoDBCheckpointer


def create_voice_agent_checkpointer(
    session_id: str,
    ttl_days: int = DEFAULT_TTL_DAYS,
    use_local_fallback: bool = True,
    **kwargs,
) -> DynamoDBCheckpointer:
    """
    Create a checkpointer with voice agent defaults.
    
    Uses DynamoDBCheckpointer from core with:
    - TTL: 1 day by default (max 10 days)
    - Local fallback enabled for development
    - Settings from app config
    
    Args:
        session_id: Session identifier
        ttl_days: Checkpoint TTL in days (1-10, default 1)
        use_local_fallback: Fall back to local if DynamoDB unavailable
        **kwargs: Additional DynamoDBCheckpointer arguments
        
    Returns:
        Configured DynamoDBCheckpointer
    """
    settings = get_settings()
    
    return create_dynamodb_checkpointer(
        session_id=session_id,
        table_name=kwargs.pop("table_name", "ahf_workflow_checkpoints"),
        ttl_days=ttl_days,
        use_local_fallback=use_local_fallback,
        local_path=settings.checkpoint_storage_path,
        cache_max_size=settings.checkpoint_cache_max_size,
        **kwargs,
    )


__all__ = [
    "VoiceAgentCheckpointer",
    "DynamoDBCheckpointer",
    "create_voice_agent_checkpointer",
    "DEFAULT_TTL_DAYS",
    "MAX_TTL_DAYS",
]
