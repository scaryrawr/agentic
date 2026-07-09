---
name: ado-review-pr
description: Review an Azure DevOps pull request. Use the shared helper script for eligibility checks, thread payloads, label sync, code links, and attachment uploads.
allowed-tools: Bash(uv run ../ado-cli/scripts/review-pr.py:*)
compatibility: "Requires uv/Python, Git, and Azure CLI with the azure-devops extension."
---

# Azure DevOps PR Review Trigger

This trigger shim preserves precise dispatch for Azure DevOps PR review requests. Use the consolidated workflow in `../ado-cli/references/review-pr.md` and the shared helper at `../ado-cli/scripts/review-pr.py`.

Start with:

```text
uv run ../ado-cli/scripts/review-pr.py eligibility --id {prId} --detect true
```

Skip inactive or draft PRs. Post only high-confidence findings, build inline comment payloads with `thread-payload`, and sync `ai-reviewed` plus `ai-model-<model-id>` labels after the review.
