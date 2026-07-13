# Blocked-Job Automation

Use this workflow in the automation that discovers finished jobs.

1. Query `blocked --since <last-run>` and also include older blocked jobs that remain unresolved.
2. Read each job's instructions, blocked `summary`, metadata, repository fields, and audit events.
3. Attempt a bounded, read-only resolution using authoritative local or linked sources already available
   to the user: repository profiles/remotes, referenced work items or PRs, source links, and established
   project documentation.
4. Call `unblock` only when evidence resolves the stated blocker without judgment on the user's behalf.
   Include the evidence and source in `--summary`, and correct only fields supported by that evidence.
   The helper appends this context to the worker instructions and requeues the job.
5. Never infer ambiguous requirements, choose between competing product decisions, grant approval,
   fabricate credentials, weaken policy, or silently expand scope.
6. If the blocker remains, leave the job `blocked`. Report:
   - job ID and title;
   - the current blocked summary;
   - what the automation checked;
   - the smallest specific question, access grant, link, or decision needed from the user.
7. On a later run, repeat the check. The user or Scout can use the same `unblock` command once grounded
   input is available.

Avoid repeatedly rewriting blocked summaries merely to record another unsuccessful check. Put run-level
investigation details in the automation report unless they materially clarify the enduring blocker.
