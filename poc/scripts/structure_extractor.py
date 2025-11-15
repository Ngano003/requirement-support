"""
構造抽出器（フェーズA: 構造把握）

LLMを使って要件定義書から主要な構造（アクター、機能、データ）の候補を抽出する
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class StructureExtractor:
    """構造抽出器"""

    def __init__(self, llm_client, model: str, provider: str = "openai"):
        """
        Args:
            llm_client: LLMクライアント（OpenAI互換 or Google Generative AI）
            model: モデル名
            provider: プロバイダー名（"openai", "google_ai"など）
        """
        self.llm_client = llm_client
        self.model = model
        self.provider = provider

    async def extract_structure(self, requirements_text: str) -> Dict[str, Any]:
        """
        要件定義書から構造候補を抽出

        Args:
            requirements_text: 要件定義書の本文

        Returns:
            {
                "actor_candidates": [...],
                "function_candidates": [...],
                "data_candidates": [...],
                "requirement_candidates": [...]
            }
        """
        logger.info("Extracting structure candidates from requirements...")

        prompt = self._build_extraction_prompt(requirements_text)

        # LLMに構造抽出を依頼
        if self.provider == "google_ai":
            response = await self._call_google_ai(prompt)
        else:
            response = await self._call_openai_compatible(prompt)

        # JSONをパース（マークダウンコードブロックを除去）
        try:
            # マークダウンコードブロック（```json ... ```）を除去
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]  # "```json" を除去
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]  # "```" を除去
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]  # "```" を除去
            cleaned_response = cleaned_response.strip()

            structure = json.loads(cleaned_response)
            logger.info(
                f"Extracted candidates:\n"
                f"  - Actors: {len(structure.get('actor_candidates', []))}\n"
                f"  - Functions: {len(structure.get('function_candidates', []))}\n"
                f"  - Data: {len(structure.get('data_candidates', []))}\n"
                f"  - Requirements: {len(structure.get('requirement_candidates', []))}"
            )
            return structure
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response (first 500 chars): {response[:500]}")
            # フォールバック: 空の構造を返す
            return {
                "actor_candidates": [],
                "function_candidates": [],
                "data_candidates": [],
                "requirement_candidates": [],
            }

    def _build_extraction_prompt(self, requirements_text: str) -> str:
        """構造抽出プロンプトを生成"""
        return f"""あなたは要件定義書の構造分析の専門家です。

以下の要件定義書から、主要な構造要素の候補を抽出してください。

## 抽出する要素

1. **アクター候補（actor_candidates）**:
   - システムを利用する人や役割（例: 管理者、一般ユーザー、営業担当）
   - 連携する外部システム（例: 決済ゲートウェイ、メール送信サービス）
   - 各候補には name と description を含める

2. **機能候補（function_candidates）**:
   - システムが提供する主要な機能やユースケース（例: 商品登録、在庫管理、注文処理）
   - ビジネスプロセスや業務フロー（例: 承認フロー、精算処理）
   - 各候補には name と description を含める

3. **データ候補（data_candidates）**:
   - 管理される主要なデータやエンティティ（例: 商品マスタ、注文DB、ユーザー情報）
   - テーブル、ファイル、API レスポンスなどの具体的なデータ構造
   - 各候補には name、description、sensitivity（機密性レベル: low/medium/high/confidential）を含める

4. **要件候補（requirement_candidates）**:
   - 制約やルール（例: パスワードは8文字以上、注文は24時間以内に処理）
   - 非機能要件（例: 99.9%の可用性、1秒以内のレスポンス）
   - セキュリティ要件（例: SSL/TLS必須、個人情報の暗号化）
   - 各候補には name、description、type（Functional/NonFunctional/Security/Business）を含める

## 出力形式

JSON形式で出力してください。JSONのみを出力し、他の説明やマークダウン記法は含めないでください。

```json
{{
  "actor_candidates": [
    {{"name": "管理者", "description": "システム全体を管理する権限を持つユーザー"}},
    {{"name": "一般ユーザー", "description": "商品を閲覧・購入するユーザー"}}
  ],
  "function_candidates": [
    {{"name": "商品登録", "description": "新しい商品をシステムに登録する機能"}},
    {{"name": "在庫管理", "description": "商品の在庫数を管理・更新する機能"}}
  ],
  "data_candidates": [
    {{"name": "商品マスタ", "description": "商品情報を格納するデータベーステーブル", "sensitivity": "low"}},
    {{"name": "ユーザー情報", "description": "ユーザーの個人情報を格納するテーブル", "sensitivity": "high"}}
  ],
  "requirement_candidates": [
    {{"name": "パスワードポリシー", "description": "パスワードは8文字以上で英数字と記号を含む", "type": "Security"}},
    {{"name": "レスポンス時間", "description": "APIのレスポンスは1秒以内", "type": "NonFunctional"}}
  ]
}}
```

## 要件定義書

{requirements_text}

## 出力

JSON形式で構造候補を出力してください:"""

    async def _call_google_ai(self, prompt: str) -> str:
        """Google AI Studio APIを呼び出し"""
        try:
            response = self.llm_client.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Google AI API call failed: {e}")
            raise

    async def _call_openai_compatible(self, prompt: str) -> str:
        """OpenAI互換APIを呼び出し"""
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは要件定義書の構造分析の専門家です。JSON形式で正確に出力してください。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # 低めの温度で一貫性を確保
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI-compatible API call failed: {e}")
            raise

    def save_candidates(self, structure: Dict[str, Any], output_path: str):
        """
        候補をJSONファイルに保存

        Args:
            structure: 抽出された構造候補
            output_path: 出力先ファイルパス
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)
        logger.info(f"Structure candidates saved to: {output_path}")

    @staticmethod
    def load_candidates(input_path: str) -> Dict[str, Any]:
        """
        候補をJSONファイルから読み込み

        Args:
            input_path: 入力ファイルパス

        Returns:
            構造候補
        """
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)
