---
name: ado-make-pr
description: Creates an Azure DevOps pull request from current changes. Use the shared helper script for repo preflight, template discovery, REST PR creation, and attachment upload before calling Azure CLI.
allowed-tools: Bash(uv run ../ado-cli/scripts/make-pr.py:*)
compatibility: "Requires uv/Python, Git, and Azure CLI with the azure-devops extension."
---

# Azure DevOps PR Creation Trigger

This trigger shim preserves precise dispatch for creating Azure DevOps PRs. Use the consolidated workflow in `../ado-cli/references/make-pr.md` and the shared helper at `../ado-cli/scripts/make-pr.py`.

Start with:

```text
uv run ../ado-cli/scripts/make-pr.py preflight
```

Stop on blockers. Use `discover-template` before composing the PR description and prefer `create-pr` when using template or file descriptions so multiline markdown is preserved.
