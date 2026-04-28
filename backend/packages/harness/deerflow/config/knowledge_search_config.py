from pydantic import BaseModel, Field


class KnowledgeSearchConfig(BaseModel):
    enabled: bool = Field(default=False, description="Whether to enable automatic KB search in agent context")
    top_k: int = Field(default=5, ge=1, le=20, description="Final number of merged results to return")
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum similarity score for KB chunks")
    max_kbs: int = Field(default=20, ge=1, description="Maximum number of KBs to search per query")
    max_results_per_kb: int = Field(default=3, ge=1, description="Max results fetched from each KB before merging")
    timeout_seconds: float = Field(default=2.0, ge=0.1, description="Total timeout for all KB searches in seconds")
    max_context_chars: int = Field(default=6000, ge=100, description="Maximum characters in injected knowledge context block")


_knowledge_search_config: KnowledgeSearchConfig = KnowledgeSearchConfig()


def get_knowledge_search_config() -> KnowledgeSearchConfig:
    return _knowledge_search_config


def set_knowledge_search_config(config: KnowledgeSearchConfig) -> None:
    global _knowledge_search_config
    _knowledge_search_config = config


def load_knowledge_search_config_from_dict(config_dict: dict) -> None:
    global _knowledge_search_config
    _knowledge_search_config = KnowledgeSearchConfig(**config_dict)
