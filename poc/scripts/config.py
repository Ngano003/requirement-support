"""
GraphRAG PoC 設定ファイル

OpenAI API、Google AI Studio (Gemini)、vLLM API に対応
"""

import os
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """LLMプロバイダー"""
    OPENAI = "openai"
    GOOGLE_AI = "google_ai"
    VLLM = "vllm"
    OPENROUTER = "openrouter"


class Config(BaseModel):
    """設定クラス"""

    # LLM設定
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENROUTER,
        description="LLMプロバイダー"
    )

    # OpenAI API設定
    openai_api_key: str = Field(
        default="",
        description="OpenAI APIキー"
    )
    openai_model: str = Field(
        default="gpt-4",
        description="OpenAIモデル名"
    )

    # OpenRouter設定
    openrouter_api_key: str = Field(
        default="",
        description="OpenRouter APIキー"
    )
    openrouter_model: str = Field(
        default="qwen/qwen-2.5-coder-32b-instruct",
        description="OpenRouterモデル名"
    )

    # Google AI Studio設定
    google_ai_api_key: str = Field(
        default="",
        description="Google AI Studio APIキー"
    )
    google_ai_model: str = Field(
        default="gemini-1.5-flash",
        description="Geminiモデル名（gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash-exp）"
    )

    # vLLM API設定
    vllm_api_base: str = Field(
        default="http://localhost:8000/v1",
        description="vLLM APIベースURL"
    )
    vllm_model: str = Field(
        default="Qwen/Qwen2.5-Coder-32B-Instruct",
        description="vLLMモデル名"
    )

    # Memgraph設定
    memgraph_host: str = Field(
        default="localhost",
        description="Memgraphホスト"
    )
    memgraph_port: int = Field(
        default=7687,
        description="Memgraphポート"
    )
    memgraph_username: str = Field(
        default="",
        description="Memgraphユーザー名（空の場合は認証なし）"
    )
    memgraph_password: str = Field(
        default="",
        description="Memgraphパスワード"
    )

    # 抽出設定
    extraction_temperature: float = Field(
        default=0.2,
        description="エンティティ抽出時のtemperature（低めで一貫性を確保）"
    )

    # パフォーマンス設定
    max_retries: int = Field(
        default=3,
        description="LLM API呼び出しの最大リトライ回数"
    )

    @classmethod
    def from_env(cls) -> "Config":
        """環境変数から設定を読み込み"""
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "google_ai"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            openrouter_model=os.getenv(
                "OPENROUTER_MODEL",
                "qwen/qwen-2.5-coder-32b-instruct"
            ),
            google_ai_api_key=os.getenv("GOOGLE_AI_API_KEY", ""),
            google_ai_model=os.getenv("GOOGLE_AI_MODEL", "gemini-1.5-flash"),
            vllm_api_base=os.getenv("VLLM_API_BASE", "http://localhost:8000/v1"),
            vllm_model=os.getenv(
                "VLLM_MODEL",
                "Qwen/Qwen2.5-Coder-32B-Instruct"
            ),
            memgraph_host=os.getenv("MEMGRAPH_HOST", "localhost"),
            memgraph_port=int(os.getenv("MEMGRAPH_PORT", "7687")),
            memgraph_username=os.getenv("MEMGRAPH_USERNAME", ""),
            memgraph_password=os.getenv("MEMGRAPH_PASSWORD", ""),
        )

    def get_llm_client_config(self) -> dict:
        """LLMクライアント設定を取得"""
        if self.llm_provider == LLMProvider.OPENAI:
            return {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
            }
        elif self.llm_provider == LLMProvider.OPENROUTER:
            return {
                "api_key": self.openrouter_api_key,
                "base_url": "https://openrouter.ai/api/v1",
                "model": self.openrouter_model,
            }
        elif self.llm_provider == LLMProvider.GOOGLE_AI:
            return {
                "api_key": self.google_ai_api_key,
                "model": self.google_ai_model,
                "provider": "google_ai",
            }
        elif self.llm_provider == LLMProvider.VLLM:
            return {
                "api_key": "EMPTY",  # vLLMは認証不要
                "base_url": self.vllm_api_base,
                "model": self.vllm_model,
            }
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}")
