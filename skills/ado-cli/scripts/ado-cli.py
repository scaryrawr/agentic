#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Parse Azure DevOps URLs and upload PR attachments."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEVOPS_RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798"


def normalize_organization(value: str) -> dict[str, str]:
    """Normalize an Azure DevOps organization name or URL."""
    raw = value.rstrip("/")
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urllib.parse.urlparse(raw)
        if parsed.hostname == "dev.azure.com":
            parts = [part for part in parsed.path.split("/") if part]
            if not parts:
                sys.exit(f"error: could not determine organization from {value}")
            org = parts[0]
        elif parsed.hostname and parsed.hostname.endswith(".visualstudio.com"):
            org = parsed.hostname.removesuffix(".visualstudio.com")
        else:
            sys.exit(f"error: unsupported Azure DevOps organization URL: {value}")
    else:
        org = raw
    return {"organization": org, "organizationUrl": f"https://dev.azure.com/{org}"}


def run(command: list[str]) -> str:
    """Run a command and return stdout, preserving stderr context on failure."""
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or str(exc)).strip()
        sys.exit(f"error: {' '.join(command)} failed: {details}")


def parse_azure_devops_url(raw_url: str) -> dict[str, Any]:
    """Parse a supported Azure DevOps URL and identify the target skill."""
    parsed = urllib.parse.urlparse(raw_url)
    is_visual_studio = (parsed.hostname or "").endswith(".visualstudio.com")
    is_dev_azure = parsed.hostname == "dev.azure.com"
    if not is_dev_azure and not is_visual_studio:
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

    project = segments[0] if segments else None
    resource_section = segments[1] if len(segments) > 1 else None
    result: dict[str, Any] = {
        "url": raw_url,
        "host": parsed.hostname,
        "organization": organization,
        "organizationUrl": f"https://dev.azure.com/{organization}",
        "project": project,
        "resourceType": "unknown",
        "routeSkill": "unknown",
        "isVisualStudioHost": is_visual_studio,
    }

    if resource_section == "_git":
        repository_index = 3 if len(segments) > 2 and segments[2] == "_optimized" else 2
        if len(segments) <= repository_index:
            return result
        repository = segments[repository_index]
        next_segment = segments[repository_index + 1] if len(segments) > repository_index + 1 else None
        if next_segment == "pullrequest":
            try:
                pull_request_id = int(segments[repository_index + 2])
            except (IndexError, ValueError):
                sys.exit(f"error: could not determine pull request id from {raw_url}")
            result.update(
                {
                    "repository": repository,
                    "resourceType": "pull-request",
                    "resourceId": pull_request_id,
                    "pullRequestId": pull_request_id,
                    "routeSkill": "ado-pr",
                }
            )
            return result

    if resource_section == "_workitems" and len(segments) > 3 and segments[2] == "edit":
        try:
            work_item_id = int(segments[3])
        except ValueError:
            sys.exit(f"error: could not determine work item id from {raw_url}")
        result.update(
            {
                "resourceType": "work-item",
                "resourceId": work_item_id,
                "workItemId": work_item_id,
                "routeSkill": "ado-work-items",
            }
        )
    return result


def upload_attachment(args: argparse.Namespace) -> None:
    """Upload a pull request attachment with the Azure DevOps REST API."""
    organization = normalize_organization(args.org)["organization"]
    file_path = Path(args.file)
    if not file_path.is_file():
        sys.exit(f"error: {file_path} is not a regular file")
    file_name = args.file_name or file_path.name
    token = run(
        [
            "az",
            "account",
            "get-access-token",
            "--resource",
            DEVOPS_RESOURCE,
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ]
    )
    project = urllib.parse.quote(args.project, safe="")
    file_name_quoted = urllib.parse.quote(file_name, safe="")
    url = (
        f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/"
        f"{args.repository_id}/pullRequests/{args.pull_request_id}/attachments/{file_name_quoted}"
        "?api-version=7.1"
    )
    request = urllib.request.Request(
        url,
        data=file_path.read_bytes(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        sys.exit(f"error: attachment upload failed ({exc.code}): {details}")
    print(json.dumps({"fileName": file_name, "filePath": str(file_path), "id": payload.get("id"), "url": payload.get("url")}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    parse_url = subparsers.add_parser("parse-url")
    parse_url.add_argument("url")
    upload = subparsers.add_parser("upload-attachment")
    upload.add_argument("--org", required=True)
    upload.add_argument("--project", required=True)
    upload.add_argument("--repository-id", required=True)
    upload.add_argument("--pull-request-id", required=True)
    upload.add_argument("--file", required=True)
    upload.add_argument("--file-name", default="")
    args = parser.parse_args()

    if args.command == "parse-url":
        print(json.dumps(parse_azure_devops_url(args.url), indent=2))
    elif args.command == "upload-attachment":
        upload_attachment(args)


if __name__ == "__main__":
    main()
