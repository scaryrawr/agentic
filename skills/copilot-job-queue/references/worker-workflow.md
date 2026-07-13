# Worker Workflow

1. Claim one job with a stable worker name. Read its full instructions, acceptance criteria,
   `repo_hint`, `target_branch`, and metadata.
2. Determine the repository before editing:
   - Use an explicit local path or remote URL from `repo_hint` when it identifies one repository.
   - Otherwise match task-specific paths, package names, links, or remote names against available
     repositories and repository profiles.
   - Use repo-specific skills such as `repo-interactions` or `codespace-repo-work` when applicable.
   - If multiple repositories remain plausible, block the job with the candidates and the evidence
     needed to choose between them instead of guessing.
3. Record the canonical local path or remote URL with `set-repo`.
4. Protect unrelated work. Confirm the worktree is safe, fetch the remote target branch, and create a
   unique job branch from the latest remote target. Use a separate worktree or the designated Codespace
   when the existing checkout contains unrelated changes.
5. Implement the complete request and run the repository's scoped validation. Follow repository
   contribution rules and do not alter unrelated files.
6. Commit and push the job branch. Create a **draft** pull request against the requested target branch:
   - GitHub: use the repository's normal `gh pr create --draft` workflow.
   - Azure DevOps: use the `azure-devops` skill's draft PR creation workflow.
7. Call `finish` with the exact pushed branch, draft PR URL, and a concise implementation/validation
   summary. This is the handoff's durable completion signal.
8. If progress requires information, access, or a decision, use `block` with a precise summary. Use
   `release` only for a retryable worker handoff that needs no new input. Never mark a job finished
   without a pushed branch and draft PR.
