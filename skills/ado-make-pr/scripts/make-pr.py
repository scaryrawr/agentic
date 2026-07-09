#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Azure DevOps PR creation helper utilities."""

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


def run(command: list[str], cwd: Path | None = None, *, exit_on_error: bool = True) -> str:
    """Run a command and return stdout, optionally letting the caller handle errors."""
    try:
        return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError as exc:
        if not exit_on_error:
            raise
        details = (exc.stderr or exc.stdout or str(exc)).strip()
        sys.exit(f"error: {' '.join(command)} failed: {details}")


def git(args: list[str], cwd: Path | None = None, *, exit_on_error: bool = True) -> str:
    """Run git with optional repository cwd."""
    return run(["git", *args], cwd=cwd, exit_on_error=exit_on_error)


def parse_azure_remote(remote_url: str) -> dict[str, Any] | None:
    """Parse Azure DevOps HTTPS or SSH git remotes."""
    parsed = urllib.parse.urlparse(remote_url)
    if parsed.scheme == "https" and parsed.hostname:
        is_visual_studio = parsed.hostname.endswith(".visualstudio.com")
        is_dev_azure = parsed.hostname == "dev.azure.com"
        if is_visual_studio or is_dev_azure:
            segments = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
            if is_dev_azure:
                if not segments:
                    return None
                organization, segments = segments[0], segments[1:]
            else:
                organization = parsed.hostname.removesuffix(".visualstudio.com")
                if segments[:1] == ["DefaultCollection"]:
                    segments = segments[1:]
            repository_index = 3 if len(segments) > 2 and segments[2] == "_optimized" else 2
            if len(segments) <= repository_index or len(segments) < 2 or segments[1] != "_git":
                return None
            return {
                "organization": organization,
                "organizationUrl": f"https://dev.azure.com/{organization}",
                "project": segments[0],
                "repository": segments[repository_index],
                "scheme": "https",
            }

    ssh_prefixes = ("ssh://git@ssh.dev.azure.com:v3/", "git@ssh.dev.azure.com:v3/")
    for prefix in ssh_prefixes:
        if remote_url.startswith(prefix):
            parts = remote_url[len(prefix):].split("/")
            if len(parts) >= 3:
                organization, project, repository = parts[:3]
                return {
                    "organization": organization,
                    "organizationUrl": f"https://dev.azure.com/{organization}",
                    "project": project,
                    "repository": repository,
                    "scheme": "ssh",
                }
    return None


def repo_root(value: str | None) -> Path:
    """Return the repository root to inspect."""
    return Path(value).resolve() if value else Path(git(["rev-parse", "--show-toplevel"])).resolve()


def preflight(args: argparse.Namespace) -> None:
    """Print PR-creation preflight state for the current repository."""
    root = repo_root(args.repo_root)
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    head = git(["rev-parse", "HEAD"], root)
    status_lines = [line for line in git(["status", "--short"], root).splitlines() if line]
    conflict_files = [line for line in git(["diff", "--name-only", "--diff-filter=U"], root).splitlines() if line]

    has_origin_remote = True
    origin_remote_url = None
    try:
        origin_remote_url = git(["remote", "get-url", "origin"], root, exit_on_error=False)
    except subprocess.CalledProcessError:
        has_origin_remote = False

    default_branch = None
    try:
        symbolic_ref = git(["symbolic-ref", "refs/remotes/origin/HEAD"], root, exit_on_error=False)
        default_branch = symbolic_ref.removeprefix("refs/remotes/origin/")
    except subprocess.CalledProcessError:
        default_branch = None

    blockers: list[str] = []
    warnings: list[str] = []
    is_detached_head = branch == "HEAD"
    if is_detached_head:
        blockers.append("Detached HEAD")
    if conflict_files:
        blockers.append("Merge conflicts present")
    if not has_origin_remote:
        blockers.append("No origin remote")

    parsed_remote = parse_azure_remote(origin_remote_url) if origin_remote_url else None
    if origin_remote_url and not parsed_remote:
        blockers.append("Origin remote is not a recognized Azure DevOps remote")
    if default_branch and branch == default_branch:
        warnings.append(f"Current branch matches the default branch ({default_branch})")

    print(
        json.dumps(
            {
                "repoRoot": str(root),
                "branch": branch,
                "head": head,
                "isDetachedHead": is_detached_head,
                "hasUncommittedChanges": bool(status_lines),
                "statusLines": status_lines,
                "hasConflicts": bool(conflict_files),
                "conflictFiles": conflict_files,
                "hasOriginRemote": has_origin_remote,
                "originRemoteUrl": origin_remote_url,
                "parsedRemote": parsed_remote,
                "defaultBranch": default_branch,
                "isOnDefaultBranch": bool(default_branch and branch == default_branch),
                "blockers": blockers,
                "warnings": warnings,
            },
            indent=2,
        )
    )


