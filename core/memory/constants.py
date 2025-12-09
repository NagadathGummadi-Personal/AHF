"""
Constants for Memory Module.

This module defines all constants used throughout the Memory subsystem including
scratchpad, checklist, and other memory-related components.
"""

# ============================================================================
# SCRATCHPAD CONSTANTS
# ============================================================================

SCRATCHPAD_SEPARATOR = "\n---\n"
SCRATCHPAD_THOUGHT_PREFIX = "Thought: "
SCRATCHPAD_ACTION_PREFIX = "Action: "
SCRATCHPAD_OBSERVATION_PREFIX = "Observation: "

# ============================================================================
# REACT AGENT CONSTANTS (used by structured scratchpad)
# ============================================================================

REACT_THOUGHT = "thought"
REACT_ACTION = "action"
REACT_ACTION_INPUT = "action_input"
REACT_OBSERVATION = "observation"
REACT_FINAL_ANSWER = "final_answer"

# ============================================================================
# CHECKLIST STATUSES
# ============================================================================

CHECKLIST_STATUS_PENDING = "pending"
CHECKLIST_STATUS_IN_PROGRESS = "in_progress"
CHECKLIST_STATUS_COMPLETED = "completed"
CHECKLIST_STATUS_FAILED = "failed"
CHECKLIST_STATUS_SKIPPED = "skipped"

# ============================================================================
# ERROR MESSAGES
# ============================================================================

UNKNOWN_MEMORY_ERROR = "Unknown memory implementation: {MEMORY_NAME}. Available: {AVAILABLE_MEMORIES}"
UNKNOWN_SCRATCHPAD_ERROR = "Unknown scratchpad implementation: {SCRATCHPAD_NAME}. Available: {AVAILABLE_SCRATCHPADS}"
UNKNOWN_CHECKLIST_ERROR = "Unknown checklist implementation: {CHECKLIST_NAME}. Available: {AVAILABLE_CHECKLISTS}"
UNKNOWN_OBSERVER_ERROR = "Unknown observer implementation: {OBSERVER_NAME}. Available: {AVAILABLE_OBSERVERS}"

# ============================================================================
# CACHE CONSTANTS
# ============================================================================

NOOP = "noop"
COMMA = ","
SPACE = " "


