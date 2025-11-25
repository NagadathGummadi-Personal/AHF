"""
No-Op Parameter Transformer.

Pass-through transformer that doesn't modify parameters.
"""

from typing import List
from ...interfaces.llm_interfaces import IParameterTransformer, Parameters
from ...spec.llm_schema import ModelMetadata


class NoOpTransformer(IParameterTransformer):
    """
    No-op implementation of IParameterTransformer.
    
    Returns parameters unchanged. Useful for:
    - Development/testing
    - Models that don't need parameter transformation
    - Direct API calls where parameters are already formatted
    
    Usage:
        transformer = NoOpTransformer()
        params = transformer.transform(params, metadata)  # Returns params unchanged
    """
    
    def transform(
        self,
        params: Parameters,
        metadata: ModelMetadata
    ) -> Parameters:
        """Return parameters unchanged."""
        return params.copy()
    
    def get_supported_parameters(self) -> List[str]:
        """Return empty list (handles nothing)."""
        return []

