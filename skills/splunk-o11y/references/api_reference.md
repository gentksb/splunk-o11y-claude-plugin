# Splunk Observability Cloud APM API Reference

## Overview

API for retrieving service dependencies and topology.

**Base URL**: `https://api.{REALM}.signalfx.com/v2`

**Required permissions**: admin, power, or read_only role

---

## 1. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v2/apm/topology` | Retrieve topology for all services in an environment |
| POST | `/v2/apm/topology/{serviceName}` | Retrieve dependencies for a specific service |

---

## 2. Authentication

The `X-SF-Token` header is required for all requests.

```
X-SF-Token: <your_access_token>
```

**Token types**: Organization Access Token (with API permissions) or Session Token

---

## 3. Request Body

### Common Fields

```json
{
  "timeRange": "<start_time>/<end_time>",
  "tagFilters": [...]
}
```

### timeRange (required)

Two ISO 8601 timestamps separated by a slash.

```
"timeRange": "2021-01-23T12:00:00Z/2021-01-24T00:00:00Z"
```

**Constraints**:
- Minimum: 5 minutes
- Maximum: trace retention period
- Start time < End time

### tagFilters (optional)

#### equals operator

Filter by a single value.

```json
{
  "name": "sf_environment",
  "operator": "equals",
  "scope": "GLOBAL",
  "value": "production"
}
```

#### in operator

Filter by multiple values.

```json
{
  "name": "sf_environment",
  "operator": "in",
  "scope": "GLOBAL",
  "values": ["production", "staging"]
}
```

### scope Values

| Value | Description |
|-------|-------------|
| `GLOBAL` | Matches the first occurrence across all spans |
| `TIER` | Matches the first occurrence of service-tier spans |
| `INCOMING` | Matches the value of incoming edge spans for service-tier spans |
| `SPAN` | Matches tags on each span in the trace |

### Supported Tag Names

- `sf_service` - Service name
- `sf_environment` - Environment name
- `sf_httpMethod` - HTTP method
- `sf_kind` - Span kind
- Custom indexed tags

---

## 4. Response Structure

### POST /v2/apm/topology

Returns the topology for all services in graph format (up to 1,000 objects).

