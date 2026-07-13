# Commands

Resolve `scripts/job_queue.py` from the loaded skill directory. The examples use `uv run`.

## Initialize or inspect

```text
uv run scripts/job_queue.py init
uv run scripts/job_queue.py list --status queued
uv run scripts/job_queue.py show JOB_ID
```

`init` is optional because every command creates or upgrades the schema before use.

## Enqueue

Prefer an instructions file for multiline work:

```text
uv run scripts/job_queue.py enqueue --title "Fix cache invalidation" --instructions-file task.txt --repo-hint "office-bohemia" --target-branch main --priority 20 --source scout
```

Use `--instructions "..."` for short jobs. `--metadata` accepts a JSON object for stable external IDs
or source links. Do not put credentials in instructions or metadata.

## Claim and resolve a repository

```text
uv run scripts/job_queue.py claim --worker "copilot-app"
uv run scripts/job_queue.py claim --worker "copilot-app" --job-id JOB_ID
uv run scripts/job_queue.py set-repo JOB_ID --worker "copilot-app" --repo "C:\path\to\repo"
```

`claim` is atomic. If no queued job matches, it returns `{"job": null}`. A claimed job can be changed
only by its recorded worker.

## Block, inspect, and unblock

```text
uv run scripts/job_queue.py block JOB_ID --worker "copilot-app" --summary "Repository is ambiguous: both repo-a and repo-b contain the package. Need the owning repo or source link."
uv run scripts/job_queue.py blocked --since "2026-07-01T00:00:00Z" --limit 50
uv run scripts/job_queue.py unblock JOB_ID --actor "scout-automation" --summary "The linked work item names repo-a as the owning repository." --repo-hint "repo-a"
```

`block` releases worker ownership and preserves any resolved repository while making the required
summary directly visible in blocked-job queries. `unblock` appends its grounded resolution summary to
the instructions, optionally corrects repository/target/metadata fields, clears stale worker ownership,
and atomically returns the job to `queued`.

Read `references/unblock-workflow.md` before automating `unblock`.

## Release for retry

```text
uv run scripts/job_queue.py release JOB_ID --worker "copilot-app" --reason "Repository is ambiguous"
```

Release returns the job to the queue and records the reason in the audit log. Use it only when no new
information or decision is required; otherwise use `block`.

## Finish and discover

```text
uv run scripts/job_queue.py finish JOB_ID --worker "copilot-app" --branch "copilot/job-JOB_ID-cache-fix" --pr-url "https://host/project/pullrequest/123" --summary "Fixed invalidation and added regression coverage"
uv run scripts/job_queue.py finished --since "2026-07-01T00:00:00Z" --limit 50
```

`finish` requires a resolved repository, nonempty branch, and HTTP(S) PR URL. The caller is responsible
for creating the PR as a draft before recording it.

Use `--db PATH` before the subcommand for isolated tests:

```text
uv run scripts/job_queue.py --db C:\temp\jobs.sqlite3 list --status all
```
