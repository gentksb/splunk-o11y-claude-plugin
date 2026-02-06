# splunk-o11y-claude-plugin

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin that provides Splunk Observability Cloud APM capabilities. Retrieve service topology, traces, and service metrics (error rate, latency, throughput) directly from your Claude Code sessions.

## Features

- **Service Topology** - Visualize service dependencies and relationships within your APM environment
- **Trace Retrieval** - Fetch trace data by trace ID, including segment listing and span details
- **Service Metrics** - Query error rates, P99 latency, and throughput per service using SignalFlow API

## Prerequisites

- [Splunk Observability Cloud](https://www.splunk.com/en_us/products/observability.html) account with APM enabled
- API access token with `admin`, `power`, or `read_only` role
- Python 3.10+
- `requests` library (`pip install requests`)

## Installation

### Step 1: Add the marketplace

```bash
claude plugin marketplace add gentksb/splunk-o11y-claude-plugin
```

### Step 2: Install the plugin

```bash
claude plugin install splunk-o11y
```

## Configuration

After installing the plugin, configure your Splunk credentials in `settings.local.json`. This file is excluded from version control by Claude Code, keeping your credentials safe.

**Choose the appropriate scope:**

| Scope | Configuration file |
|-------|-------------------|
| User scope (`~/.claude/skills/`) | `~/.claude/settings.local.json` |
| Project scope (`.claude/skills/`) | `<project>/.claude/settings.local.json` |

**Add the following to your `settings.local.json`:**

```json
{
  "env": {
    "SF_TOKEN": "your-api-token",
    "SF_REALM": "us1"
  }
}
```

If `settings.local.json` already exists, merge the `env` section into it. The environment variables are automatically injected when you start a new Claude Code session.

### Available Realms

| Realm | Region |
|-------|--------|
| `us0` | US (Oregon) |
| `us1` | US (Virginia) |
| `us2` | US (Oregon) |
| `eu0` | EU (Frankfurt) |
| `jp0` | Japan (Tokyo) |
| `au0` | Australia (Sydney) |

## Usage

Once configured, Claude Code will automatically use this skill when you ask about APM-related topics such as service topology, traces, error rates, latency, or throughput.

### Service Topology

Get the full service topology for an environment:

```
> Show me the service topology for the production environment
```

This runs:
```bash
python scripts/get_topology.py --environment production
```

Get dependencies for a specific service:

```bash
python scripts/get_topology.py --environment production --service my-service
```

### Trace Retrieval

Retrieve trace data by trace ID:

```
> Get the trace details for trace ID abc123def456
```

This runs:
```bash
python scripts/get_trace.py abc123def456
```

List segments or get a specific segment:

```bash
# List segments
python scripts/get_trace.py abc123def456 --segments

# Get specific segment by timestamp
python scripts/get_trace.py abc123def456 --segment-timestamp 1704067200000000
```

### Service Metrics

Query service metrics using SignalFlow API:

```
> What are the error rates for services in the production environment?
```

This runs:
```bash
python scripts/get_service_metrics.py --environment production --metric error-rate
```

Other metric types:

```bash
# P99 latency for a specific service
python scripts/get_service_metrics.py --environment production --metric latency --service checkout

# Throughput with custom time range
python scripts/get_service_metrics.py --environment production --metric throughput \
    --start-time 2024-01-01T00:00:00Z --end-time 2024-01-01T01:00:00Z
```

**Sample output (error rate):**

```json
{
  "metric_type": "error-rate",
  "description": "Error rate per service (%)",
  "environment": "production",
  "time_range": {
    "start_ms": 1704063600000,
    "stop_ms": 1704067200000
  },
  "results": [
    {
      "service": "checkout",
      "error_rate_pct": 2.5,
      "error_count": 5,
      "total_count": 200
    }
  ]
}
```

## Security & Transparency

This plugin is designed to be fully auditable. Here is what the scripts do and do not do:

### What the scripts do

- Make HTTP requests **only** to Splunk Observability Cloud APIs:
  - `https://api.{realm}.signalfx.com/v2/apm/topology` (service topology)
  - `https://api.{realm}.signalfx.com/v2/apm/trace/{traceId}/*` (trace data)
  - `https://stream.{realm}.signalfx.com/v2/signalflow/execute` (metrics)
- Read `SF_TOKEN` and `SF_REALM` from environment variables
- Parse JSON/SSE responses and output results to stdout
- Print errors to stderr

### What the scripts do NOT do

- No file system writes or modifications
- No subprocess execution (`subprocess`, `os.system`, etc.)
- No dynamic code execution (`eval`, `exec`, `compile`)
- No data sent to any third-party service (only Splunk APIs)
- No credential logging or persistence
- No network requests other than to the configured Splunk realm

### Audit information

| Property | Value |
|----------|-------|
| Total lines of Python code | ~764 lines across 3 files |
| External dependency | `requests` only |
| Script files | `get_topology.py`, `get_trace.py`, `get_service_metrics.py` |

All scripts are short, well-documented, and use only standard Python libraries plus `requests`. You can review the complete source code in the [`skills/splunk-o11y/scripts/`](skills/splunk-o11y/scripts/) directory.

## Troubleshooting

### `Error: SF_TOKEN environment variable is required`

The API token is not configured. Add `SF_TOKEN` to your `settings.local.json` `env` section and restart your Claude Code session.

### `Error: HTTP error: 401 - Unauthorized: Invalid token`

Your API token is invalid or expired. Generate a new token from Splunk Observability Cloud Settings > Access Tokens.

### `Error: Could not connect to Splunk API (realm: us1)`

Check your `SF_REALM` setting. Ensure it matches your Splunk Observability Cloud organization's realm.

### `Error: HTTP error: 429` (Rate limit)

You've exceeded the API rate limit. Wait for the `Retry-After` period indicated in the error message.

### `ModuleNotFoundError: No module named 'requests'`

Install the `requests` library:

```bash
pip install requests
```

### `TypeError` related to `str | None` syntax

Python 3.10+ is required. Check your Python version with `python --version`.

## API Reference

For detailed API documentation, see [`skills/splunk-o11y/references/api_reference.md`](skills/splunk-o11y/references/api_reference.md).

OpenAPI specifications:
- [APM Service Topology API](skills/splunk-o11y/references/apm_service_topology-latest.json)
- [Trace ID API](skills/splunk-o11y/references/trace_id-latest.json)
- [SignalFlow Execute API](skills/splunk-o11y/references/signalflow-latest.json)

## License

[MIT](LICENSE)

---

## 日本語ドキュメント (Japanese)

### 概要

Splunk Observability Cloud APMの機能をClaude Codeから直接利用できるプラグインです。サービストポロジー、トレース、サービスメトリクス（エラー率・レイテンシ・スループット）を取得・分析できます。

### 前提条件

- Splunk Observability Cloudアカウント（APM有効）
- APIアクセストークン（admin, power, または read_only ロール）
- Python 3.10以上
- `requests`ライブラリ（`pip install requests`）

### インストール

```bash
# マーケットプレースを追加
claude plugin marketplace add gentksb/splunk-o11y-claude-plugin

# プラグインをインストール
claude plugin install splunk-o11y
```

### 設定

プラグインのインストール後、`settings.local.json`にSplunk認証情報を設定してください。このファイルはClaude Codeによってバージョン管理から除外されるため、認証情報は安全に保持されます。

```json
{
  "env": {
    "SF_TOKEN": "your-api-token",
    "SF_REALM": "us1"
  }
}
```

設定ファイルの場所はインストールスコープによって異なります：

| スコープ | 設定ファイル |
|---------|------------|
| ユーザースコープ | `~/.claude/settings.local.json` |
| プロジェクトスコープ | `<project>/.claude/settings.local.json` |

既存の`settings.local.json`がある場合は、`env`セクションのみ追記・マージしてください。設定後、新しいClaude Codeセッションから環境変数として自動注入されます。

### 使い方

設定完了後、APM関連の質問（サービストポロジー、トレース、エラー率、レイテンシ、スループットなど）をするとClaude Codeが自動的にこのスキルを使用します。

#### トポロジー取得

```bash
# 全サービスのトポロジー
python scripts/get_topology.py --environment production

# 特定サービスの依存関係
python scripts/get_topology.py --environment production --service my-service
```

#### トレース取得

```bash
# 最新セグメント取得
python scripts/get_trace.py <trace-id>

# セグメント一覧
python scripts/get_trace.py <trace-id> --segments
```

#### サービスメトリクス

```bash
# エラー率
python scripts/get_service_metrics.py --environment production --metric error-rate

# P99レイテンシ
python scripts/get_service_metrics.py --environment production --metric latency --service checkout

# スループット
python scripts/get_service_metrics.py --environment production --metric throughput
```

### セキュリティと透明性

本プラグインのスクリプトは、Splunk Observability Cloud APIへのHTTPリクエストのみを行い、ファイルの書き込み・プロセス実行・動的コード実行は一切行いません。外部依存は`requests`ライブラリのみです。全ソースコードは[`skills/splunk-o11y/scripts/`](skills/splunk-o11y/scripts/)ディレクトリで確認できます。
