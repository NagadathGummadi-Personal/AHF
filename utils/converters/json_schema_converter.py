"""
JSON Schema Converter for Structured LLM Outputs.

Converts Pydantic models to OpenAI JSON schema format and validates responses.
Supports partial JSON parsing for streaming outputs.
Also supports raw JSON dict output validation.
"""

import json
from typing import Dict, Any, Type, Optional, TypeVar, Union
from pydantic import BaseModel, ValidationError
from .partial_json_parser import parse_partial_json, parse_json_markdown, is_complete_json

T = TypeVar('T', bound=BaseModel)


def pydantic_to_openai_schema(
    model_class: Type[BaseModel],
    name: Optional[str] = None,
    description: Optional[str] = None,
    strict: bool = True
) -> Dict[str, Any]:
    """
    Convert Pydantic model to OpenAI structured output schema.
    
    OpenAI Format (for response_format parameter):
    {
        "type": "json_schema",
        "json_schema": {
            "name": "schema_name",
            "description": "Optional description",
            "schema": {...},  # JSON schema with additionalProperties: false
            "strict": true
        }
    }
    
    Args:
        model_class: Pydantic model class
        name: Schema name (defaults to model class name)
        description: Schema description (defaults to model docstring)
        strict: Whether to enforce strict schema validation
        
    Returns:
        OpenAI-compatible response_format dict
        
    Example:
        class CustomerResponse(BaseModel):
            responseText: str
            intent: str
            confidenceScore: float
        
        schema = pydantic_to_openai_schema(CustomerResponse)
        # Use in API call
        response = await llm.get_answer(
            messages,
            ctx,
            response_format=schema
        )
    """
    # Get Pydantic JSON schema
    pydantic_schema = model_class.model_json_schema()
    
    # Extract name and description
    schema_name = name or model_class.__name__
    schema_description = description or model_class.__doc__ or f"Schema for {schema_name}"
    
    # Add additionalProperties: false for strict mode compliance
    if strict:
        pydantic_schema["additionalProperties"] = False
        
        # Also add it to nested objects if present
        if "properties" in pydantic_schema:
            for prop_name, prop_schema in pydantic_schema["properties"].items():
                if isinstance(prop_schema, dict) and prop_schema.get("type") == "object":
                    prop_schema["additionalProperties"] = False
    
    # Build OpenAI format
    openai_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "description": schema_description.strip(),
            "schema": pydantic_schema,
            "strict": strict
        }
    }
    
    return openai_schema


def json_object_schema() -> Dict[str, Any]:
    """
    Get basic JSON object schema for raw JSON output.
    
    Returns:
        OpenAI-compatible response_format dict for JSON object
        
    Example:
        schema = json_object_schema()
        response = await llm.get_answer(
            messages,
            ctx,
            response_format=schema
        )
        # response.content will be a valid JSON object
    """
    return {"type": "json_object"}


def validate_json_response(
    response_content: str,
    model_class: Type[T],
    raise_on_error: bool = True
) -> Optional[T]:
    """
    Validate and parse JSON response against Pydantic model.
    
    Args:
        response_content: JSON string from LLM
        model_class: Pydantic model to validate against
        raise_on_error: Whether to raise on validation errors
        
    Returns:
        Validated Pydantic model instance, or None if validation fails and raise_on_error=False
        
    Raises:
        ValidationError: If response doesn't match schema and raise_on_error=True
        json.JSONDecodeError: If response is not valid JSON
        
    Example:
        response = await llm.get_answer(messages, ctx, response_format=schema)
        validated = validate_json_response(response.content, CustomerResponse)
        print(validated.responseText)
    """
    try:
        json_data = json.loads(response_content)
        return model_class(**json_data)
    except (json.JSONDecodeError, ValidationError):
        if raise_on_error:
            raise
        return None


