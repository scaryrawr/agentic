---
name: ado-pr
description: When users share Azure DevOps pull request links or ask about an Azure DevOps PR, inspect and manage the PR with Azure CLI plus the shared ADO PR helper script.
allowed-tools: Bash(uv run ../ado-cli/scripts/ado-pr.py:*)
compatibility: "Requires uv/Python, Azure CLI with the azure-devops extension, and Git for checkout flows."
---

# Azure DevOps Pull Request Trigger

This trigger shim preserves precise dispatch for existing Azure DevOps PR operations. Use the consolidated workflow in `../ado-cli/references/pr.md` and the shared helper at `../ado-cli/scripts/ado-pr.py`.

Start with:

```text
uv run ../ado-cli/scripts/ado-pr.py context --id {prId} --detect true
```

Use `list-threads` for comment thread state and `thread-payload` before posting PR comments. Keep commands shell-neutral and rerun with explicit `--org` when `--detect true` fails.
