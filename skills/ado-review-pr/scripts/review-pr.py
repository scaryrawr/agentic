#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Azure DevOps PR review helper utilities."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
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


def run_json(command: list[str]) -> Any:
    """Run an az command and decode JSON output."""
    return json.loads(run([*command, "--output", "json"]))


def token() -> str:
    """Return an Azure DevOps access token from Azure CLI."""
    return run(["az", "account", "get-access-token", "--resource", DEVOPS_RESOURCE, "--query", "accessToken", "-o", "tsv"])


def request_json(url: str, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None) -> Any:
    """Call an Azure DevOps JSON endpoint and return decoded JSON."""
    request = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        sys.exit(f"error: request failed ({exc.code}): {details}")
    return json.loads(payload) if payload else {}


def scope_args(args: argparse.Namespace) -> list[str]:
    """Return az scope arguments from --org or --detect."""
    if args.org:
        return ["--org", normalize_organization(args.org)["organizationUrl"]]
    return ["--detect", args.detect]


def parse_remote_organization(remote_url: str) -> str | None:
    """Extract an Azure DevOps organization from a git remote URL."""
    patterns = (
        r"https://dev.azure.com/",
        r"https://",
        r"ssh://git@ssh.dev.azure.com:v3/",
        r"git@ssh.dev.azure.com:v3/",
    )
    if remote_url.startswith(patterns[0]):
        parts = remote_url[len(patterns[0]):].split("/")
        return parts[0] if parts else None
    if remote_url.startswith(patterns[1]) and ".visualstudio.com/" in remote_url:
        host = urllib.parse.urlparse(remote_url).hostname or ""
        return host.removesuffix(".visualstudio.com")
    for prefix in patterns[2:]:
        if remote_url.startswith(prefix):
            parts = remote_url[len(prefix):].split("/")
            return parts[0] if parts else None
    return None


def strip_refs_heads(value: str | None) -> str | None:
    """Strip refs/heads/ from a branch ref."""
    prefix = "refs/heads/"
    return value[len(prefix):] if value and value.startswith(prefix) else value


def parse_line_number(value: int, flag: str) -> int:
    """Validate a positive line number."""
    if value < 1:
        sys.exit(f"error: expected {flag} to be a positive integer")
    return value


def normalize_ado_file_path(file_path: str) -> str:
    """Normalize a repository-relative file path to Azure DevOps slash form."""
    slash_path = file_path.replace("\\", "/")
    if (len(slash_path) > 1 and slash_path[1] == ":") or slash_path.startswith("//"):
        sys.exit("error: --file-path must be repository-relative, not a local absolute path")
    trimmed = "/".join(part for part in slash_path.split("/") if part)
    if not trimmed:
        sys.exit("error: --file-path cannot be empty")
    return f"/{trimmed}"


def resolve_out_file(value: str) -> Path:
    """Resolve the optional thread payload output file."""
    if value != "auto":
        return Path(value)
    directory = Path(tempfile.mkdtemp(prefix="ado-review-"))
    return directory / "thread.json"


def build_thread_payload(args: argparse.Namespace) -> dict[str, Any]:
    """Build an Azure DevOps pull request thread payload."""
    payload: dict[str, Any] = {
        "comments": [{"parentCommentId": 0, "content": args.content, "commentType": "text"}],
        "status": args.status,
    }
    if args.file_path:
        if args.line_start is None:
            sys.exit("error: file-specific thread payloads require --line-start")
        line_start = parse_line_number(args.line_start, "--line-start")
        line_end = parse_line_number(args.line_end or line_start, "--line-end")
        if line_end < line_start:
            sys.exit("error: --line-end must be greater than or equal to --line-start")
        payload["threadContext"] = {
            "filePath": normalize_ado_file_path(args.file_path),
            "rightFileStart": {"line": line_start, "offset": 0},
            "rightFileEnd": {"line": line_end, "offset": 0},
        }
    return payload


