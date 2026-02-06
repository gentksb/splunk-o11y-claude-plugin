#!/usr/bin/env python3
"""
Splunk Observability Cloud APM Service Metrics via SignalFlow API.

Retrieves APM service metrics (error rate, latency, throughput) using
the SignalFlow execute API.

Usage:
    # Get error rate for all services in an environment
    python get_service_metrics.py --environment production --metric error-rate

    # Get P99 latency for a specific service
    python get_service_metrics.py --environment production --metric latency --service checkout

    # Get throughput (requests/sec) with custom time range
    python get_service_metrics.py --environment production --metric throughput \
        --start-time 2024-01-01T00:00:00Z --end-time 2024-01-01T01:00:00Z

Environment variables:
    SF_TOKEN: Splunk Observability Cloud API token (required)
    SF_REALM: Splunk realm (default: us1)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

METRIC_TYPES = {
    "error-rate": {
        "description": "Error rate per service (%)",
        "program": (
            "errors = data('service.request.count', "
            "filter=filter('sf_error', 'true') and filter('sf_environment', '{env}'){svc_filter})"
            ".sum(by=['sf_service']).publish('errors')\n"
            "total = data('service.request.count', "
            "filter=filter('sf_environment', '{env}'){svc_filter})"
            ".sum(by=['sf_service']).publish('total')"
        ),
    },
    "latency": {
        "description": "Request duration P99 per service (ms)",
        "program": (
            "data('service.request.duration.ns.p99', "
            "filter=filter('sf_environment', '{env}'){svc_filter})"
            ".mean(by=['sf_service']).publish('latency_p99')"
        ),
    },
    "throughput": {
        "description": "Request throughput per service (req/sec)",
        "program": (
            "data('service.request.count', "
            "filter=filter('sf_environment', '{env}'){svc_filter})"
            ".sum(by=['sf_service']).publish('throughput')"
        ),
    },
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Retrieve APM service metrics from Splunk Observability Cloud"
    )
    parser.add_argument("--environment", required=True, help="Environment name")
    parser.add_argument(
        "--metric",
        required=True,
        choices=list(METRIC_TYPES.keys()),
        help="Metric type to retrieve",
    )
    parser.add_argument("--service", help="Filter by service name (optional)")
    parser.add_argument("--start-time", help="Start time ISO8601 (default: 10min ago)")
    parser.add_argument("--end-time", help="End time ISO8601 (default: now)")
    parser.add_argument(
        "--resolution", type=int, default=60000, help="Resolution in ms (default: 60000)"
    )
    return parser.parse_args()


def iso_to_epoch_ms(iso_str: str) -> int:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def build_program(metric_type: str, environment: str, service: str | None) -> str:
    svc_filter = ""
    if service:
        svc_filter = f" and filter('sf_service', '{service}')"
    template = METRIC_TYPES[metric_type]["program"]
    return template.format(env=environment, svc_filter=svc_filter)


def parse_sse_stream(response: requests.Response) -> dict:
    """Parse SSE stream from SignalFlow execute API into structured data.

    SignalFlow SSE uses multi-line data fields:
        event: metadata
        data: {
        data:   "tsId": "abc",
        data:   ...
        data: }
    """
    metadata = {}  # tsid -> metadata
    data_points = {}  # tsid -> list of (timestamp, value)
    current_event = None
    data_buffer = []

    def flush_buffer():
        if not data_buffer or not current_event:
            return
        raw = "\n".join(data_buffer)
        data_buffer.clear()
        try:
            obj = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return

        if current_event == "metadata":
            tsid = obj.get("tsId")
            if tsid:
                props = obj.get("properties", {})
                metadata[tsid] = {
                    "sf_service": props.get("sf_service", ""),
                    "label": props.get("sf_streamLabel", ""),
                }
        elif current_event == "data":
            raw_data = obj.get("data", [])
            ts = obj.get("logicalTimestampMs")
            if isinstance(raw_data, list):
                for item in raw_data:
                    tid = item.get("tsId")
                    value = item.get("value")
                    if tid:
                        if tid not in data_points:
                            data_points[tid] = []
                        data_points[tid].append({"timestamp": ts, "value": value})

    for line in response.iter_lines(decode_unicode=True):
        if line is None or line == "":
            flush_buffer()
            current_event = None
            continue
        if line.startswith("event:"):
            flush_buffer()
            current_event = line[6:].strip()
            continue
        if line.startswith("data:"):
            data_buffer.append(line[5:])

    flush_buffer()
    return {"metadata": metadata, "data_points": data_points}


def aggregate_results(parsed: dict, metric_type: str) -> list[dict]:
    """Aggregate parsed SSE data into per-service results."""
    service_data: dict[str, dict[str, list]] = {}

    for tsid, points in parsed["data_points"].items():
        meta = parsed["metadata"].get(tsid, {})
        svc = meta.get("sf_service", "unknown")
        label = meta.get("label", "")
        if svc not in service_data:
            service_data[svc] = {}
        if label not in service_data[svc]:
            service_data[svc][label] = []
        service_data[svc][label].extend(points)

    results = []
    for svc, labels in sorted(service_data.items()):
        if not svc:
            continue
        entry: dict = {"service": svc}

        if metric_type == "error-rate":
            errors_vals = [p["value"] for p in labels.get("errors", []) if p["value"] is not None]
            total_vals = [p["value"] for p in labels.get("total", []) if p["value"] is not None]
            total_sum = sum(total_vals)
            error_sum = sum(errors_vals)
            if total_sum > 0:
                entry["error_rate_pct"] = round(error_sum / total_sum * 100, 2)
                entry["error_count"] = error_sum
                entry["total_count"] = total_sum
            else:
                entry["error_rate_pct"] = 0.0
                entry["error_count"] = 0
                entry["total_count"] = 0
        elif metric_type == "latency":
            vals = []
            for label_points in labels.values():
                vals.extend([p["value"] for p in label_points if p["value"] is not None])
            if vals:
                entry["p99_ms"] = round(sum(vals) / len(vals) / 1_000_000, 2)
        elif metric_type == "throughput":
            vals = []
            for label_points in labels.values():
                vals.extend([p["value"] for p in label_points if p["value"] is not None])
            if vals:
                entry["requests_total"] = sum(vals)
                entry["avg_per_interval"] = round(sum(vals) / len(vals), 2)

        results.append(entry)

    return results


def main():
    args = parse_args()

    token = os.environ.get("SF_TOKEN")
    if not token:
        print("Error: SF_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    realm = os.environ.get("SF_REALM", "us1")

    now = datetime.now(timezone.utc)
    if args.end_time:
        stop_ms = iso_to_epoch_ms(args.end_time)
    else:
        stop_ms = int(now.timestamp() * 1000)

    if args.start_time:
        start_ms = iso_to_epoch_ms(args.start_time)
    else:
        start_ms = int((now - timedelta(minutes=10)).timestamp() * 1000)

    program = build_program(args.metric, args.environment, args.service)

    url = f"https://stream.{realm}.signalfx.com/v2/signalflow/execute"
    headers = {
        "Content-Type": "application/json",
        "X-SF-Token": token,
    }
    params = {
        "start": start_ms,
        "stop": stop_ms,
        "resolution": args.resolution,
        "immediate": "true",
    }
    body = {"programText": program}

    try:
        resp = requests.post(
            url, headers=headers, params=params, json=body, stream=True, timeout=60
        )
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        msg = f"HTTP error: {e.response.status_code}"
        try:
            msg += f" - {e.response.json().get('message', '')}"
        except Exception:
            pass
        print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    parsed = parse_sse_stream(resp)
    results = aggregate_results(parsed, args.metric)

    output = {
        "metric_type": args.metric,
        "description": METRIC_TYPES[args.metric]["description"],
        "environment": args.environment,
        "time_range": {
            "start_ms": start_ms,
            "stop_ms": stop_ms,
        },
        "results": results,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
