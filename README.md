# DevOps Lifecycle Agent

**DevOps × AI Agent Hackathon（Findy × Google Cloud）出展作品**

Cloud Run のインシデントを検知→診断→修正PR作成→ポストモーテム自動生成まで、
ライフサイクル全体を AI エージェントが一気通貫で対応します。

## アーキテクチャ

```
[Cloud Monitoring Alert]
        ↓
  ObserverAgent     ← Cloud Logging / Monitoring / Revisions から情報収集
        ↓
  DiagnoserAgent    ← Gemini 2.5 Flash が根本原因を特定
        ↓
  FixerAgent        ← 修正PRを自動作成（Human-in-the-Loop: レビュー後マージ）
        ↓
  ReviewerAgent     ← ポストモーテム＋再発防止アラート生成
```

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| エージェント基盤 | Google Agent Development Kit (ADK) — SequentialAgent |
| LLM | Gemini 2.5 Flash (Vertex AI) |
| ホスティング | Cloud Run (デモアプリ) |
| 観測 | Cloud Logging / Cloud Monitoring |
| ソースコード管理 | GitHub API (`gh` CLI) |
| Human-in-the-Loop | GitHub Pull Request レビュー |

## セットアップ

```bash
# 依存インストール
pip install google-adk

# 環境変数設定
cd devops-lifecycle-agent
cp devops_agent/.env.example devops_agent/.env
# .env に GCP プロジェクト ID を記入

# GCP 認証
gcloud auth application-default login

# ADK Dev UI 起動
adk web --port 8766
```

## デモシナリオ: Cloud Run OOM 自動対応

### 1. OOM を発生させる

```bash
# デモアプリに負荷 → メモリリーク（無限キャッシュ）でOOM
for i in $(seq 1 300); do
  curl "https://demo-app-jrf4w2avsq-an.a.run.app/work?n=$i" &
done
wait
```

### 2. エージェント起動

ADK Dev UI (http://localhost:8766) で以下を入力:

> Cloud Run demo-app OOM detected. Memory limit 256Mi exceeded. Investigate and fix.

### 3. パイプライン自動実行

| ステージ | 動作 | 出力 |
|---------|------|------|
| Observer | Cloud Logging/Monitoring/Revisions から収集 | 構造化インシデントレポート |
| Diagnoser | ログ・デプロイ相関分析 | 根本原因レポート（OOM = 無限キャッシュ） |
| Fixer | 修正コード生成 + PR作成 | GitHub PR URL |
| Reviewer | ポストモーテム + 予防ルール | Markdown レポート + アラートJSON |

### 4. Human-in-the-Loop

FixerAgent が作成した PR を人がレビュー → Approve → Merge。
マージ後に再デプロイすればインシデント解決。

## デモアプリ（故障シミュレーション）

`demo-app/app.py` — リアルな隠れメモリリーク:
- `/work?n=X` エンドポイントが計算結果を無限キャッシュ（1MB/エントリ）
- 256Mi 制限下で繰り返し呼び出すと OOM 発生
- Cloud Monitoring アラート（メモリ使用率 >80%）で自動検知

## プロジェクト構成

```
devops-lifecycle-agent/
├── devops_agent/
│   ├── __init__.py          # ADK エントリポイント
│   ├── agent.py             # 4エージェント・パイプライン定義
│   ├── tools.py             # GCP/GitHub ツール群
│   ├── .env.example         # 環境変数テンプレート
│   └── .env                 # (gitignore) 実際の設定
├── demo-app/
│   ├── app.py               # Cloud Run デモアプリ
│   ├── Dockerfile
│   └── requirements.txt
├── README.md
└── LICENSE (MIT)
```

## ライセンス

MIT
