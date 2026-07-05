---
name: ado-cli
description: When users share Azure DevOps links or mention Azure DevOps resources, parse the URL, identify the resource type, and route to the right Azure DevOps skill.
allowed-tools: Bash(node ./scripts/ado-cli.mts:*)
compatibility: "Requires Node.js >=22.18 and Azure CLI with the azure-devops extension."
---

# Azure DevOps Router

## Available scripts

Run these non-interactive helpers with `node` and the skill-relative `./scripts/...` paths shown below; they print JSON to stdout and diagnostics to stderr. Run `node ./scripts/ado-cli.mts --help` to confirm flags or subcommands.

### `parse-url`

Always normalize the URL with the script instead of manually re-parsing host and path segments:

```text
node ./scripts/ado-cli.mts parse-url "https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{prId}"
```

The script returns structured JSON including:

- `organization`
- `organizationUrl`
- `project`
- `repository` when present
- `resourceType`
- `resourceId`
- `routeSkill`

Routing rules:

- `pull-request` -> `ado-pr`
- `work-item` -> `ado-work-items`
- `unknown` -> inspect the user request and choose `ado-make-pr`, `ado-review-pr`, or another flow yourself

### `upload-attachment`

When you need a PR attachment URL, use the script instead of rebuilding the token + binary upload flow inline:

```text
node ./scripts/ado-cli.mts upload-attachment --org {org-or-url} --project {project} --repository-id {repositoryId} --pull-request-id {prId} --file {absolute_path_to_image}
```

The script returns `fileName`, `filePath`, `id`, and `url` as JSON.

## Workflow

1. Parse the Azure DevOps URL with `parse-url`.
2. Use `routeSkill` for existing resource URLs. If the parse result is `unknown`, choose `ado-make-pr` or `ado-review-pr` from the user's request instead of expecting the parser to infer intent.
3. Reuse `organizationUrl` or the parsed project/repository identifiers when later Azure CLI commands need explicit scope.
4. Use `upload-attachment` only when the task needs a PR attachment URL. Pass an OS-native absolute path to `--file`.

## Organization detection

For Azure CLI commands that support it, prefer `--detect true` when you are inside the target repository.

If auto-detection fails, fall back to `organizationUrl` from the parse result or a user-supplied org URL.

## Rules

- Prefer the script output over handwritten URL parsing.
- Prefer the script output over handwritten `curl` + `python3` attachment upload snippets.
- Keep examples shell-neutral: avoid hard-coded POSIX temp paths, Bash parameter expansion, and line-continuation syntax when a single-line command works.
- Fail loudly when the URL host or path is unsupported.
