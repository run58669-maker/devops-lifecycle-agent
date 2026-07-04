# DevOps Lifecycle Agent

**DevOps × AI Agent Hackathon（Findy × Google Cloud）出展作品**

Cloud Run のインシデントを検知→診断→修正PR作成→ポストモーテム自動生成まで、
ライフサイクル全体を AI エージェントが一気通貫で対応します。

## アーキテクチャ

```
[Cloud Monitoring Alert]
        ↓
  ObserverAgent     ← ログ・アラート・デプロイ履歴を収集
        ↓
  DiagnoserAgent    ← Gemini が根本原因を分析
        ↓
  FixerAgent        ← 修正PRを自動作成（Human-in-the-Loop）
        ↓
  ReviewerAgent     ← ポストモーテム＋再発防止アラート生成
```

## 技術スタック

- **Google Agent Development Kit (ADK)** — マルチエージェント・オーケストレーション
- **Gemini 2.5 Flash** (Vertex AI) — 根本原因分析・修正コード生成
- **Cloud Run** — デモアプリのホスティング
- **Cloud Logging / Monitoring** — 観測データ取得
- **GitHub API** — 修正PRの自動作成

## セットアップ

```bash
pip install google-adk
cd devops-lifecycle-agent
cp devops_agent/.env.example devops_agent/.env
# .env に GCP プロジェクト ID を設定
adk web --port 8766
```

## デモ

1. デモアプリ（Cloud Run）に負荷をかけて OOM を発生させる
2. ADK Dev UI でエージェントを起動
3. 4段階パイプラインが自動実行：検知→診断→修正PR→ポストモーテム

## ライセンス

MIT
