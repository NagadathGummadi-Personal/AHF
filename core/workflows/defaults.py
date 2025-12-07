"""
Workflow Module Default Values

Version: 1.0.0
"""

from .constants import (
    STATUS_DRAFT,
    NODE_TYPE_AGENT,
    EDGE_TYPE_DEFAULT,
    IO_TYPE_TEXT,
    FORMAT_PLAIN,
    PROMPT_PRECEDENCE_MERGE,
    PROMPT_MERGE_APPEND,
    BG_MODE_MONITOR,
    DEFAULT_WORKFLOWS_DIR,
    DEFAULT_NODES_DIR,
    DEFAULT_EDGES_DIR,
    FILE_EXT_JSON,
)

# =============================================================================
# VERSION DEFAULTS
# =============================================================================

DEFAULT_VERSION = "1.0.0"
DEFAULT_WORKFLOW_VERSION = "1.0.0"
DEFAULT_NODE_VERSION = "1.0.0"
DEFAULT_EDGE_VERSION = "1.0.0"

# =============================================================================
# STATUS DEFAULTS
# =============================================================================

DEFAULT_STATUS = STATUS_DRAFT
DEFAULT_NODE_STATUS = STATUS_DRAFT
DEFAULT_EDGE_STATUS = STATUS_DRAFT

# =============================================================================
# TYPE DEFAULTS
# =============================================================================

DEFAULT_NODE_TYPE = NODE_TYPE_AGENT
DEFAULT_EDGE_TYPE = EDGE_TYPE_DEFAULT

# =============================================================================
# IO DEFAULTS
# =============================================================================

DEFAULT_INPUT_TYPE = IO_TYPE_TEXT
DEFAULT_OUTPUT_TYPE = IO_TYPE_TEXT
DEFAULT_INPUT_FORMAT = FORMAT_PLAIN
DEFAULT_OUTPUT_FORMAT = FORMAT_PLAIN

# =============================================================================
# PROMPT DEFAULTS
# =============================================================================

DEFAULT_PROMPT_PRECEDENCE = PROMPT_PRECEDENCE_MERGE
DEFAULT_PROMPT_MERGE_STRATEGY = PROMPT_MERGE_APPEND
DEFAULT_SHOW_PROMPT_TO_USER = False
DEFAULT_ALLOW_USER_PROMPT = True

# =============================================================================
# BACKGROUND AGENT DEFAULTS
# =============================================================================

DEFAULT_BG_AGENT_MODE = BG_MODE_MONITOR
DEFAULT_BG_AGENT_ENABLED = False

# =============================================================================
# EXECUTION DEFAULTS
# =============================================================================

DEFAULT_TIMEOUT_S = 300  # 5 minutes
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY_S = 1.0

# =============================================================================
# STORAGE DEFAULTS
# =============================================================================

DEFAULT_STORAGE_PATH = DEFAULT_WORKFLOWS_DIR
DEFAULT_NODES_PATH = DEFAULT_NODES_DIR
DEFAULT_EDGES_PATH = DEFAULT_EDGES_DIR
DEFAULT_FILE_EXTENSION = FILE_EXT_JSON

# =============================================================================
# EDGE DEFAULTS
# =============================================================================

DEFAULT_EDGE_PRIORITY = 0
DEFAULT_EDGE_WEIGHT = 1.0

# =============================================================================
# DISPLAY DEFAULTS
# =============================================================================

DEFAULT_NODE_DISPLAY_NAME = "Untitled Node"
DEFAULT_NODE_DESCRIPTION = ""
DEFAULT_EDGE_DISPLAY_NAME = "Untitled Edge"

# =============================================================================
# VARIABLE ASSIGNMENT DEFAULTS
# =============================================================================

DEFAULT_VARIABLE_ASSIGNMENT_ENABLED = True
DEFAULT_ON_ERROR_BEHAVIOR = "log"  # "log", "raise", "ignore"