def first_existing(paths: list[Path]) -> Path | None:
    """Return the first existing file from candidates."""
    return next((path for path in paths if path.exists()), None)


def discover_template(args: argparse.Namespace) -> None:
    """Discover a pull request template for a target branch."""
    root = repo_root(args.repo_root)
    target_branch = args.target_branch
    checked: list[Path] = []
    branch_template_bases = [
        ".azuredevops/pull_request_template/branches",
        ".vsts/pull_request_template/branches",
        "docs/pull_request_template/branches",
        "pull_request_template/branches",
    ]
    general_templates = [
        ".azuredevops/pull_request_template.md",
        ".azuredevops/pull_request_template.txt",
        ".vsts/pull_request_template.md",
        ".vsts/pull_request_template.txt",
        "docs/pull_request_template.md",
        "docs/pull_request_template.txt",
        "pull_request_template.md",
        "pull_request_template.txt",
    ]
    additional_dirs = [
        ".azuredevops/pull_request_template",
        ".vsts/pull_request_template",
        "docs/pull_request_template",
        "pull_request_template",
    ]

    found: Path | None = None
    if target_branch:
        branch_candidates = [
            root / base / f"{target_branch}{suffix}"
            for base in branch_template_bases
            for suffix in (".md", ".txt")
        ]
        checked.extend(branch_candidates)
        found = first_existing(branch_candidates)
    if not found:
        general_candidates = [root / relative for relative in general_templates]
        checked.extend(general_candidates)
        found = first_existing(general_candidates)

    additional_templates: list[Path] = []
    for directory in additional_dirs:
        absolute = root / directory
        if not absolute.is_dir():
            continue
        additional_templates.extend(path for path in absolute.iterdir() if path.is_file() and path.suffix in {".md", ".txt"})

    selected = found or (additional_templates[0] if len(additional_templates) == 1 else None)
    print(
        json.dumps(
            {
                "repoRoot": str(root),
                "targetBranch": target_branch,
                "selectedPath": str(selected) if selected else None,
                "selectedContent": selected.read_text(encoding="utf-8") if selected else None,
                "checked": [str(path) for path in checked],
                "additionalTemplates": [str(path) for path in additional_templates],
            },
            indent=2,
        )
    )


def token() -> str:
    """Return an Azure DevOps access token from Azure CLI."""
    return run(["az", "account", "get-access-token", "--resource", DEVOPS_RESOURCE, "--query", "accessToken", "-o", "tsv"])


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
    request = urllib.request.Request(
        url,
        data=file_path.read_bytes(),
        headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/octet-stream"},
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
    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("--repo-root", default="")
    template_parser = subparsers.add_parser("discover-template")
    template_parser.add_argument("--repo-root", default="")
    template_parser.add_argument("--target-branch", default="")
    upload_parser = subparsers.add_parser("upload-attachment")
    upload_parser.add_argument("--org", required=True)
    upload_parser.add_argument("--project", required=True)
    upload_parser.add_argument("--repository-id", required=True)
    upload_parser.add_argument("--pull-request-id", required=True)
    upload_parser.add_argument("--file", required=True)
    upload_parser.add_argument("--file-name", default="")
    args = parser.parse_args()

    if args.command == "preflight":
        preflight(args)
    elif args.command == "discover-template":
        discover_template(args)
    elif args.command == "upload-attachment":
        upload_attachment(args)


if __name__ == "__main__":
    main()
