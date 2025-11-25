"""
LLM Response Parsers.

Provides pluggable parsers for extracting content from provider responses.

Available parsers:
- AzureResponseParser: Parse Azure OpenAI responses
- NoOpResponseParser: Return raw response (for debugging)

Usage:
    from core.llms.runtimes.parsers import ParserFactory
    
    # Get specific parser
    parser = ParserFactory.get_parser('azure')
"""

from .azure_response_parser import AzureResponseParser
from .noop_response_parser import NoOpResponseParser
from .parser_factory import ParserFactory

__all__ = [
    "AzureResponseParser",
    "NoOpResponseParser",
    "ParserFactory",
]

