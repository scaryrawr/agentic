---
name: ado-cli
description: When users share Azure DevOps links or mention Azure DevOps resources, parse the URL, identify the resource type, and route to the right Azure DevOps workflow. Also use this skill for shared Azure DevOps helper scripts, reference workflows, and uploading PNG/image/file attachments to Azure DevOps pull requests.
allowed-tools: >-
  Bash(uv run ./scripts/ado-cli.py:*)
  Bash(uv run ./scripts/ado-pr.py:*)
  Bash(uv run ./scripts/review-pr.py:*)
  Bash(uv run ./scripts/make-pr.py:*)
  Bash(uv run ./scripts/ado-work-items.py:*)
compatibility: "Requires uv/Python, Git for checkout and PR creation flows, and Azure CLI with the azure-devops extension."
---

# Azure DevOps Operations

## Start here

Use this skill directly for Azure DevOps URL routing, unknown Azure DevOps resource links, and shared helper scripts. Specialized trigger shims (`ado-pr`, `ado-review-pr`, `ado-make-pr`, and `ado-work-items`) point back to this skill's reference files and scripts for the detailed workflows.

Supported hosts are `dev.azure.com` and `*.visualstudio.com`.

When the user provides an Azure DevOps URL, normalize it first:

```text
uv run ./scripts/ado-cli.py parse-url "{azure_devops_url}"
```

Use the returned `organizationUrl`, `project`, `repository`, `resourceType`, and `resourceId` directly. `routeSkill` is an internal workflow hint:

- `pull-request` -> use `references/pr.md` for existing PR inspection or management.
- `work-items` -> use `references/work-items.md` for Azure Boards work items and WIQL.
- `unknown` -> choose from the user's intent: PR creation, PR review, existing PR operations, or work items.

## Choose the workflow

- **Create an Azure DevOps PR from current changes**: read `references/make-pr.md` and use `uv run ./scripts/make-pr.py ...`.
- **Inspect or manage an existing Azure DevOps PR**: read `references/pr.md` and use `uv run ./scripts/ado-pr.py ...`.
- **Review an Azure DevOps PR**: read `references/review-pr.md` and use `uv run ./scripts/review-pr.py ...`.
- **Inspect or manage Azure Boards work items, relations, or WIQL**: read `references/work-items.md` and use `uv run ./scripts/ado-work-items.py ...`.
- **Upload a PR attachment**: use `uv run ./scripts/ado-cli.py upload-attachment ...` or the equivalent workflow-specific helper command.

## Organization detection

For Azure CLI commands that support it, prefer `--detect true` when you are inside the target repository. If auto-detection fails, fall back to `organizationUrl` from `parse-url`, parsed git remote metadata from `make-pr.py preflight`, or a user-supplied org URL.

## Rules

- Prefer helper output over handwritten URL parsing, WIQL assembly, PR thread JSON, code links, template discovery, or attachment uploads.
- Keep commands shell-neutral: use single-line commands, quote shell-sensitive values such as `"@Me"`, use helper-provided temp paths, and avoid POSIX-only temp paths or Bash parameter expansion.
- Stop and surface blockers, branch-policy errors, permission failures, unsupported URL hosts, and unsupported paths verbatim.
