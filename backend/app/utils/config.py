"""
アプリケーション設定
"""
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定"""

    # LLMプロバイダー設定
    llm_provider: Literal["openrouter", "vllm", "google_ai"] = "openrouter"

    # OpenRouter設定
    openrouter_api_key: str = ""
    openrouter_model: str = "qwen/qwen-2.5-coder-32b-instruct"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # vLLM設定
    vllm_api_base: str = "http://localhost:8000/v1"
    vllm_model: str = "Qwen/Qwen2.5-Coder-32B-Instruct"
    vllm_api_key: str = ""

    # Google AI Studio設定
    google_ai_api_key: str = ""
    google_ai_model: str = "gemini-2.0-flash-exp"

    # アプリケーション設定
    data_dir: str = "../data"
    max_tokens: int = 4096
    temperature: float = 0.7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    @property
    def api_key(self) -> str:
        """使用するLLMプロバイダーのAPIキーを返す"""
        if self.llm_provider == "openrouter":
            return self.openrouter_api_key
        elif self.llm_provider == "google_ai":
            return self.google_ai_api_key
        return self.vllm_api_key

    @property
    def base_url(self) -> str:
        """使用するLLMプロバイダーのベースURLを返す"""
        if self.llm_provider == "openrouter":
            return self.openrouter_base_url
        return self.vllm_api_base

    @property
    def model_name(self) -> str:
        """使用するモデル名を返す"""
        if self.llm_provider == "openrouter":
            return self.openrouter_model
        elif self.llm_provider == "google_ai":
            return self.google_ai_model
        return self.vllm_model


# シングルトンインスタンス
settings = Settings()
