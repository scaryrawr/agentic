#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Build Azure Boards helper payloads."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
import urllib.parse
from typing import Any


def parse_work_item_url(raw_url: str) -> dict[str, Any]:
    """Parse a supported Azure DevOps work item URL."""
    parsed = urllib.parse.urlparse(raw_url)
    is_visual_studio = (parsed.hostname or "").endswith(".visualstudio.com")
    is_dev_azure = parsed.hostname == "dev.azure.com"
    if not is_visual_studio and not is_dev_azure:
        sys.exit(f"error: unsupported Azure DevOps host: {parsed.hostname}")

    segments = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
    if is_dev_azure:
        if not segments:
            sys.exit(f"error: could not determine organization from {raw_url}")
        organization, segments = segments[0], segments[1:]
    else:
        organization = (parsed.hostname or "").removesuffix(".visualstudio.com")
        if segments[:1] == ["DefaultCollection"]:
            segments = segments[1:]

    if len(segments) < 4 or segments[1] != "_workitems" or segments[2] != "edit":
        sys.exit(f"error: URL is not a recognized work item URL: {raw_url}")
    try:
        work_item_id = int(segments[3])
    except ValueError:
        sys.exit(f"error: could not determine work item id from {raw_url}")

    return {
        "url": raw_url,
        "host": parsed.hostname,
        "organization": organization,
        "organizationUrl": f"https://dev.azure.com/{organization}",
        "project": segments[0],
        "workItemId": work_item_id,
    }


def escape_wiql_string(value: str) -> str:
    """Escape a value for a WIQL string literal."""
    return "'" + value.replace("'", "''") + "'"


def build_wiql(args: argparse.Namespace) -> dict[str, Any]:
    """Build a WIQL query and equivalent az command arguments."""
    fields = args.fields or "System.Id,System.Title,System.State"
    clauses: list[str] = []
    if args.assigned_to:
        assigned = "@Me" if args.assigned_to == "@Me" else escape_wiql_string(args.assigned_to)
        clauses.append(f"[System.AssignedTo] = {assigned}")
    if args.state:
        clauses.append(f"[System.State] IN ({', '.join(escape_wiql_string(value) for value in args.state)})")
    for state in args.exclude_state:
        clauses.append(f"[System.State] <> {escape_wiql_string(state)}")
    if args.type:
        clauses.append(f"[System.WorkItemType] IN ({', '.join(escape_wiql_string(value) for value in args.type)})")
    clauses.extend(args.extra_clause)

    select_fields = ", ".join(f"[{field.strip()}]" for field in fields.split(","))
    where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    wiql = f"SELECT {select_fields} FROM workitems{where_clause} ORDER BY [System.ChangedDate] DESC"
    executable = "az"
    command_args = ["boards", "query", "--wiql", wiql, "--detect", "true"]
    posix_command = " ".join(shlex.quote(part) for part in [executable, *command_args])
    return {"wiql": wiql, "executable": executable, "commandArgs": command_args, "posixCommand": posix_command}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    parse_url = subparsers.add_parser("parse-url")
    parse_url.add_argument("url")
    wiql = subparsers.add_parser("wiql")
    wiql.add_argument("--assigned-to", default="")
    wiql.add_argument("--state", action="append", default=[])
    wiql.add_argument("--exclude-state", action="append", default=[])
    wiql.add_argument("--type", action="append", default=[])
    wiql.add_argument("--fields", default="")
    wiql.add_argument("--extra-clause", action="append", default=[])
    args = parser.parse_args()

    if args.command == "parse-url":
        print(json.dumps(parse_work_item_url(args.url), indent=2))
    elif args.command == "wiql":
        print(json.dumps(build_wiql(args), indent=2))


if __name__ == "__main__":
    main()
