"""
要件定義ブレークダウンサービス
"""
import json
import uuid
from typing import List, Tuple, Optional
from app.models.schemas import Question, SessionData
from app.services.llm_service import llm_service
from app.utils.config import settings


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

【質問作成のルール】
1. **1つの質問には1つの観点のみ**：複数の観点を1つの質問にまとめない
2. **簡潔で明確**：「例:」や括弧での補足説明は最小限にする
3. **具体的**：曖昧な表現を避け、何を知りたいのか明確にする
4. **優先度付け**：重要な質問から順に生成する

【指示】
- 不明瞭な点や不足している情報について質問する
- エラーハンドリング、セキュリティ、パフォーマンスなどの非機能要件も考慮
- **重要度の高い質問に絞り込み、最大{settings.max_questions}個程度にする**
- 各質問について以下の情報を含める：
  - id: 一意の識別子（q1, q2, ...）
  - category: 必ず次のいずれかを使用 → functional, non_functional, constraint, other
  - question: 質問文（簡潔に1文で）
  - priority: 必ず次のいずれかを使用 → high, medium, low
  - context: 質問の背景（省略可）

**悪い例**：
「本の予約機能について、予約待ちの管理方法（優先順位、キャンセル時の扱い、有効期限）や、受け渡しフロー（通知方法、受け取り方法）の詳細を教えてください。」
→ 複数の観点が混在している

