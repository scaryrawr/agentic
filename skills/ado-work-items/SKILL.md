---
name: ado-work-items
description: When users share Azure DevOps work item links or ask about work items, inspect and manage work items with Azure CLI plus the local work-item helper script.
allowed-tools: Bash(node ./scripts/ado-work-items.mts:*)
compatibility: "Requires Node.js >=22.18 and Azure CLI with the azure-devops extension."
---

# Azure DevOps Work Item Operations

## Available scripts

Run these non-interactive helpers with `node` and the skill-relative `./scripts/...` paths shown below; they print JSON to stdout and diagnostics to stderr. Run `node ./scripts/ado-work-items.mts --help` to confirm flags or subcommands.

### `parse-url`

Use the script instead of manually pulling the ID out of the URL:

```text
node ./scripts/ado-work-items.mts parse-url "https://dev.azure.com/{org}/{project}/_workitems/edit/{workItemId}"
```

Use these fields directly:

- `organization`, `organizationUrl`
- `project`
- `workItemId`

### `wiql`

Use the helper to assemble common WIQL queries instead of rewriting the `WHERE` clause from scratch:

```text
node ./scripts/ado-work-items.mts wiql --assigned-to @Me --exclude-state Closed --type Bug --fields System.Id,System.Title,System.State
```

The script returns:

- `wiql`: the query text
- `executable` and `commandArgs`: shell-neutral argv values for `az boards query`
- `posixCommand`: a display-only command for POSIX shells

## Workflow

1. Parse incoming Azure DevOps work item URLs with `parse-url`.
2. Build WIQL with `wiql` instead of manually composing `WHERE` clauses.
3. Run the appropriate Azure CLI command after the helper has normalized the inputs.

## Common work item commands

Show a work item:

```text
az boards work-item show --id {workItemId} --detect true
```

Show specific fields:

```text
az boards work-item show --id {workItemId} --fields "System.Title,System.State,System.AssignedTo" --detect true
```

Create a work item:

```text
az boards work-item create --title "Title" --type "Task" --project {project} --detect true
```

Update a work item:

```text
az boards work-item update --id {workItemId} --state "Active" --detect true
```

Run WIQL:

```text
az boards query --wiql "SELECT [System.Id], [System.Title] FROM workitems WHERE [System.AssignedTo] = @Me" --detect true
```

Manage relations:

```text
az boards work-item relation add --id {workItemId} --relation-type parent --target-id {targetId} --detect true
az boards work-item relation show --id {workItemId} --detect true
az boards work-item relation remove --id {workItemId} --relation-type child --target-id {targetId} --detect true
```

## Rules

- Prefer the helper script for URL parsing and WIQL assembly.
- Prefer `--detect true` when repository context is available.
- Keep custom field names exact; do not silently rewrite them.
- Use `executable` plus `commandArgs` from the WIQL helper instead of copying POSIX shell quoting on Windows.
