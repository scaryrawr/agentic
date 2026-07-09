#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Inspect Azure DevOps PR context and build thread payloads."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


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


def scope_args(args: argparse.Namespace) -> list[str]:
    """Return az scope arguments from --org or --detect."""
    if args.org:
        return ["--org", args.org]
    return ["--detect", args.detect]


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
    directory = Path(tempfile.mkdtemp(prefix="ado-pr-"))
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


def context(args: argparse.Namespace) -> None:
    """Print compact context for an Azure DevOps pull request."""
    details = run_json(["az", "repos", "pr", "show", "--id", args.id, *scope_args(args)])
    repo = details.get("repository") or {}
    project = repo.get("project") or {}
    payload = {
        "pullRequestId": details.get("pullRequestId"),
        "title": details.get("title"),
        "status": details.get("status"),
        "isDraft": details.get("isDraft", False),
        "sourceBranch": details.get("sourceRefName"),
        "sourceBranchName": strip_refs_heads(details.get("sourceRefName")),
        "targetBranch": details.get("targetRefName"),
        "targetBranchName": strip_refs_heads(details.get("targetRefName")),
        "repositoryId": repo.get("id"),
        "repositoryName": repo.get("name"),
        "projectId": project.get("id"),
        "projectName": project.get("name"),
        "createdBy": (details.get("createdBy") or {}).get("uniqueName") or (details.get("createdBy") or {}).get("displayName"),
        "url": details.get("url"),
    }
    print(json.dumps(payload, indent=2))


def list_threads(args: argparse.Namespace) -> None:
    """List Azure DevOps pull request threads, optionally filtering by status."""
    details = run_json(["az", "repos", "pr", "show", "--id", args.id, *scope_args(args)])
    repo = details.get("repository") or {}
    project = repo.get("project") or {}
    project_name = project.get("name")
    repository_id = repo.get("id")
    if not project_name or not repository_id:
        sys.exit("error: could not determine project or repository for the pull request")

    response = run_json(
        [
            "az",
            "devops",
            "invoke",
            "--area",
            "git",
            "--resource",
            "pullRequestThreads",
            "--route-parameters",
            f"project={project_name}",
            f"repositoryId={repository_id}",
            f"pullRequestId={args.id}",
            "--api-version",
            "7.1",
            *scope_args(args),
        ]
    )
    threads = response.get("value") or []
    if args.status:
        threads = [thread for thread in threads if thread.get("status") == args.status]
    print(json.dumps({"count": len(threads), "threads": threads}, indent=2))


def add_scope_flags(parser: argparse.ArgumentParser) -> None:
    """Add common Azure DevOps CLI scope flags."""
    parser.add_argument("--detect", default="true")
    parser.add_argument("--org", default="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    context_parser = subparsers.add_parser("context")
    context_parser.add_argument("--id", required=True)
    add_scope_flags(context_parser)
    threads_parser = subparsers.add_parser("list-threads")
    threads_parser.add_argument("--id", required=True)
    threads_parser.add_argument("--status", default="")
    add_scope_flags(threads_parser)
    payload_parser = subparsers.add_parser("thread-payload")
    payload_parser.add_argument("--content", required=True)
    payload_parser.add_argument("--status", default="active")
    payload_parser.add_argument("--file-path", default="")
    payload_parser.add_argument("--line-start", type=int)
    payload_parser.add_argument("--line-end", type=int)
    payload_parser.add_argument("--out-file", default="")
    args = parser.parse_args()

    if args.command == "context":
        context(args)
    elif args.command == "list-threads":
        list_threads(args)
    elif args.command == "thread-payload":
        payload = build_thread_payload(args)
        if args.out_file:
            out_file = resolve_out_file(args.out_file)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"outFile": str(out_file), "payload": payload}, indent=2))
        else:
            print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
