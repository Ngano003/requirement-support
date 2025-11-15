# GraphRAG PoC クイックスタート

## 🎯 5分で始める

### 1. 環境のアクティベート

```bash
cd /home/nagano/work/requirement-support/poc
source .venv/bin/activate
```

### 2. APIキーの設定

```bash
# .envファイルを編集
nano .env

# 以下を設定
GOOGLE_AI_API_KEY=your-api-key-here
```

### 3. 実行

```bash
cd scripts
python graphrag_poc.py samples/sample_requirements_1.md
```

## 📋 期待される出力

```
================================================================================
GraphRAG PoC Started
================================================================================

[Step 1] Loading requirements...
[Step 2] Extracting entities and relations...
[Step 3] Building graph in Memgraph...
[Step 4] Detecting problems...
[Step 5] Generating report...

================================================================================
RESULTS SUMMARY
================================================================================
Total Issues Found: 2
  - Missing Items: 1
  - Contradictions: 1
```

## 🎉 完了！

結果は `output/` ディレクトリに保存されます。
