"""Workflow configuration models."""

from typing import Optional

from pydantic import BaseModel, Field


class WorkflowModelConfig(BaseModel):
    """Model selection for each workflow step."""

    query_generation: str = Field(default="ollama:llama3.1:8b")
    binary_filter: str = Field(default="ollama:qwen2.5:14b")
    scoring: str = Field(default="ollama:deepseek-r1:8b")
    verification: str = Field(default="ollama:mistral-nemo:12b")
    contrary_queries: str = Field(default="ollama:llama3.1:8b")
    contrary_scoring: str = Field(default="ollama:deepseek-r1:8b")
    contrary_network: str = Field(default="ollama:llama3.1:8b")
    summary: str = Field(default="ollama:qwen2.5:14b")

    @classmethod
    def cloud_config(cls) -> "WorkflowModelConfig":
        return cls(
            query_generation="google:gemini-2.5-flash-lite",
            binary_filter="google:gemini-2.5-flash-lite",
            scoring="google:gemini-2.5-flash",
            verification="google:gemini-2.5-flash-lite",
            contrary_queries="google:gemini-2.5-flash-lite",
            contrary_scoring="google:gemini-2.5-flash",
            contrary_network="google:gemini-2.5-flash-lite",
            summary="google:gemini-2.5-flash",
        )

    @classmethod
    def hybrid_config(cls) -> "WorkflowModelConfig":
        return cls(
            query_generation="ollama:llama3.1:8b",
            binary_filter="ollama:qwen2.5:14b",
            scoring="ollama:deepseek-r1:8b",
            verification="ollama:mistral-nemo:12b",
            contrary_queries="google:gemini-2.5-flash",
            contrary_scoring="ollama:deepseek-r1:8b",
            contrary_network="ollama:llama3.1:8b",
            summary="google:gemini-2.5-flash",
        )

    def is_local_model(self, model_string: str) -> bool:
        return model_string.startswith("ollama:")

    def is_cloud_model(self, model_string: str) -> bool:
        return any(model_string.startswith(p) for p in ("google:", "openai:", "anthropic:"))


class WorkflowOptimizationConfig(BaseModel):
    enable_batch_scoring: bool = True
    batch_size: int = Field(default=10, ge=1, le=20)
    enable_binary_filter: bool = True
    binary_filter_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    use_categorical_scoring: Optional[bool] = None
    enable_parallel_search: bool = False
    enable_result_caching: bool = False
    cache_ttl_hours: int = Field(default=24, ge=1)
    use_pymupdf4llm: bool = True


class WorkflowConfig(BaseModel):
    models: WorkflowModelConfig = Field(default_factory=WorkflowModelConfig)
    optimization: WorkflowOptimizationConfig = Field(default_factory=WorkflowOptimizationConfig)

    @classmethod
    def local_optimized(cls) -> "WorkflowConfig":
        return cls(
            models=WorkflowModelConfig(),
            optimization=WorkflowOptimizationConfig(
                enable_batch_scoring=True,
                enable_binary_filter=True,
                use_categorical_scoring=True,
                batch_size=10,
            ),
        )

    @classmethod
    def cloud_optimized(cls) -> "WorkflowConfig":
        return cls(
            models=WorkflowModelConfig.cloud_config(),
            optimization=WorkflowOptimizationConfig(
                enable_batch_scoring=True,
                enable_binary_filter=False,
                use_categorical_scoring=False,
                batch_size=10,
            ),
        )

    @classmethod
    def hybrid_optimized(cls) -> "WorkflowConfig":
        return cls(
            models=WorkflowModelConfig.hybrid_config(),
            optimization=WorkflowOptimizationConfig(
                enable_batch_scoring=True,
                enable_binary_filter=True,
                use_categorical_scoring=True,
                batch_size=10,
            ),
        )
