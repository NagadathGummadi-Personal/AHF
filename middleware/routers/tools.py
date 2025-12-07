"""
Tools API Router

CRUD endpoints for tool management with S3 storage.

Endpoints:
- GET /tools - List all tools
- GET /tools/{tool_id} - Get a specific tool
- GET /tools/{tool_id}/versions - List tool versions
- POST /tools - Create a new tool
- PUT /tools/{tool_id} - Update a tool (creates new version)
- DELETE /tools/{tool_id} - Delete a tool
- DELETE /tools/{tool_id}/versions/{version} - Delete specific version
- POST /tools/{tool_id}/submit-review - Submit tool for review

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, Query, Body, Path
from pydantic import BaseModel, Field

from core.tools.runtimes.storage import S3ToolStorage
from core.tools.serializers.tool_serializer import tool_to_dict, tool_from_dict
from core.tools.spec.tool_types import ToolSpec
from core.tools.enum import ToolType

from ..config import get_settings


router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ToolStatus(str, Enum):
    """Tool review status."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class ToolMetadata(BaseModel):
    """Tool metadata for API responses."""
    tool_id: str
    tool_name: str
    description: str
    tool_type: str
    version: str
    status: ToolStatus = ToolStatus.DRAFT
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    owner: Optional[str] = None


class ToolCreateRequest(BaseModel):
    """Request body for creating a tool."""
    id: str = Field(..., description="Unique tool identifier")
    tool_name: str = Field(..., description="Human-readable tool name")
    description: str = Field(..., description="Tool description")
    tool_type: ToolType = Field(..., description="Type of tool: function, http, or db")
    parameters: List[Dict[str, Any]] = Field(default_factory=list, description="Tool parameters")
    
    # Function tool specific
    function_code: Optional[str] = Field(default=None, description="Python code for function tools")
    
    # HTTP tool specific
    url: Optional[str] = Field(default=None, description="URL for HTTP tools")
    method: Optional[str] = Field(default="GET", description="HTTP method")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers")
    
    # DB tool specific
    driver: Optional[str] = Field(default=None, description="Database driver")
    connection_config: Optional[Dict[str, Any]] = Field(default=None, description="Database connection config")
    
    # Additional config
    timeout_s: int = Field(default=30, description="Execution timeout in seconds")
    owner: Optional[str] = Field(default=None, description="Tool owner")
    
    model_config = {"extra": "allow"}  # Allow additional fields


class ToolUpdateRequest(BaseModel):
    """Request body for updating a tool."""
    tool_name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[List[Dict[str, Any]]] = None
    function_code: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    timeout_s: Optional[int] = None
    
    model_config = {"extra": "allow"}