**良い例**：
- 「予約待ちの管理方法として、複数人が予約した場合の優先順位はどのように決めますか？」
- 「予約の有効期限はありますか？」
- 「予約した本が返却されたとき、どのように予約者に通知しますか？」

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

    async def validate_answer(
        self,
        question: str,
        answer: str,
        conversation_history: Optional[List[Tuple[str, str]]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        回答が質問に対して適切かどうかを評価

        Args:
            question: 質問文
            answer: ユーザーの回答
            conversation_history: これまでの会話履歴 [(質問, 回答), ...]

        Returns:
            (is_valid, follow_up_question):
            - is_valid: 回答が妥当ならTrue
            - follow_up_question: 不十分な場合の追加質問（妥当な場合はNone）
        """
        # 会話履歴を整形
        history_text = ""
        if conversation_history and len(conversation_history) > 0:
            history_text = "\n【これまでの会話履歴】\n"
            for i, (prev_q, prev_a) in enumerate(conversation_history, 1):
                history_text += f"{i}. Q: {prev_q}\n   A: {prev_a}\n\n"

        # デバッグログ
        print(f"[DEBUG] validate_answer called")
        print(f"[DEBUG] Question: {question}")
        print(f"[DEBUG] Answer: {answer}")
        print(f"[DEBUG] History length: {len(conversation_history) if conversation_history else 0}")
        print(f"[DEBUG] History text: {history_text}")

        validation_prompt = f"""以下の質問と回答を評価してください。
{history_text}
【今回の質問】
{question}

【今回の回答】
{answer}

【評価基準】
1. 回答が質問に対して直接的に答えているか
2. 回答が具体的で実装可能な内容か、または「未確定」「不明」「決まっていない」と明示されているか
3. 回答が曖昧でないか
4. **会話履歴がある場合、前回の回答と組み合わせて評価する**（今回の回答は前回の補足として扱う）

【指示】
回答を評価し、以下のJSON形式で出力してください：

- 回答が妥当な場合（具体的な回答、または「未確定」「不明」「決まっていない」と明示している場合）：
```json
{{"is_valid": true, "reason": "評価理由"}}
```

- 回答が不十分な場合（言い換えた追加質問を含める）：
```json
{{"is_valid": false, "reason": "不十分な理由", "follow_up": "言い換えた質問文（より具体的で答えやすく）"}}
```

**重要**：
- 「未確定」「不明」「決まっていない」「まだ決まっていない」などの回答はis_valid=true（現段階で決まっていないことを明示しているため）
- 「特になし」「任せます」など、検討したのか不明な曖昧な回答はis_valid=false
- 質問に対して何も答えていない場合はis_valid=false
- 追加質問は元の質問を言い換えて、より答えやすくする

JSON形式のみを出力してください。
"""

        response_json = await llm_service.generate_with_system_prompt(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=validation_prompt,
            temperature=0.3,
        )

        # JSONをパース
        try:
            response_json = response_json.strip()
            if response_json.startswith("```json"):
                response_json = response_json[7:]
            if response_json.startswith("```"):
                response_json = response_json[3:]
            if response_json.endswith("```"):
                response_json = response_json[:-3]
            response_json = response_json.strip()

            result = json.loads(response_json)
            is_valid = result.get("is_valid", True)
            follow_up = result.get("follow_up", None)

            return is_valid, follow_up

        except Exception as e:
            print(f"回答評価エラー: {e}")
            # エラーの場合は妥当とみなす（フォールバック）
            return True, None

    async def process_answer(
        self,
        session_data: SessionData,
        question_id: str,
        answer: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        質問への回答を記録し、妥当性をチェック

        Args:
            session_data: セッションデータ
            question_id: 質問ID
            answer: ユーザーの回答

        Returns:
            (is_valid, follow_up_question):
            - is_valid: 回答が妥当ならTrue
            - follow_up_question: 不十分な場合の追加質問
        """
        # 該当する質問を見つける
        question = next((q for q in session_data.questions if q.id == question_id), None)
        if not question:
            raise ValueError(f"質問ID {question_id} が見つかりません")

        # これまでの会話履歴を構築（回答済みの質問）
        conversation_history = []
        for answered_q in session_data.answered_questions:
            q_text = answered_q.question
            a_text = session_data.answers.get(answered_q.id, "")
            conversation_history.append((q_text, a_text))

        # 現在の質問に対する過去の回答があれば追加（追加質問の場合）
        if question_id in session_data.answers:
            previous_answer = session_data.answers[question_id]
            # 前回の回答を履歴に追加（「以前の回答」として）
            conversation_history.append((f"{question.question}（前回の回答）", previous_answer))

        # 回答の妥当性をチェック（会話履歴を含む）
        is_valid, follow_up = await self.validate_answer(
            question.question, answer, conversation_history
        )

        if is_valid:
            # 回答を記録（前回の回答を上書き）
            session_data.answers[question_id] = answer

            # 回答済みの質問に移動
            session_data.questions.remove(question)
            session_data.answered_questions.append(question)

            return True, None
        else:
            # 不十分な回答の場合、一時的に回答を記録（次の回答時に参照できるように）
            session_data.answers[question_id] = answer
            # 質問は削除しない（まだ回答が完了していないため）
            return False, follow_up

    async def update_requirements_with_all_answers(
        self,
        session_data: SessionData,
    ) -> str:
        """
        全ての回答を反映して要件定義書を更新

        Args:
            session_data: セッションデータ

        Returns:
            updated_requirements: 更新された要件定義書
        """
        # 全ての質問と回答をまとめる
        qa_text = ""
        for q in session_data.answered_questions:
            answer = session_data.answers.get(q.id, "")
            qa_text += f"\n【質問{q.id}】\n{q.question}\n【回答】\n{answer}\n"

        # 要件定義書を更新
        update_prompt = f"""以下の要件定義書を、全てのユーザー回答に基づいて更新してください。

【現在の要件定義書】
{session_data.requirements}

【全ての質問と回答】
{qa_text}

【指示】
- 全てのユーザー回答を要件定義書に反映する
- 関連する「TODO」や「要確認」を具体的な内容に置き換える
- 新しい情報を適切なセクションに追加する
- マークダウン形式を維持する
- 矛盾がないように注意する
- 回答の内容を統合して、一貫性のある要件定義書にする

更新された要件定義書のみを出力してください。他の説明は不要です。
"""

        updated_requirements = await llm_service.generate_with_system_prompt(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=update_prompt,
        )

        return updated_requirements

    async def generate_update_summary(
        self,
        session_data: SessionData,
        updated_requirements: str,
    ) -> str:
        """
        要件定義書の更新要点を生成

        Args:
            session_data: セッションデータ
            updated_requirements: 更新された要件定義書

        Returns:
            update_summary: 更新要点
        """
        # 全ての質問と回答をまとめる
        qa_text = ""
        for q in session_data.answered_questions:
            answer = session_data.answers.get(q.id, "")
            qa_text += f"\n- {q.question}\n  回答: {answer}\n"

        summary_prompt = f"""以下のユーザー回答に基づいて、要件定義書をどのように更新したかを簡潔に要約してください。

【ユーザーの回答】
{qa_text}

【指示】
- 更新した主要なポイントを3〜5個の箇条書きで記載
- 各ポイントは1文で簡潔に
- 「〜を明確化しました」「〜を追加しました」のような形式で
- マークダウン形式の箇条書きで出力

例：
- システム概要として社内書籍管理システムであることを明確化しました
- 対象ユーザーを全社員（約100名）と明記しました
- 予算を200万円以内、納期を3ヶ月後と設定しました
"""

        update_summary = await llm_service.generate_with_system_prompt(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=summary_prompt,
            temperature=0.3,
        )

        return update_summary.strip()

    async def generate_next_questions(
        self,
        session_data: SessionData,
        updated_requirements: str,
    ) -> List[Question]:
        """
        要件定義書更新後に新しい質問を生成

        Args:
            session_data: セッションデータ
            updated_requirements: 更新された要件定義書

        Returns:
            new_questions: 新しい質問リスト
        """
        # これまでの全Q&Aをまとめる
        qa_history = ""
        for q in session_data.answered_questions:
            answer = session_data.answers.get(q.id, "")
            qa_history += f"\n質問: {q.question}\n回答: {answer}\n"

        # 新しい質問を生成
        new_questions_prompt = f"""以下の要件定義書を見て、まだ明確でない点や追加で確認すべき点について質問を生成してください。

【要件定義書】
{updated_requirements}

【これまでの質問と回答の履歴】
{qa_history}

【質問作成のルール】
1. **1つの質問には1つの観点のみ**：複数の観点を1つの質問にまとめない
2. **簡潔で明確**：「例:」や括弧での補足説明は最小限にする
3. **具体的**：曖昧な表現を避け、何を知りたいのか明確にする
4. **優先度付け**：重要な質問から順に生成する

【指示】
- 既に明確になった点については質問しない
- 要件定義書の品質を高めるための追加質問をする
- **重要度の高い質問に絞り込み、最大{settings.max_questions}個程度にする**
- categoryは必ず "functional", "non_functional", "constraint", "other" のいずれかを使用
- priorityは必ず "high", "medium", "low" のいずれかを使用
- 要件が十分に明確で追加質問が不要な場合は空の配列を返す

JSON形式で出力してください：
```json
[
  {{
    "id": "q{len(session_data.answered_questions) + 1}",
    "category": "functional",
    "question": "質問文（簡潔に1文で）",
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

        return new_questions

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
