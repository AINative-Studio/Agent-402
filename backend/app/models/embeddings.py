"""
Embedding model definitions and constants.

Per DX Contract §3 (Embeddings & Vectors):
- Default embedding model: BAAI/bge-small-en-v1.5 -> 384 dimensions
- If model is omitted, 384-dim is guaranteed
- If model is specified, the same model must be used for store + search
- Dimension mismatches always return DIMENSION_MISMATCH

Per Backlog Epic 3, Story 4 (Issue #14):
- Unsupported models return MODEL_NOT_FOUND with HTTP 404
- Error response includes error_code and detail field
- Error message lists supported models
"""
from typing import Dict, List
from enum import Enum


class EmbeddingModel(str, Enum):
    """
    Supported embedding models with their dimensions.
    Per DX Contract: These models are stable and will not change without versioning.
    """
    BGE_SMALL = "BAAI/bge-small-en-v1.5"  # Default: 384 dimensions
    BGE_BASE = "BAAI/bge-base-en-v1.5"    # 768 dimensions
    BGE_LARGE = "BAAI/bge-large-en-v1.5"  # 1024 dimensions
    OPENAI_LEGACY = "openai/text-embedding-ada-002"  # Legacy: 1536 dimensions


# Model dimension mapping
MODEL_DIMENSIONS: Dict[str, int] = {
    EmbeddingModel.BGE_SMALL: 384,
    EmbeddingModel.BGE_BASE: 768,
    EmbeddingModel.BGE_LARGE: 1024,
    EmbeddingModel.OPENAI_LEGACY: 1536,
}


# Default model per DX Contract
DEFAULT_MODEL = EmbeddingModel.BGE_SMALL
DEFAULT_DIMENSIONS = MODEL_DIMENSIONS[DEFAULT_MODEL]


def get_supported_models() -> List[str]:
    """
    Get list of all supported embedding models.

    Returns:
        List of model identifiers as strings
    """
    return [model.value for model in EmbeddingModel]


def get_model_dimensions(model: str) -> int:
    """
    Get the dimension count for a given model.

    Args:
        model: Model identifier string

    Returns:
        Dimension count for the model

    Raises:
        ValueError: If model is not supported
    """
    if model not in MODEL_DIMENSIONS:
        raise ValueError(f"Unsupported model: {model}")
    return MODEL_DIMENSIONS[model]


def is_model_supported(model: str) -> bool:
    """
    Check if a model is supported.

    Args:
        model: Model identifier to check

    Returns:
        True if model is supported, False otherwise
    """
    return model in MODEL_DIMENSIONS


def get_model_info() -> Dict[str, Dict[str, any]]:
    """
    Get comprehensive information about all supported models.

    Returns:
        Dictionary mapping model names to their metadata
    """
    return {
        EmbeddingModel.BGE_SMALL: {
            "dimensions": 384,
            "status": "default",
            "description": "Default model - BAAI BGE Small English v1.5"
        },
        EmbeddingModel.BGE_BASE: {
            "dimensions": 768,
            "status": "supported",
            "description": "BAAI BGE Base English v1.5"
        },
        EmbeddingModel.BGE_LARGE: {
            "dimensions": 1024,
            "status": "supported",
            "description": "BAAI BGE Large English v1.5"
        },
        EmbeddingModel.OPENAI_LEGACY: {
            "dimensions": 1536,
            "status": "legacy",
            "description": "OpenAI text-embedding-ada-002 (legacy support)"
        }
    }