```json
{
  "nodes": [
    {
      "serviceName": "checkout-service",
      "inferred": false,
      "type": "service"
    }
  ],
  "edges": [
    {
      "fromNode": "frontend",
      "toNode": "checkout-service"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `nodes` | array | List of services |
| `nodes[].serviceName` | string | Service name |
| `nodes[].inferred` | boolean | Whether the service is inferred |
| `nodes[].type` | string | `service`, `database`, `pubsub` |
| `edges` | array | Connections between services |
| `edges[].fromNode` | string | Source service |
| `edges[].toNode` | string | Destination service |

### POST /v2/apm/topology/{serviceName}

Returns the inbound/outbound dependencies for the specified service.

```json
{
  "inbound": ["frontend", "api-gateway"],
  "outbound": ["database", "cache"],
  "services": [
    {
      "serviceName": "frontend",
      "inferred": false,
      "type": "service"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `inbound` | array | Array of service names that call this service |
| `outbound` | array | Array of service names that this service calls |
| `services` | array | Detailed information about related services |

**Note**: If the serviceName does not exist, a 200 status with an empty response is returned.

---

## 5. Error Codes and Solutions

### 400 Bad Request

| Message | Solution |
|---------|----------|
| `timeRange is required` | Add the timeRange field |
| `Invalid delimiter used to split time range` | Use a slash (/) as delimiter |
| `Invalid time range` | Verify ISO 8601 format |
| `time range must not be negative` | Ensure start time < end time |
| `time range must be more than or equal to 5 minutes` | Specify a range of 5 minutes or more |
| `time range must be less than or equal to the trace retention limit` | Keep within the retention period |
| `name is a mandatory field` | Add name to tagFilter |
| `scope is a mandatory field` | Add scope to tagFilter |
| `value is a mandatory field` | value is required for equals operator |
| `values is a mandatory field` | values is required for in operator |
| `unsupported filter name` | Use a supported tag name |
| `Invalid tag filter operator value` | Use equals or in |

### 401 Unauthorized

```json
{
  "code": 401,
  "message": "Unauthorized: Invalid token"
}
```

**Solution**: Verify the X-SF-Token value and use a valid token.

---

## 6. Sample Requests

### Get Topology for All Services

```bash
curl -X POST "https://api.us1.signalfx.com/v2/apm/topology" \
  -H "Content-Type: application/json" \
  -H "X-SF-Token: YOUR_ACCESS_TOKEN" \
  -d '{
    "timeRange": "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z",
    "tagFilters": [
      {
        "name": "sf_environment",
        "operator": "equals",
        "scope": "GLOBAL",
        "value": "production"
      }
    ]
  }'
```

### Get Dependencies for a Specific Service

```bash
curl -X POST "https://api.us1.signalfx.com/v2/apm/topology/checkout-service" \
  -H "Content-Type: application/json" \
  -H "X-SF-Token: YOUR_ACCESS_TOKEN" \
  -d '{
    "timeRange": "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z",
    "tagFilters": [
      {
        "name": "sf_environment",
        "operator": "equals",
        "scope": "GLOBAL",
        "value": "production"
      }
    ]
  }'
```

### Filter by Multiple Environments

```bash
curl -X POST "https://api.us1.signalfx.com/v2/apm/topology" \
  -H "Content-Type: application/json" \
  -H "X-SF-Token: YOUR_ACCESS_TOKEN" \
  -d '{
    "timeRange": "2024-01-01T00:00:00Z/2024-01-01T01:00:00Z",
    "tagFilters": [
      {
        "name": "sf_environment",
        "operator": "in",
        "scope": "GLOBAL",
        "values": ["production", "staging"]
      }
    ]
  }'
```

---

## 7. Trace ID API

API for retrieving span information for a specific trace by specifying a trace ID.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v2/apm/trace/{traceId}/segments` | Get list of segment timestamps for a trace |
| GET | `/v2/apm/trace/{traceId}/{segmentTimestamp}` | Get spans for a specific segment |
| GET | `/v2/apm/trace/{traceId}/latest` | Get spans for the latest segment |

### Response Structure

#### GET /v2/apm/trace/{traceId}/segments

Returns an array of segment timestamps.

| Field | Type | Description |
|-------|------|-------------|
| `segments` | array[int64] | Array of timestamps |

#### GET /v2/apm/trace/{traceId}/{segmentTimestamp} and /latest

Returns an array of Span objects.

| Field | Type | Description |
|-------|------|-------------|
| `traceId` | string | Trace ID (hexadecimal string) |
| `spanId` | string | Span ID (hexadecimal string) |
| `parentId` | string | Parent span ID (hexadecimal string) |
| `serviceName` | string | Service name |
| `operationName` | string | Operation name |
| `startTime` | string | Start time (ISO-8601 format) |
| `durationMicros` | int64 | Duration (microseconds) |
| `tags` | object | Span tags (key-value) |
| `processTags` | object | Process tags (key-value) |
| `logs` | array | Array of Log objects |

### Accept Header

| Value | Description |
|-------|-------------|
| `application/json` | JSON array (default) |
| `application/x-ndjson` | Newline-delimited JSON |

### Error Codes

| Code | Description |
|------|-------------|
| 404 | Trace not found |
| 429 | Rate limit exceeded |

### Sample Requests

#### Get List of Segment Timestamps

```bash
curl -X GET "https://api.us1.signalfx.com/v2/apm/trace/abc123def456/segments" \
  -H "X-SF-Token: YOUR_ACCESS_TOKEN"
```

#### Get Spans for a Specific Segment

```bash
curl -X GET "https://api.us1.signalfx.com/v2/apm/trace/abc123def456/1704067200000" \
  -H "X-SF-Token: YOUR_ACCESS_TOKEN" \
  -H "Accept: application/json"
```

#### Get Spans for the Latest Segment

```bash
curl -X GET "https://api.us1.signalfx.com/v2/apm/trace/abc123def456/latest" \
  -H "X-SF-Token: YOUR_ACCESS_TOKEN"
```

#### Get in NDJSON Format

```bash
curl -X GET "https://api.us1.signalfx.com/v2/apm/trace/abc123def456/latest" \
  -H "X-SF-Token: YOUR_ACCESS_TOKEN" \
  -H "Accept: application/x-ndjson"
```

---

## 8. SignalFlow Execute API

API for executing SignalFlow programs and retrieving real-time or historical metrics data as an SSE (Server-Sent Events) stream.

**Base URL**: `https://stream.{REALM}.signalfx.com/v2`

### Endpoint

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v2/signalflow/execute` | Execute a SignalFlow program |

### Request

**Headers**:
```
Content-Type: application/json
X-SF-Token: <your_access_token>
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start` | int64 | Yes | Start time (epoch milliseconds) |
| `stop` | int64 | No | End time (epoch milliseconds). Omit for real-time streaming |
| `resolution` | int64 | No | Data point resolution (milliseconds) |
| `immediate` | boolean | No | Set to `true` for immediate result return (for historical data) |

**Request Body**:

```json
{
  "programText": "data('service.request.count', filter=filter('sf_environment', 'production')).sum(by=['sf_service']).publish('throughput')"
}
```

### SSE Response Format

The response is returned as an SSE (Server-Sent Events) stream.

#### Wire Format

**Important**: In SignalFlow SSE, a single JSON object can span multiple `data:` lines. This differs from standard SSE (one JSON per line), so take note.

```
event: metadata
data:  {
data:    "properties" : {
data:      "sf_service" : "checkout",
data:      "sf_streamLabel" : "throughput"
data:    },
data:    "tsId" : "AAAAAF0-GPM"
data:  }
                          <- empty line (event delimiter)
event: data
data:  {
data:    "data" : [ {
data:      "tsId" : "AAAAAF0-GPM",
data:      "value" : 82
data:    } ],
data:    "logicalTimestampMs" : 1770338520000
data:  }
```

Key points for parser implementation:
- Strip the `data:` prefix (5 characters) from each line and accumulate the remainder in a buffer
- **Events are delimited by empty lines**. When an empty line is detected, join the buffer (`\n`.join) and parse as JSON
- `event:` lines announce a new event type. `data:` lines belong to the current `event` type
- `iter_lines()` may return empty lines as `""` or `None`, so handle both cases

#### Event Types and Ordering

The stream returns events in the following order:

| Order | Event | Description |
|-------|-------|-------------|
| 1 | `control-message` | Stream control such as `STREAM_START`, `JOB_START` |
| 2 | `metadata` | Metadata for each time series (tsId). **All metadata arrives first** |
| 3 | `data` | Data points. One event per timestamp |
| 4 | `message` | Informational/warning messages (interspersed between data points) |
| End | `control-message` | Stream completion with `END_OF_CHANNEL` |

#### metadata Event Structure

```json
{
  "properties": {
    "sf_service": "checkout",
    "sf_environment": "production",
    "sf_streamLabel": "throughput",
    "sf_originatingMetric": "service.request.count",
    "sf_resolutionMs": 60000
  },
  "tsId": "AAAAAF0-GPM"
}
```

- `tsId`: Unique identifier for the time series. Subsequent `data` events will contain values corresponding to this ID
- `properties.sf_streamLabel`: The label specified by `.publish('label')` in the SignalFlow program
- `properties.sf_service`: For APM metrics, contains the service name

#### data Event Structure

```json
{
  "data": [
    {"tsId": "AAAAAF0-GPM", "value": 82},
    {"tsId": "AAAAABr7PB8", "value": 206}
  ],
  "logicalTimestampMs": 1770338520000,
  "maxDelayMs": 10000
}
```

**Note: The `data` field is a list** (`[{tsId, value}, ...]`), not a dict (`{tsId: value, ...}`). A single `data` event contains values for multiple time series.

### SignalFlow Program Examples for APM Metrics

#### Error Rate

```
errors = data('service.request.count',
  filter=filter('sf_error', 'true') and filter('sf_environment', 'production'))
  .sum(by=['sf_service']).publish('errors')
total = data('service.request.count',
  filter=filter('sf_environment', 'production'))
  .sum(by=['sf_service']).publish('total')
```

#### P99 Latency

```
data('service.request.duration.ns.p99',
  filter=filter('sf_environment', 'production'))
  .mean(by=['sf_service']).publish('latency_p99')
```

#### Throughput

```
data('service.request.count',
  filter=filter('sf_environment', 'production'))
  .sum(by=['sf_service']).publish('throughput')
```

### Service Filtering

To filter by a specific service, add `filter('sf_service', 'name')`:

```
data('service.request.count',
  filter=filter('sf_environment', 'production') and filter('sf_service', 'checkout'))
  .sum(by=['sf_service']).publish('throughput')
```
