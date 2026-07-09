---
name: ado-work-items
description: When users share Azure DevOps work item links or ask about Azure Boards work items, inspect, search, create, update, link, or query work items with Azure CLI plus the shared work-item helper script.
allowed-tools: Bash(uv run ../ado-cli/scripts/ado-work-items.py:*)
compatibility: "Requires uv/Python and Azure CLI with the azure-devops extension."
---

# Azure DevOps Work Item Trigger

This trigger shim preserves precise dispatch for Azure Boards work item requests. Use the consolidated workflow in `../ado-cli/references/work-items.md` and the shared helper at `../ado-cli/scripts/ado-work-items.py`.

Start work item URLs with:

```text
uv run ../ado-cli/scripts/ado-work-items.py parse-url "https://dev.azure.com/{org}/{project}/_workitems/edit/{workItemId}"
```

Use `wiql` for indexed field queries, `search` for keyword lookup, `required-fields` before creating customized work item types, and `link-pr` when linking pull requests to work items.