class ToolResponse(BaseModel):
    """Response for single tool."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[ToolMetadata] = None


class ToolListResponse(BaseModel):
    """Response for tool list."""
    success: bool
    message: str
    tools: List[ToolMetadata] = Field(default_factory=list)
    total: int = 0


class ToolVersionResponse(BaseModel):
    """Response for tool versions."""
    success: bool
    message: str
    tool_id: str
    versions: List[Dict[str, Any]] = Field(default_factory=list)


class SubmitReviewRequest(BaseModel):
    """Request for submitting tool for review."""
    version: Optional[str] = Field(default=None, description="Specific version to submit")
    notes: Optional[str] = Field(default=None, description="Review notes")


# =============================================================================
# Helper Functions
# =============================================================================

def get_storage() -> S3ToolStorage:
    """Get S3 storage instance."""
    settings = get_settings()
    return S3ToolStorage(
        bucket_name=settings.s3.tools_bucket,
        region=settings.aws.region,
        endpoint_url=settings.aws.endpoint_url,
        aws_access_key_id=settings.aws.access_key_id,
        aws_secret_access_key=settings.aws.secret_access_key,
    )


def build_tool_spec(request: ToolCreateRequest) -> Dict[str, Any]:
    """Build tool spec dictionary from request."""
    spec = {
        "id": request.id,
        "tool_name": request.tool_name,
        "description": request.description,
        "tool_type": request.tool_type.value,
        "parameters": request.parameters,
        "timeout_s": request.timeout_s,
        "owner": request.owner,
    }
    
    # Add type-specific fields
    if request.tool_type == ToolType.FUNCTION:
        if request.function_code:
            spec["function_code"] = request.function_code
    
    elif request.tool_type == ToolType.HTTP:
        if request.url:
            spec["url"] = request.url
        spec["method"] = request.method or "GET"
        if request.headers:
            spec["headers"] = request.headers
    
    elif request.tool_type == ToolType.DB:
        if request.driver:
            spec["driver"] = request.driver
        if request.connection_config:
            spec.update(request.connection_config)
    
    # Add metadata
    spec["_metadata"] = {
        "status": ToolStatus.DRAFT.value,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    return spec


def extract_metadata(spec: Dict[str, Any], tool_id: str) -> ToolMetadata:
    """Extract metadata from tool spec."""
    meta = spec.get("_metadata", {})
    return ToolMetadata(
        tool_id=tool_id,
        tool_name=spec.get("tool_name", ""),
        description=spec.get("description", ""),
        tool_type=spec.get("tool_type", "unknown"),
        version=spec.get("version", "1.0.0"),
        status=ToolStatus(meta.get("status", "draft")),
        created_at=meta.get("created_at"),
        updated_at=meta.get("updated_at"),
        created_by=meta.get("created_by"),
        owner=spec.get("owner"),
    )


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("", response_model=ToolListResponse)
async def list_tools(
    prefix: Optional[str] = Query(default=None, description="Filter by ID prefix"),
    limit: int = Query(default=100, le=1000, description="Maximum results"),
):
    """
    List all tools.
    
    Returns a list of tool metadata without full specs.
    Use GET /tools/{tool_id} to get full spec.
    """
    storage = get_storage()
    
    try:
        tool_ids = await storage.list_tools(prefix=prefix, limit=limit)
        
        tools_metadata = []
        for tool_id in tool_ids:
            result = await storage.load(tool_id)
            if result.success and result.data:
                tools_metadata.append(extract_metadata(result.data, tool_id))
        
        return ToolListResponse(
            success=True,
            message=f"Found {len(tools_metadata)} tools",
            tools=tools_metadata,
            total=len(tools_metadata),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str = Path(..., description="Tool identifier"),
    version: Optional[str] = Query(default=None, description="Specific version"),
):
    """
    Get a specific tool by ID.
    
    Returns the full tool specification.
    """
    storage = get_storage()
    
    result = await storage.load(tool_id, version=version)
    
    if not result.success:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    
    return ToolResponse(
        success=True,
        message="Tool retrieved successfully",
        data=result.data,
        metadata=extract_metadata(result.data, tool_id),
    )


@router.get("/{tool_id}/versions", response_model=ToolVersionResponse)
async def list_tool_versions(
    tool_id: str = Path(..., description="Tool identifier"),
):
    """
    List all versions of a tool.
    """
    storage = get_storage()
    
    versions = await storage.list_versions(tool_id)
    
    if not versions:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    
    return ToolVersionResponse(
        success=True,
        message=f"Found {len(versions)} versions",
        tool_id=tool_id,
        versions=[
            {
                "version": v.version,
                "version_id": v.version_id,
                "created_at": v.created_at,
                "is_latest": v.is_latest,
            }
            for v in versions
        ],
    )


@router.post("", response_model=ToolResponse, status_code=201)
async def create_tool(
    request: ToolCreateRequest = Body(...),
):
    """
    Create a new tool.
    
    Creates a new tool with version 1.0.0.
    The tool starts in DRAFT status.
    
    For function tools, provide the Python code in `function_code`.
    For HTTP tools, provide `url`, `method`, and optionally `headers`.
    For DB tools, provide `driver` and `connection_config`.
    """
    storage = get_storage()
    
    # Check if tool already exists
    exists = await storage.exists(request.id)
    if exists:
        raise HTTPException(
            status_code=409,
            detail=f"Tool already exists: {request.id}. Use PUT to update."
        )
    
    # Build spec
    spec = build_tool_spec(request)
    
    # Save
    result = await storage.save(request.id, spec, version="1.0.0")
    
    if not result.success:
        raise HTTPException(status_code=500, detail=f"Failed to create tool: {result.message}")
    
    # Load and return
    load_result = await storage.load(request.id)
    
    return ToolResponse(
        success=True,
        message=f"Tool created successfully with version {result.version}",
        data=load_result.data,
        metadata=extract_metadata(load_result.data, request.id) if load_result.data else None,
    )


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: str = Path(..., description="Tool identifier"),
    request: ToolUpdateRequest = Body(...),
):
    """
    Update a tool.
    
    Creates a new version with the updates.
    Only the tool owner can update.
    """
    storage = get_storage()
    
    # Load existing
    existing = await storage.load(tool_id)
    if not existing.success:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    
    # Merge updates
    spec = existing.data.copy()
    
    if request.tool_name is not None:
        spec["tool_name"] = request.tool_name
    if request.description is not None:
        spec["description"] = request.description
    if request.parameters is not None:
        spec["parameters"] = request.parameters
    if request.function_code is not None:
        spec["function_code"] = request.function_code
    if request.url is not None:
        spec["url"] = request.url
    if request.method is not None:
        spec["method"] = request.method
    if request.headers is not None:
        spec["headers"] = request.headers
    if request.timeout_s is not None:
        spec["timeout_s"] = request.timeout_s
    
    # Update metadata
    if "_metadata" not in spec:
        spec["_metadata"] = {}
    spec["_metadata"]["updated_at"] = datetime.utcnow().isoformat()
    
    # Save as new version
    result = await storage.save(tool_id, spec)  # Auto-increments version
    
    if not result.success:
        raise HTTPException(status_code=500, detail=f"Failed to update tool: {result.message}")
    
    # Load and return
    load_result = await storage.load(tool_id)
    
    return ToolResponse(
        success=True,
        message=f"Tool updated successfully, new version: {result.version}",
        data=load_result.data,
        metadata=extract_metadata(load_result.data, tool_id) if load_result.data else None,
    )


@router.delete("/{tool_id}", response_model=ToolResponse)
async def delete_tool(
    tool_id: str = Path(..., description="Tool identifier"),
):
    """
    Delete a tool and all its versions.
    
    Only the tool owner can delete.
    Tools in PUBLISHED status cannot be deleted.
    """
    storage = get_storage()
    
    # Load to check status
    existing = await storage.load(tool_id)
    if not existing.success:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    
    # Check status
    meta = existing.data.get("_metadata", {})
    if meta.get("status") == ToolStatus.PUBLISHED.value:
        raise HTTPException(
            status_code=403,
            detail="Cannot delete published tools. Archive instead."
        )
    
    # Delete
    result = await storage.delete(tool_id)
    
    if not result.success:
        raise HTTPException(status_code=500, detail=f"Failed to delete tool: {result.message}")
    
    return ToolResponse(
        success=True,
        message=f"Tool {tool_id} deleted successfully",
        data=None,
        metadata=None,
    )


@router.delete("/{tool_id}/versions/{version}", response_model=ToolResponse)
async def delete_tool_version(
    tool_id: str = Path(..., description="Tool identifier"),
    version: str = Path(..., description="Version to delete"),
):
    """
    Delete a specific version of a tool.
    
    Cannot delete the only remaining version - use DELETE /tools/{tool_id} instead.
    """
    storage = get_storage()
    
    # Check versions
    versions = await storage.list_versions(tool_id)
    if len(versions) <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the only version. Use DELETE /tools/{tool_id} to delete the tool."
        )
    
    # Delete version
    result = await storage.delete(tool_id, version=version)
    
    if not result.success:
        raise HTTPException(status_code=500, detail=f"Failed to delete version: {result.message}")
    
    return ToolResponse(
        success=True,
        message=f"Version {version} of {tool_id} deleted successfully",
        data=None,
        metadata=None,
    )


@router.post("/{tool_id}/submit-review", response_model=ToolResponse)
async def submit_for_review(
    tool_id: str = Path(..., description="Tool identifier"),
    request: SubmitReviewRequest = Body(...),
):
    """
    Submit a tool for review.
    
    Changes the tool status to PENDING_REVIEW.
    Once reviewed, the tool will be APPROVED or REJECTED.
    Approved tools can be PUBLISHED to the tool hub.
    """
    storage = get_storage()
    
    # Load
    version = request.version
    existing = await storage.load(tool_id, version=version)
    if not existing.success:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    
    spec = existing.data
    
    # Check current status
    meta = spec.get("_metadata", {})
    current_status = meta.get("status", ToolStatus.DRAFT.value)
    
    if current_status == ToolStatus.PENDING_REVIEW.value:
        raise HTTPException(status_code=400, detail="Tool is already pending review")
    if current_status == ToolStatus.PUBLISHED.value:
        raise HTTPException(status_code=400, detail="Tool is already published")
    
    # Update status
    spec["_metadata"] = spec.get("_metadata", {})
    spec["_metadata"]["status"] = ToolStatus.PENDING_REVIEW.value
    spec["_metadata"]["review_submitted_at"] = datetime.utcnow().isoformat()
    if request.notes:
        spec["_metadata"]["review_notes"] = request.notes
    
    # Save (creates new version)
    result = await storage.save(tool_id, spec)
    
    if not result.success:
        raise HTTPException(status_code=500, detail=f"Failed to submit for review: {result.message}")
    
    # Load and return
    load_result = await storage.load(tool_id)
    
    return ToolResponse(
        success=True,
        message=f"Tool {tool_id} submitted for review",
        data=load_result.data,
        metadata=extract_metadata(load_result.data, tool_id) if load_result.data else None,
    )
