"""
Response Parser Factory.

Provides a centralized way to create and register parsers by name.
"""

from typing import Dict
from ...interfaces.llm_interfaces import IResponseParser
from .azure_response_parser import AzureResponseParser
from .noop_response_parser import NoOpResponseParser


# Constants
AZURE = "azure"
NOOP = "noop"


class ParserFactory:
    """
    Factory for creating response parser instances.
    
    Built-in Parsers:
        - 'azure': AzureResponseParser - Azure OpenAI responses
        - 'noop': NoOpResponseParser - Raw response (debugging)
    
    Usage:
        # Get built-in parser
        parser = ParserFactory.get_parser('azure')
        
        # Register custom parser
        ParserFactory.register('my_custom', MyCustomParser())
    """
    
    _parsers: Dict[str, IResponseParser] = {
        AZURE: AzureResponseParser(),
        NOOP: NoOpResponseParser(),
    }
    
    @classmethod
    def get_parser(cls, name: str = AZURE) -> IResponseParser:
        """
        Get a parser by name.
        
        Args:
            name: Parser name ('azure', 'noop', etc.)
            
        Returns:
            IResponseParser instance
            
        Raises:
            ValueError: If parser name is not registered
        """
        parser = cls._parsers.get(name)
        
        if not parser:
            available = ", ".join(cls._parsers.keys())
            raise ValueError(
                f"Unknown parser: '{name}'. Available parsers: {available}"
            )
        
        return parser
    
    @classmethod
    def register(cls, name: str, parser: IResponseParser) -> None:
        """
        Register a custom parser.
        
        Args:
            name: Name to register the parser under
            parser: Parser instance implementing IResponseParser
        """
        cls._parsers[name] = parser
    
    @classmethod
    def list_parsers(cls) -> list:
        """
        List all registered parser names.
        
        Returns:
            List of parser names
        """
        return list(cls._parsers.keys())

