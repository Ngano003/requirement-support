"""
要件定義ブレークダウンサービス
"""
import json
import uuid
from typing import List, Tuple
from app.models.schemas import Question, SessionData
from app.services.llm_service import llm_service


class BreakdownService:
    """要件定義ブレークダウンサービス"""

    SYSTEM_PROMPT = """あなたは優秀なシステムエンジニアであり、要件定義のエキスパートです。
ユーザーから提供される打ち合わせの記録や議事録を分析し、要件定義書を作成します。

あなたの役割：
1. 入力されたテキストから要件を抽出し、構造化された要件定義書を作成する
2. 不明瞭な点や不足している情報について、的確な質問を生成する
3. ユーザーの回答を受けて、要件定義書を段階的に改善する

要件定義書のフォーマット：
- マークダウン形式
- 以下のセクションを含める：
  1. システム概要
  2. 目的・背景
  3. 対象ユーザー
  4. 機能要件
  5. 非機能要件
  6. 制約条件
  7. 前提条件

質問生成のガイドライン：
- 具体的で明確な質問をする
- エラーハンドリング、セキュリティ、パフォーマンスなどの非機能要件も考慮する
- 優先度を適切に設定する（High/Medium/Low）
"""

    async def initialize_session(self, input_text: str) -> Tuple[str, str, List[Question]]:
        """
        セッションを初期化し、要件定義書のたたき台と質問を生成

        Args:
            input_text: 打ち合わせの記録

        Returns:
            (session_id, draft_requirements, questions)
        """
        # 要件定義書のたたき台を生成
        draft_prompt = f"""以下の打ち合わせの記録から、要件定義書のたたき台を作成してください。

【打ち合わせの記録】
{input_text}

【指示】
- マークダウン形式で作成
- 以下のセクションを含める：
  1. システム概要
  2. 目的・背景
  3. 対象ユーザー
  4. 機能要件
  5. 非機能要件
  6. 制約条件
  7. 前提条件
- 情報が不足している箇所は「TODO」または「要確認」と記載
- 具体的かつ明確に記述

要件定義書のみを出力してください。他の説明は不要です。
"""

        draft_requirements = await llm_service.generate_with_system_prompt(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=draft_prompt,
        )

        # 質問を生成
        questions_prompt = f"""以下の打ち合わせの記録と要件定義書のたたき台を見て、要件を明確にするための質問を生成してください。

【打ち合わせの記録】
{input_text}

【要件定義書のたたき台】
{draft_requirements}

【指示】
- 不明瞭な点や不足している情報について質問する
- エラーハンドリング、セキュリティ、パフォーマンスなどの非機能要件も考慮
- 各質問について以下の情報を含める：
  - id: 一意の識別子（q1, q2, ...）
  - category: 必ず次のいずれかを使用 → functional, non_functional, constraint, other
  - question: 質問文
  - priority: 必ず次のいずれかを使用 → high, medium, low
  - context: 質問の背景（オプション）

**重要**: categoryは必ず "functional", "non_functional", "constraint", "other" のいずれか、priorityは必ず "high", "medium", "low" のいずれかを使用してください。

JSON形式で出力してください：
```json
[
  {{
    "id": "q1",
    "category": "functional",
    "question": "質問文",
    "priority": "high",
    "context": "背景説明"
  }}
]
```

JSON配列のみを出力してください。他の説明は不要です。
"""

        questions_json = await llm_service.generate_with_system_prompt(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=questions_prompt,
            temperature=0.5,
        )

        # JSONをパース
        questions = self._parse_questions(questions_json)

        # セッションIDを生成
        session_id = str(uuid.uuid4())

        return session_id, draft_requirements, questions

    async def process_answer(
        self,
        session_data: SessionData,
        question_id: str,
        answer: str,
    ) -> Tuple[str, List[Question]]:
        """
        質問への回答を処理し、要件定義書を更新

        Args:
            session_data: セッションデータ
            question_id: 質問ID
            answer: ユーザーの回答

        Returns:
            (updated_requirements, new_questions)
        """
        # 該当する質問を見つける
        question = next((q for q in session_data.questions if q.id == question_id), None)
        if not question:
            raise ValueError(f"質問ID {question_id} が見つかりません")

        # 要件定義書を更新
        update_prompt = f"""以下の要件定義書を、ユーザーの回答に基づいて更新してください。

【現在の要件定義書】
{session_data.requirements}

【質問】
{question.question}

【ユーザーの回答】
{answer}

【指示】
- ユーザーの回答を要件定義書に反映する
- 関連する「TODO」や「要確認」を具体的な内容に置き換える
- 新しい情報を適切なセクションに追加する
- マークダウン形式を維持する
- 矛盾がないように注意する

更新された要件定義書のみを出力してください。他の説明は不要です。
"""

        updated_requirements = await llm_service.generate_with_system_prompt(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=update_prompt,
        )

        # 新しい質問を生成（必要に応じて）
        new_questions_prompt = f"""以下の要件定義書を見て、まだ明確でない点や追加で確認すべき点について質問を生成してください。

【要件定義書】
{updated_requirements}

【これまでの質問と回答】
質問: {question.question}
回答: {answer}

【指示】
- 既に明確になった点については質問しない
- 要件定義書の品質を高めるための追加質問をする
- 最大5個の質問を生成する
- categoryは必ず "functional", "non_functional", "constraint", "other" のいずれかを使用
- priorityは必ず "high", "medium", "low" のいずれかを使用

JSON形式で出力してください：
```json
[
  {{
    "id": "q{len(session_data.answered_questions) + len(session_data.questions) + 1}",
    "category": "functional",
    "question": "質問文",
    "priority": "high",
    "context": "背景説明"
  }}
]
```

質問がない場合は空の配列 [] を返してください。
JSON配列のみを出力してください。他の説明は不要です。
"""

        new_questions_json = await llm_service.generate_with_system_prompt(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=new_questions_prompt,
            temperature=0.5,
        )

        new_questions = self._parse_questions(new_questions_json)

        return updated_requirements, new_questions

    def _parse_questions(self, json_str: str) -> List[Question]:
        """
        JSON文字列から質問リストをパース

        Args:
            json_str: JSON形式の文字列

        Returns:
            質問リスト
        """
        try:
            # コードブロックを除去
            json_str = json_str.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            json_str = json_str.strip()

            # JSONをパース
            questions_data = json.loads(json_str)

            # Questionオブジェクトに変換（バリデーションエラーを処理）
            questions = []
            valid_categories = ["functional", "non_functional", "constraint", "other"]
            valid_priorities = ["high", "medium", "low"]

            for q_data in questions_data:
                # カテゴリの正規化
                if "category" in q_data and q_data["category"] not in valid_categories:
                    print(f"Invalid category '{q_data['category']}', replacing with 'other'")
                    q_data["category"] = "other"

                # 優先度の正規化
                if "priority" in q_data and q_data["priority"] not in valid_priorities:
                    print(f"Invalid priority '{q_data['priority']}', replacing with 'medium'")
                    q_data["priority"] = "medium"

                try:
                    question = Question(**q_data)
                    questions.append(question)
                except Exception as e:
                    print(f"Error creating Question object: {e}")
                    print(f"Question data: {q_data}")
                    # エラーが発生した質問はスキップ
                    continue

            return questions

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"JSON string: {json_str}")
            return []
        except Exception as e:
            print(f"Error parsing questions: {e}")
            return []

    def calculate_completion_rate(self, session_data: SessionData) -> float:
        """
        要件の充足率を計算

        Args:
            session_data: セッションデータ

        Returns:
            充足率（0-100）
        """
        total_questions = len(session_data.answered_questions) + len(session_data.questions)
        if total_questions == 0:
            return 100.0

        answered = len(session_data.answered_questions)
        return (answered / total_questions) * 100


# シングルトンインスタンス
breakdown_service = BreakdownService()
