"""
LLMサービス
OpenRouter、vLLM、またはGoogle AI Studioと通信するためのサービス
"""
from typing import List, Optional
from openai import AsyncOpenAI
from app.utils.config import settings


class LLMService:
    """LLMサービスクラス"""

    def __init__(self):
        """初期化"""
        self.provider = settings.llm_provider

        if self.provider == "google_ai":
            # Google AI Studioの場合
            import google.generativeai as genai
            genai.configure(api_key=settings.api_key)
            self.google_client = genai.GenerativeModel(settings.model_name)
            self.client = None
        else:
            # OpenRouterまたはvLLMの場合
            self.client = AsyncOpenAI(
                api_key=settings.api_key,
                base_url=settings.base_url,
            )
            self.google_client = None

        self.model = settings.model_name
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature

    async def generate_completion(
        self,
        messages: List[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        テキスト生成

        Args:
            messages: メッセージリスト [{"role": "user", "content": "..."}]
            temperature: 温度パラメータ（オプション）
            max_tokens: 最大トークン数（オプション）

        Returns:
            生成されたテキスト
        """
        try:
            if self.provider == "google_ai":
                # Google AI Studioの場合
                import google.generativeai as genai

                # メッセージを結合してプロンプトに変換
                prompt = ""
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "system":
                        prompt += f"System: {content}\n\n"
                    elif role == "user":
                        prompt += f"User: {content}\n\n"
                    elif role == "assistant":
                        prompt += f"Assistant: {content}\n\n"

                # 生成設定
                generation_config = genai.GenerationConfig(
                    temperature=temperature or self.temperature,
                    max_output_tokens=max_tokens or self.max_tokens,
                )

                # テキスト生成（非同期）
                response = await self.google_client.generate_content_async(
                    prompt,
                    generation_config=generation_config,
                )

                return response.text

            else:
                # OpenRouterまたはvLLMの場合
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature or self.temperature,
                    max_tokens=max_tokens or self.max_tokens,
                )

                return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"LLM生成エラー: {str(e)}")

    async def generate_with_system_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        システムプロンプトとユーザープロンプトでテキスト生成

        Args:
            system_prompt: システムプロンプト
            user_prompt: ユーザープロンプト
            temperature: 温度パラメータ（オプション）
            max_tokens: 最大トークン数（オプション）

        Returns:
            生成されたテキスト
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        return await self.generate_completion(messages, temperature, max_tokens)


# シングルトンインスタンス
llm_service = LLMService()