def validate_json_dict(
    response_content: str,
    raise_on_error: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Validate and parse JSON response as a raw dictionary.
    
    Args:
        response_content: JSON string from LLM
        raise_on_error: Whether to raise on parse errors
        
    Returns:
        Parsed JSON dict, or None if parsing fails and raise_on_error=False
        
    Raises:
        json.JSONDecodeError: If response is not valid JSON and raise_on_error=True
        
    Example:
        response = await llm.get_answer(messages, ctx, response_format=json_object_schema())
        json_dict = validate_json_dict(response.content)
        print(json_dict["key"])
    """
    try:
        result = json.loads(response_content)
        if not isinstance(result, dict):
            if raise_on_error:
                raise ValueError(f"Expected JSON object, got {type(result).__name__}")
            return None
        return result
    except json.JSONDecodeError:
        if raise_on_error:
            raise
        return None


def parse_structured_response(
    response_content: str,
    model_class: Optional[Type[T]] = None,
    partial: bool = False
) -> Optional[Union[T, Dict[str, Any]]]:
    """
    Parse structured response with support for partial/incomplete JSON.
    
    Attempts to parse the response as JSON and validate against the schema.
    Handles markdown code blocks, embedded JSON, and partial JSON during streaming.
    
    If model_class is None, returns raw dict. Otherwise returns validated Pydantic model.
    
    Args:
        response_content: Response content from LLM (may be incomplete if streaming)
        model_class: Pydantic model to validate against (None for raw dict)
        partial: If True, attempts to parse incomplete JSON (for streaming)
        
    Returns:
        Validated Pydantic model instance, dict, or None if partial and not yet parseable
        
    Raises:
        ValidationError: If response cannot be validated (only when partial=False)
        json.JSONDecodeError: If JSON is malformed (only when partial=False)
        
    Example:
        # Complete JSON with Pydantic validation
        validated = parse_structured_response(response.content, CustomerResponse)
        
        # Complete JSON as raw dict
        json_dict = parse_structured_response(response.content)
        
        # Streaming (partial JSON)
        partial_obj = parse_structured_response(
            chunk_content,
            CustomerResponse,
            partial=True
        )
        if partial_obj:
            print(f"Partial data: {partial_obj}")
    """
    if not response_content or not response_content.strip():
        return None
    
    # Try parsing with markdown/code block extraction
    try:
        json_data = parse_json_markdown(response_content)
        
        # If no model class, return raw dict
        if model_class is None:
            return json_data if isinstance(json_data, dict) else None
        
        # Validate against Pydantic model
        try:
            return model_class(**json_data)
        except ValidationError:
            if not partial:
                raise
            return None
    
    except json.JSONDecodeError:
        if not partial:
            # Try partial JSON parsing as last resort
            json_data = parse_partial_json(response_content)
            if json_data:
                if model_class is None:
                    return json_data if isinstance(json_data, dict) else None
                try:
                    return model_class(**json_data)
                except ValidationError:
                    raise
            
            raise ValueError(
                f"Failed to parse response{' as ' + model_class.__name__ if model_class else ''}. "
                f"Content: {response_content[:200]}{'...' if len(response_content) > 200 else ''}"
            )
        else:
            # Partial mode - try to parse incomplete JSON
            json_data = parse_partial_json(response_content)
            if json_data:
                if model_class is None:
                    return json_data if isinstance(json_data, dict) else None
                try:
                    return model_class(**json_data)
                except ValidationError:
                    return None
            return None


def extract_json_from_text(text: str) -> Optional[str]:
    """
    Extract JSON from text that may contain additional content.
    
    Args:
        text: Text that may contain JSON
        
    Returns:
        Extracted JSON string, or None if not found
        
    Example:
        text = "The answer is: {\"key\": \"value\"} - hope this helps!"
        json_str = extract_json_from_text(text)
        # Returns: '{"key": "value"}'
    """
    # Try to find JSON object
    if "{" in text and "}" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        if end > start:
            return text[start:end]
    
    # Try to find JSON array
    if "[" in text and "]" in text:
        start = text.find("[")
        end = text.rfind("]") + 1
        if end > start:
            return text[start:end]
    
    return None


def is_valid_json(text: str) -> bool:
    """
    Check if text is valid JSON.
    
    Args:
        text: Text to check
        
    Returns:
        True if valid JSON
    """
    return is_complete_json(text)


def parse_streaming_json(
    accumulated_content: str,
    model_class: Optional[Type[T]] = None
) -> Optional[Union[T, Dict[str, Any]]]:
    """
    Parse JSON from accumulated streaming chunks.
    
    Designed for streaming scenarios where JSON is built up progressively.
    Returns None if JSON is incomplete, otherwise returns validated object.
    
    Args:
        accumulated_content: All chunks accumulated so far
        model_class: Pydantic model to validate against (None for raw dict)
        
    Returns:
        Validated model instance (or dict if no model_class) if JSON is parseable, None otherwise
        
    Example:
        accumulated = ""
        async for chunk in llm.stream_answer(messages, ctx, response_format=Schema):
            accumulated += chunk.content
            obj = parse_streaming_json(accumulated, Schema)
            if obj:
                print(f"Got complete object: {obj}")
                
        # For raw JSON dict:
        obj = parse_streaming_json(accumulated)  # Returns dict
    """
    return parse_structured_response(accumulated_content, model_class, partial=True)


def get_partial_json_fields(accumulated_content: str) -> list:
    """
    Get list of fields currently available in partial JSON.
    
    Args:
        accumulated_content: Accumulated streaming content
        
    Returns:
        List of field names parsed so far
    """
    json_data = parse_partial_json(accumulated_content)
    if json_data and isinstance(json_data, dict):
        return list(json_data.keys())
    return []
