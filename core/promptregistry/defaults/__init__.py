"""
Default prompts for the prompt registry.

This module provides default prompts for agents and other system components.
"""

import json
from pathlib import Path
from typing import Dict, Any, List

# Path to default prompts file
DEFAULT_PROMPTS_FILE = Path(__file__).parent / "agent_prompts.json"


def load_default_prompts() -> Dict[str, Any]:
    """
    Load default prompts from the JSON file.
    
    Returns:
        Dictionary containing all default prompts
    """
    with open(DEFAULT_PROMPTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_default_prompt_labels() -> List[str]:
    """
    Get list of all default prompt labels.
    
    Returns:
        List of prompt labels
    """
    data = load_default_prompts()
    return [p["label"] for p in data.get("prompts", [])]


async def initialize_default_prompts(registry: Any) -> None:
    """
    Initialize the registry with default prompts.
    
    Loads all default prompts from the JSON file and saves them
    to the registry if they don't already exist.
    
    Args:
        registry: IPromptRegistry instance to initialize
    """
    from ..spec.prompt_models import PromptMetadata
    from ..enum import PromptEnvironment, PromptType, PromptCategory
    
    data = load_default_prompts()
    
    for prompt_data in data.get("prompts", []):
        label = prompt_data["label"]
        
        # Check if already exists
        try:
            existing = await registry.list_prompts()
            if label in existing:
                continue
        except Exception:
            pass
        
        # Create each version
        for version_data in prompt_data.get("versions", []):
            metadata = PromptMetadata(
                version=version_data.get("version", "1.0.0"),
                model_target=version_data.get("model_target", "default"),
                environment=PromptEnvironment(version_data.get("environment", "prod")),
                prompt_type=PromptType(version_data.get("prompt_type", "system")),
                category=PromptCategory(prompt_data.get("category", "system")),
                tags=prompt_data.get("tags", []),
                description=prompt_data.get("description", ""),
                response_format=version_data.get("response_format"),
            )
            
            # Handle nested metadata
            version_metadata = version_data.get("metadata", {})
            if version_metadata.get("llm_eval_score") is not None:
                metadata.llm_eval_score = version_metadata["llm_eval_score"]
            if version_metadata.get("human_eval_score") is not None:
                metadata.human_eval_score = version_metadata["human_eval_score"]
            
            await registry.save_prompt(
                label=label,
                content=version_data["content"],
                metadata=metadata
            )


__all__ = [
    "load_default_prompts",
    "get_default_prompt_labels",
    "initialize_default_prompts",
    "DEFAULT_PROMPTS_FILE",
]

