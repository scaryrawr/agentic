# Queue Storage

The default database is `state/jobs.sqlite3`. SQLite write-ahead logging, foreign keys, a busy timeout,
and `BEGIN IMMEDIATE` claim transactions make concurrent Scout/Copilot access deterministic.

## Tables

- `jobs`: authoritative lifecycle and job payload. Status is `queued`, `claimed`, `blocked`, or
  `finished`; `summary` describes the latest durable transition.
- `finished_jobs`: one immutable completion row per successful job, including repository, pushed branch,
  draft PR URL, worker, timestamp, and summary.
- `job_events`: append-only audit records for enqueue, claim, repository selection, block, unblock,
  release, and finish.
- `schema_version`: tracks compatible schema revisions.

## Ordering and ownership

The next claim is selected by descending priority, then oldest creation time and ID. Claiming and
ownership assignment happen in one write transaction. Only `claimed_by` can set the repository,
block, release, or finish the job.

A blocked job is unowned and has `blocked_at`, `blocked_by`, and a nonempty `summary`. `unblock` records
the resolver as an event actor, appends grounded resolution context to the instructions, applies only
explicit field corrections, and returns the job to the normal claim queue.

Finished jobs remain visible in `jobs` and are joined to `finished_jobs` by `job_id`. This preserves
the original instructions while making completion discovery efficient.

## Backup

Back up the database only while no writer is active, or use SQLite's online backup API. Do not copy
only the main database file while WAL mode has uncheckpointed changes.
