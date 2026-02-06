#!/usr/bin/env python3
"""
Splunk Observability Cloud APM Trace API client.

Retrieves trace data from Splunk Observability Cloud APM.

Usage:
    # Get latest segment of a trace (default)
    python get_trace.py <trace_id>

    # Get list of segments for a trace
    python get_trace.py <trace_id> --segments

    # Get specific segment by timestamp
    python get_trace.py <trace_id> --segment-timestamp 1704067200000000

    # Output in NDJSON format
    python get_trace.py <trace_id> --format ndjson

Environment variables:
    SF_TOKEN: Splunk Observability Cloud API token (required)
    SF_REALM: Splunk realm (default: us1)

API Response (Span object fields):
    - traceId, spanId, parentId, serviceName, operationName
    - startTime (ISO-8601), durationMicros
    - tags, processTags, logs, splunk
"""

import argparse
import json
import os
import sys

import requests


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Retrieve APM trace data from Splunk Observability Cloud"
    )
    parser.add_argument(
        "trace_id",
        help="Trace ID to retrieve (required)",
    )

    # Mutually exclusive options for endpoint selection
    endpoint_group = parser.add_mutually_exclusive_group()
    endpoint_group.add_argument(
        "--segments",
        action="store_true",
        help="Get list of segments for the trace",
    )
    endpoint_group.add_argument(
        "--segment-timestamp",
        type=int,
        metavar="TIMESTAMP",
        help="Get specific segment by timestamp (int64 microseconds)",
    )
    endpoint_group.add_argument(
        "--latest",
        action="store_true",
        default=True,
        help="Get latest segment (default behavior)",
    )

    parser.add_argument(
        "--format",
        choices=["json", "ndjson"],
        default="json",
        help="Output format (default: json)",
    )

    return parser.parse_args()


def get_accept_header(output_format: str) -> str:
    """
    Get the Accept header value for the specified output format.

    Args:
        output_format: Output format (json or ndjson)

    Returns:
        Accept header value
    """
    if output_format == "ndjson":
        return "application/x-ndjson"
    return "application/json"


def get_trace_segments(
    token: str,
    realm: str,
    trace_id: str,
    output_format: str,
) -> requests.Response:
    """
    Get list of segments for a trace.

    Args:
        token: Splunk Observability Cloud API token
        realm: Splunk realm (e.g., us1, eu0)
        trace_id: Trace ID
        output_format: Output format (json or ndjson)

    Returns:
        API response

    Raises:
        requests.exceptions.RequestException: On API errors
    """
    url = f"https://api.{realm}.signalfx.com/v2/apm/trace/{trace_id}/segments"

    headers = {
        "X-SF-Token": token,
        "Accept": get_accept_header(output_format),
    }

    response = requests.get(url, headers=headers, timeout=30)
    return response


def get_trace_segment_by_timestamp(
    token: str,
    realm: str,
    trace_id: str,
    segment_timestamp: int,
    output_format: str,
) -> requests.Response:
    """
    Get specific segment by timestamp.

    Args:
        token: Splunk Observability Cloud API token
        realm: Splunk realm (e.g., us1, eu0)
        trace_id: Trace ID
        segment_timestamp: Segment timestamp in microseconds (int64)
        output_format: Output format (json or ndjson)

    Returns:
        API response

    Raises:
        requests.exceptions.RequestException: On API errors
    """
    url = f"https://api.{realm}.signalfx.com/v2/apm/trace/{trace_id}/{segment_timestamp}"

    headers = {
        "X-SF-Token": token,
        "Accept": get_accept_header(output_format),
    }

    response = requests.get(url, headers=headers, timeout=30)
    return response


def get_trace_latest(
    token: str,
    realm: str,
    trace_id: str,
    output_format: str,
) -> requests.Response:
    """
    Get latest segment of a trace.

    Args:
        token: Splunk Observability Cloud API token
        realm: Splunk realm (e.g., us1, eu0)
        trace_id: Trace ID
        output_format: Output format (json or ndjson)

    Returns:
        API response

    Raises:
        requests.exceptions.RequestException: On API errors
    """
    url = f"https://api.{realm}.signalfx.com/v2/apm/trace/{trace_id}/latest"

    headers = {
        "X-SF-Token": token,
        "Accept": get_accept_header(output_format),
    }

    response = requests.get(url, headers=headers, timeout=30)
    return response


def handle_response(response: requests.Response, output_format: str) -> None:
    """
    Handle API response, outputting result or raising error.

    Args:
        response: API response object
        output_format: Output format (json or ndjson)

    Raises:
        SystemExit: On HTTP errors
    """
    if response.status_code == 404:
        print("Error: Trace not found", file=sys.stderr)
        sys.exit(1)

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "unknown")
        print(
            f"Error: Rate limit exceeded. Retry after: {retry_after} seconds",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP error: {e.response.status_code}"
        try:
            error_body = e.response.json()
            if "message" in error_body:
                error_message += f" - {error_body['message']}"
        except (ValueError, KeyError):
            pass
        print(f"Error: {error_message}", file=sys.stderr)
        sys.exit(1)

    # Output based on format
    if output_format == "ndjson":
        # For NDJSON, output raw text as-is
        print(response.text)
    else:
        # For JSON, pretty-print
        try:
            result = response.json()
            print(json.dumps(result, indent=2))
        except ValueError:
            # If response is not valid JSON, output raw text
            print(response.text)


def main():
    """Main entry point."""
    args = parse_args()

    # Get credentials from environment
    token = os.environ.get("SF_TOKEN")
    if not token:
        print("Error: SF_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    realm = os.environ.get("SF_REALM", "us1")

    try:
        # Determine which endpoint to call
        if args.segments:
            response = get_trace_segments(
                token=token,
                realm=realm,
                trace_id=args.trace_id,
                output_format=args.format,
            )
        elif args.segment_timestamp:
            response = get_trace_segment_by_timestamp(
                token=token,
                realm=realm,
                trace_id=args.trace_id,
                segment_timestamp=args.segment_timestamp,
                output_format=args.format,
            )
        else:
            # Default: get latest
            response = get_trace_latest(
                token=token,
                realm=realm,
                trace_id=args.trace_id,
                output_format=args.format,
            )

        handle_response(response, args.format)

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to Splunk API (realm: {realm})", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("Error: Request timed out", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: Request failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
