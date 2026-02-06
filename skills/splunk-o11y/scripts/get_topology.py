#!/usr/bin/env python3
"""
Splunk Observability Cloud APM Service Topology API client.

Retrieves service topology or dependencies from Splunk Observability Cloud APM.

Usage:
    # Get full topology for an environment
    python get_topology.py --environment production

    # Get topology with custom time range
    python get_topology.py --environment production \
        --start-time 2024-01-01T00:00:00Z --end-time 2024-01-01T12:00:00Z

    # Get dependencies for a specific service
    python get_topology.py --environment production --service my-service

Environment variables:
    SF_TOKEN: Splunk Observability Cloud API token (required)
    SF_REALM: Splunk realm (default: us1)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Retrieve APM service topology from Splunk Observability Cloud"
    )
    parser.add_argument(
        "--environment",
        required=True,
        help="Environment name (required)",
    )
    parser.add_argument(
        "--start-time",
        help="Start time in ISO8601 format (default: 1 hour ago)",
    )
    parser.add_argument(
        "--end-time",
        help="End time in ISO8601 format (default: now)",
    )
    parser.add_argument(
        "--service",
        help="Service name to get dependencies for (optional)",
    )
    return parser.parse_args()


def get_time_range(start_time_str: str | None, end_time_str: str | None) -> str:
    """
    Build time range string in the format required by the API.

    Args:
        start_time_str: Start time in ISO8601 format, or None for 1 hour ago
        end_time_str: End time in ISO8601 format, or None for now

    Returns:
        Time range string in format "start_iso/end_iso"
    """
    now = datetime.now(timezone.utc)

    if end_time_str:
        end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
    else:
        end_time = now

    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
    else:
        start_time = end_time - timedelta(hours=1)

    # Format as ISO8601 with Z suffix
    start_iso = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    return f"{start_iso}/{end_iso}"


def get_topology(
    token: str,
    realm: str,
    environment: str,
    time_range: str,
    service_name: str | None = None,
) -> dict:
    """
    Call the APM Service Topology API.

    Args:
        token: Splunk Observability Cloud API token
        realm: Splunk realm (e.g., us1, eu0)
        environment: Environment name to filter by
        time_range: Time range in format "start_iso/end_iso"
        service_name: Optional service name for dependency lookup

    Returns:
        API response as dictionary

    Raises:
        requests.exceptions.RequestException: On API errors
    """
    base_url = f"https://api.{realm}.signalfx.com/v2"

    if service_name:
        url = f"{base_url}/apm/topology/{quote(service_name, safe='')}"
    else:
        url = f"{base_url}/apm/topology"

    headers = {
        "X-SF-Token": token,
        "Content-Type": "application/json",
    }

    payload = {
        "timeRange": time_range,
        "tagFilters": [
            {
                "name": "sf_environment",
                "operator": "equals",
                "scope": "GLOBAL",
                "value": environment,
            }
        ],
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    return response.json()


def main():
    """Main entry point."""
    args = parse_args()

    # Get credentials from environment
    token = os.environ.get("SF_TOKEN")
    if not token:
        print("Error: SF_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    realm = os.environ.get("SF_REALM", "us1")

    # Build time range
    try:
        time_range = get_time_range(args.start_time, args.end_time)
    except ValueError as e:
        print(f"Error: Invalid time format: {e}", file=sys.stderr)
        sys.exit(1)

    # Call API
    try:
        result = get_topology(
            token=token,
            realm=realm,
            environment=args.environment,
            time_range=time_range,
            service_name=args.service,
        )
        print(json.dumps(result, indent=2))
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
