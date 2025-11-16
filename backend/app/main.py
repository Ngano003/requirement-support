"""
要件定義書支援AIシステム - バックエンドAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import breakdown, review

# FastAPIアプリケーションを作成
app = FastAPI(
    title="要件定義書支援AIシステム API",
    description="要件定義作業を支援するAIシステムのバックエンドAPI",
    version="1.0.0",
)

# CORS設定
# プロキシ環境や異なるネットワークからのアクセスを許可するため、すべてのオリジンを許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # すべてのオリジンを許可（開発・テスト環境用）
    allow_credentials=False,  # allow_origins=["*"]の場合はFalseにする必要がある
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターを登録
app.include_router(breakdown.router)
app.include_router(review.router)


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "要件定義書支援AIシステム API",
        "version": "1.0.0",
        "endpoints": {
            "breakdown": "/api/breakdown",
            "review": "/api/review",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