def eligibility(args: argparse.Namespace) -> None:
    """Print review eligibility and compact PR metadata."""
    details = run_json(["az", "repos", "pr", "show", "--id", args.id, *scope_args(args)])
    repo = details.get("repository") or {}
    project = repo.get("project") or {}
    status = details.get("status") or "unknown"
    payload = {
        "pullRequestId": details.get("pullRequestId"),
        "title": details.get("title"),
        "status": status,
        "isDraft": details.get("isDraft", False),
        "eligible": status == "active" and not details.get("isDraft", False),
        "sourceBranch": details.get("sourceRefName"),
        "sourceBranchName": strip_refs_heads(details.get("sourceRefName")),
        "targetBranch": details.get("targetRefName"),
        "targetBranchName": strip_refs_heads(details.get("targetRefName")),
        "repositoryId": repo.get("id"),
        "repositoryName": repo.get("name"),
        "projectId": project.get("id"),
        "projectName": project.get("name"),
        "lastMergeSourceCommit": (details.get("lastMergeSourceCommit") or {}).get("commitId"),
        "reviewers": [
            {"reviewer": reviewer.get("uniqueName") or reviewer.get("displayName"), "vote": reviewer.get("vote", 0)}
            for reviewer in details.get("reviewers", [])
        ],
        "url": details.get("url"),
    }
    print(json.dumps(payload, indent=2))


def sync_labels(args: argparse.Namespace) -> None:
    """Synchronize AI review labels on an Azure DevOps pull request."""
    if not args.model:
        sys.exit("error: provide at least one --model value")
    details = run_json(["az", "repos", "pr", "show", "--id", args.id, *scope_args(args)])
    repo = details.get("repository") or {}
    project = repo.get("project") or {}
    repository_id = repo.get("id")
    project_id = project.get("id")
    if not repository_id or not project_id:
        sys.exit("error: could not determine repository or project for the pull request")

    organization = args.org or parse_remote_organization(run(["git", "remote", "get-url", "origin"]))
    if not organization:
        sys.exit("error: could not determine organization; provide --org explicitly")
    normalized = normalize_organization(organization)
    access_token = token()
    endpoint = (
        f"https://dev.azure.com/{normalized['organization']}/{project_id}/_apis/git/repositories/"
        f"{repository_id}/pullRequests/{args.id}/labels?api-version=7.1"
    )
    headers = {"Authorization": f"Bearer {access_token}"}
    existing_payload = request_json(endpoint, headers=headers)
    existing = {label["name"] for label in existing_payload.get("value", []) if label.get("name")}
    desired = list(dict.fromkeys(["ai-reviewed", *[f"ai-model-{model}" for model in args.model]]))
    desired_set = set(desired)
    added: list[str] = []
    removed: list[str] = []

    for label in sorted(existing):
        if not label.startswith("ai-model-") or label in desired_set:
            continue
        delete_url = endpoint.replace("?api-version=7.1", f"/{urllib.parse.quote(label, safe='')}?api-version=7.1")
        request_json(delete_url, method="DELETE", headers=headers)
        removed.append(label)

    for label in desired:
        if label in existing:
            continue
        body = json.dumps({"name": label}).encode("utf-8")
        request_json(endpoint, method="POST", body=body, headers={**headers, "Content-Type": "application/json"})
        added.append(label)

    final_payload = request_json(endpoint, headers=headers)
    final_labels = [label["name"] for label in final_payload.get("value", []) if label.get("name")]
    print(
        json.dumps(
            {
                "organization": normalized["organization"],
                "desiredLabels": desired,
                "addedLabels": added,
                "removedLabels": removed,
                "finalLabels": final_labels,
            },
            indent=2,
        )
    )


