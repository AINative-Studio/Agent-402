"""
Embedding Models Configuration.

This module defines supported embedding models and their specifications.
Implements Epic 3, Story 3: Multi-model support with correct dimensions.

PRD §12 (Extensibility):
- Support multiple embedding models with different dimensions
- Validate model parameter against supported models list
- Return embeddings with correct dimensions for each model

DX Contract §3 (Embeddings & Vectors):
- Default model: BAAI/bge-small-en-v1.5 → 384 dimensions
- Model must be specified consistently for store + search
"""
from enum import Enum
from typing import Dict


class EmbeddingModel(str, Enum):
    """
    Supported embedding models.

    Each model has a specific output dimension that must be maintained
    throughout the embedding lifecycle (generation, storage, search).
    """
    # Default model - lightweight, fast, good quality (DX Contract default)
    BGE_SMALL_EN_V1_5 = "BAAI/bge-small-en-v1.5"

    # Popular sentence-transformers models
    ALL_MINILM_L6_V2 = "sentence-transformers/all-MiniLM-L6-v2"
    ALL_MINILM_L12_V2 = "sentence-transformers/all-MiniLM-L12-v2"
    ALL_MPNET_BASE_V2 = "sentence-transformers/all-mpnet-base-v2"

    # Multi-lingual models
    PARAPHRASE_MULTILINGUAL_MINILM_L12_V2 = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # Specialized models
    ALL_DISTILROBERTA_V1 = "sentence-transformers/all-distilroberta-v1"
    MSMARCO_DISTILBERT_BASE_V4 = "sentence-transformers/msmarco-distilbert-base-v4"


# Model specifications: dimensions and metadata
EMBEDDING_MODEL_SPECS: Dict[str, Dict] = {
    # Default model (DX Contract §3)
    EmbeddingModel.BGE_SMALL_EN_V1_5: {
        "dimensions": 384,
        "description": "Lightweight English model with good quality/speed trade-off (default)",
        "languages": ["en"],
        "max_seq_length": 512,
    },

    # Sentence-transformers models
    EmbeddingModel.ALL_MINILM_L6_V2: {
        "dimensions": 384,
        "description": "Fast and efficient model for semantic similarity",
        "languages": ["en"],
        "max_seq_length": 256,
    },
    EmbeddingModel.ALL_MINILM_L12_V2: {
        "dimensions": 384,
        "description": "Balanced model with good performance",
        "languages": ["en"],
        "max_seq_length": 256,
    },
    EmbeddingModel.ALL_MPNET_BASE_V2: {
        "dimensions": 768,
        "description": "High-quality embeddings with larger dimension",
        "languages": ["en"],
        "max_seq_length": 384,
    },

    # Multi-lingual
    EmbeddingModel.PARAPHRASE_MULTILINGUAL_MINILM_L12_V2: {
        "dimensions": 384,
        "description": "Multi-lingual model for 50+ languages",
        "languages": ["multi"],
        "max_seq_length": 128,
    },

    # Specialized
    EmbeddingModel.ALL_DISTILROBERTA_V1: {
        "dimensions": 768,
        "description": "RoBERTa-based model for high quality embeddings",
        "languages": ["en"],
        "max_seq_length": 512,
    },
    EmbeddingModel.MSMARCO_DISTILBERT_BASE_V4: {
        "dimensions": 768,
        "description": "Optimized for semantic search and retrieval",
        "languages": ["en"],
        "max_seq_length": 512,
    },
}

# Default model per DX Contract §3
DEFAULT_EMBEDDING_MODEL = EmbeddingModel.BGE_SMALL_EN_V1_5.value


def get_model_dimensions(model: str) -> int:
    """
    Get the output dimensions for a specific model.

    Args:
        model: Model identifier (must be in EMBEDDING_MODEL_SPECS)

    Returns:
        Integer dimension count for the model

    Raises:
        ValueError: If model is not supported
    """
    if model not in EMBEDDING_MODEL_SPECS:
        supported_models = ", ".join(EMBEDDING_MODEL_SPECS.keys())
        raise ValueError(
            f"Model '{model}' is not supported. "
            f"Supported models: {supported_models}"
        )

    return EMBEDDING_MODEL_SPECS[model]["dimensions"]


def get_model_spec(model: str) -> Dict:
    """
    Get full specification for a model.

    Args:
        model: Model identifier

    Returns:
        Dictionary with model specifications

    Raises:
        ValueError: If model is not supported
    """
    if model not in EMBEDDING_MODEL_SPECS:
        supported_models = ", ".join(EMBEDDING_MODEL_SPECS.keys())
        raise ValueError(
            f"Model '{model}' is not supported. "
            f"Supported models: {supported_models}"
        )

    return EMBEDDING_MODEL_SPECS[model]


def is_model_supported(model: str) -> bool:
    """
    Check if a model is supported.

    Args:
        model: Model identifier to check

    Returns:
        True if model is supported, False otherwise
    """
    return model in EMBEDDING_MODEL_SPECS


def get_supported_models() -> Dict[str, Dict]:
    """
    Get all supported models and their specifications.

    Returns:
        Dictionary mapping model names to their specifications
    """
    return EMBEDDING_MODEL_SPECS.copy()
