---
name: splunk-o11y
description: Splunk Observability Cloud APM APIを使用してサービストポロジー、トレース、サービスメトリクス（エラー率・レイテンシ・スループット）を取得・分析するためのスキル。デバッグ時の問題特定、サービス依存関係の調査、環境別のサービス比較に使用。トレースID、サービス名、APM、依存関係、トポロジー、エラー率、レイテンシ、スループットなどのキーワードで起動。
---

# Splunk Observability Cloud APM

Splunk Observability CloudのAPM APIを使用してサービストポロジー、トレース、サービスメトリクスを取得する。

## 環境設定

### 認証情報（SF_TOKEN / SF_REALM）

スクリプトの実行には環境変数 `SF_TOKEN`（必須）と `SF_REALM`（デフォルト: `us1`）が必要。
これらは `settings.local.json` の `env` セクションで設定する。`settings.local.json` はgit管理対象外のため、認証情報が誤ってコミットされることを防げる。

**スキルのインストールスコープに応じた設定先**:

| インストールスコープ | 設定ファイル |
|-------------------|------------|
| ユーザースコープ（`~/.claude/skills/`） | `~/.claude/settings.local.json` |
| プロジェクトスコープ（`.claude/skills/`） | `<project>/.claude/settings.local.json` |

設定例:

```json
{
  "env": {
    "SF_TOKEN": "your-api-token",
    "SF_REALM": "us1"
  }
}
```

既存の `settings.local.json` がある場合は `env` セクションのみ追記・マージすること。設定後、新しいClaude Codeセッションから自動的に環境変数として注入される。

### environment パラメータ

`--environment` にはアプリケーションで設定している環境名（`deployment.environment` 属性の値）を指定する。以下の `production` は例であり、実際の環境名に置き換えること。

**重要**: 会話のコンテキストやプロンプトから `--environment` に指定すべき値が判断できない場合、AskUserQuestion ツールを使用して環境名をユーザーに確認すること。推測して実行してはならない。

## サービストポロジー取得

### 全サービスのトポロジー

```bash
python3 scripts/get_topology.py --environment production
```

### 特定サービスの依存関係

```bash
python3 scripts/get_topology.py --environment production --service my-service
```

### 時間範囲を指定

```bash
python3 scripts/get_topology.py --environment production \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-01T12:00:00Z
```

## トレース取得

### トレースIDから最新スパンを取得

```bash
python3 scripts/get_trace.py <trace-id>
```

### セグメント一覧を取得

```bash
python3 scripts/get_trace.py <trace-id> --segments
```

### 特定セグメントのスパンを取得

```bash
python3 scripts/get_trace.py <trace-id> --segment-timestamp 1704067200000000
```

## サービスメトリクス取得

SignalFlow APIを使用して、APMサービスメトリクス（エラー率、P99レイテンシ、スループット）を取得する。

### エラー率（全サービス）

```bash
python3 scripts/get_service_metrics.py --environment production --metric error-rate
```

### P99レイテンシ（特定サービス）

```bash
python3 scripts/get_service_metrics.py --environment production --metric latency --service checkout
```

### スループット（カスタム時間範囲）

```bash
python3 scripts/get_service_metrics.py --environment production --metric throughput \
    --start-time 2024-01-01T00:00:00Z --end-time 2024-01-01T01:00:00Z
```

### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--environment` | 環境名（必須） | - |
| `--metric` | `error-rate`, `latency`, `throughput` のいずれか（必須） | - |
| `--service` | サービス名でフィルタ | 全サービス |
| `--start-time` | 開始時刻（ISO8601） | 10分前 |
| `--end-time` | 終了時刻（ISO8601） | 現在 |
| `--resolution` | 解像度（ミリ秒） | 60000 |

### 出力例

```json
{
  "metric_type": "error-rate",
  "environment": "production",
  "results": [
    {
      "service": "checkout",
      "error_rate_pct": 50.0,
      "error_count": 10,
      "total_count": 20
    }
  ]
}
```

## デバッグワークフロー

1. **サービス健全性を確認**: `get_service_metrics.py --metric error-rate` で全サービスのエラー率を確認
2. **問題サービスを特定**: エラー率やレイテンシが異常なサービスを絞り込む
3. **サービス依存関係を調査**: `get_topology.py --service <name>` で上流・下流を確認
4. **問題のトレースを特定**: トレースIDを取得
5. **トレース詳細を取得**: `get_trace.py` でスパン一覧を確認
6. **環境比較**: 異なる `--environment` で結果を比較

## APIリファレンス

- 概要・使用例: [references/api_reference.md](references/api_reference.md)
- OpenAPI定義（詳細）:
  - [references/apm_service_topology-latest.json](references/apm_service_topology-latest.json)
  - [references/trace_id-latest.json](references/trace_id-latest.json)