def build_code_link(args: argparse.Namespace) -> None:
    """Print an Azure DevOps source URL for a commit file range."""
    organization = normalize_organization(args.org)["organization"]
    file_path = normalize_ado_file_path(args.file_path)
    line_start = parse_line_number(args.line_start, "--line-start")
    line_end = parse_line_number(args.line_end or line_start, "--line-end")
    query = urllib.parse.urlencode(
        {
            "path": file_path,
            "version": f"GC{args.commit}",
            "lineStart": str(line_start),
            "lineEnd": str(line_end),
            "lineStartColumn": "1",
            "lineEndColumn": "1",
        }
    )
    project = urllib.parse.quote(args.project, safe="")
    repo = urllib.parse.quote(args.repo, safe="")
    print(json.dumps({"url": f"https://dev.azure.com/{organization}/{project}/_git/{repo}?{query}"}, indent=2))


def upload_attachment(args: argparse.Namespace) -> None:
    """Upload a pull request attachment with the Azure DevOps REST API."""
    organization = normalize_organization(args.org)["organization"]
    file_path = Path(args.file)
    if not file_path.is_file():
        sys.exit(f"error: {file_path} is not a regular file")
    file_name = args.file_name or file_path.name
    project = urllib.parse.quote(args.project, safe="")
    file_name_quoted = urllib.parse.quote(file_name, safe="")
    url = (
        f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/"
        f"{args.repository_id}/pullRequests/{args.pull_request_id}/attachments/{file_name_quoted}"
        "?api-version=7.1"
    )
    payload = request_json(
        url,
        method="POST",
        body=file_path.read_bytes(),
        headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/octet-stream"},
    )
    print(json.dumps({"fileName": file_name, "filePath": str(file_path), "id": payload.get("id"), "url": payload.get("url")}, indent=2))


def add_scope_flags(parser: argparse.ArgumentParser) -> None:
    """Add common Azure DevOps CLI scope flags."""
    parser.add_argument("--detect", default="true")
    parser.add_argument("--org", default="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    eligibility_parser = subparsers.add_parser("eligibility")
    eligibility_parser.add_argument("--id", required=True)
    add_scope_flags(eligibility_parser)
    payload_parser = subparsers.add_parser("thread-payload")
    payload_parser.add_argument("--content", required=True)
    payload_parser.add_argument("--status", default="active")
    payload_parser.add_argument("--file-path", default="")
    payload_parser.add_argument("--line-start", type=int)
    payload_parser.add_argument("--line-end", type=int)
    payload_parser.add_argument("--out-file", default="")
    labels_parser = subparsers.add_parser("sync-labels")
    labels_parser.add_argument("--id", required=True)
    labels_parser.add_argument("--model", action="append", default=[])
    add_scope_flags(labels_parser)
    code_link_parser = subparsers.add_parser("code-link")
    code_link_parser.add_argument("--org", required=True)
    code_link_parser.add_argument("--project", required=True)
    code_link_parser.add_argument("--repo", required=True)
    code_link_parser.add_argument("--commit", required=True)
    code_link_parser.add_argument("--file-path", required=True)
    code_link_parser.add_argument("--line-start", type=int, required=True)
    code_link_parser.add_argument("--line-end", type=int)
    upload_parser = subparsers.add_parser("upload-attachment")
    upload_parser.add_argument("--org", required=True)
    upload_parser.add_argument("--project", required=True)
    upload_parser.add_argument("--repository-id", required=True)
    upload_parser.add_argument("--pull-request-id", required=True)
    upload_parser.add_argument("--file", required=True)
    upload_parser.add_argument("--file-name", default="")
    args = parser.parse_args()

    if args.command == "eligibility":
        eligibility(args)
    elif args.command == "thread-payload":
        payload = build_thread_payload(args)
        if args.out_file:
            out_file = resolve_out_file(args.out_file)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"outFile": str(out_file), "payload": payload}, indent=2))
        else:
            print(json.dumps(payload, indent=2))
    elif args.command == "sync-labels":
        sync_labels(args)
    elif args.command == "code-link":
        build_code_link(args)
    elif args.command == "upload-attachment":
        upload_attachment(args)


if __name__ == "__main__":
    main()
