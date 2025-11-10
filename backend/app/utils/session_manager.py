"""
セッション管理
"""
import json
import os
from pathlib import Path
from typing import Optional
from app.models.schemas import SessionData
from app.utils.config import settings


class SessionManager:
    """セッション管理クラス"""

    def __init__(self):
        """初期化"""
        self.data_dir = Path(settings.data_dir)
        self.sessions_dir = self.data_dir / "sessions"
        self.requirements_dir = self.data_dir / "requirements"

        # ディレクトリが存在しない場合は作成
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.requirements_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, session_data: SessionData) -> None:
        """
        セッションデータを保存

        Args:
            session_data: セッションデータ
        """
        session_file = self.sessions_dir / f"{session_data.session_id}.json"

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data.model_dump(), f, ensure_ascii=False, indent=2)

    def load_session(self, session_id: str) -> Optional[SessionData]:
        """
        セッションデータを読み込み

        Args:
            session_id: セッションID

        Returns:
            セッションデータ（存在しない場合はNone）
        """
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return None

        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return SessionData(**data)

    def save_requirements(self, session_id: str, requirements: str) -> str:
        """
        要件定義書を保存

        Args:
            session_id: セッションID
            requirements: 要件定義書（マークダウン）

        Returns:
            保存したファイルのパス
        """
        req_file = self.requirements_dir / f"{session_id}.md"

        with open(req_file, "w", encoding="utf-8") as f:
            f.write(requirements)

        return str(req_file)

    def load_requirements(self, session_id: str) -> Optional[str]:
        """
        要件定義書を読み込み

        Args:
            session_id: セッションID

        Returns:
            要件定義書（存在しない場合はNone）
        """
        req_file = self.requirements_dir / f"{session_id}.md"

        if not req_file.exists():
            return None

        with open(req_file, "r", encoding="utf-8") as f:
            return f.read()


# シングルトンインスタンス
session_manager = SessionManager()
