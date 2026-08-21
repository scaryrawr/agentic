---
name: code-review
description: >-
  Perform a thorough code review of diffs or branch comparisons for correctness,
  structure, regression risk, and edge-case coverage. Use when the user asks to
  review uncommitted changes, inspect a PR/diff, compare a branch to default, or
  audit recent changes for regressions. Not for general conceptual explanations
  of code-review practices or static-analysis tooling.
---

# Code Review

Deliver a concise, structured review that flags real risks — not style nitpicks.
Focus on correctness, data flow, error handling, edge cases, and regression
potential.

## Workflow

### 0. Gate: is this worth reviewing?

Skip if the change is a draft, WIP, or otherwise not ready for review. Only
review when the diff represents an intentional, reviewable change.

### 1. Gather the diff

Uncommitted changes (default), branch-to-default comparison, or PR/fork/remote branch — get the right diff first.

### 2. Read the surrounding code

Diffs are context-poor. Before judging changes, read the affected files and their
immediate callers/callers-to understand:

- The existing contract (APIs, invariants, error-handling patterns)
- How callers use the changed code
- Whether the change touches a shared or high-risk module (auth, serialization,
  persistence, networking, concurrency)

Read at least the changed file, its module-level imports/exports, and the nearest
caller or consumer. Skim adjacent files only when the diff touches a boundary
(imports, config, shared types).

### 3. Evaluate the change

Run through these lenses in order. Keep commentary tight — one or two sentences
per finding, with file/line anchors.

**Correctness**
- Does the change do what it claims to do?
- Are there off-by-one errors, wrong comparisons, or swapped arguments?
- Does the new logic handle the cases the old logic handled?

**Data flow and side effects**
- Are new variables passed through correctly?
- Do mutations propagate to the right places?
- Are there leaked state, race conditions, or stale closures?

**Error handling and edge cases**
- Are new error paths covered?
- Are null/empty/zero/empty-string edge cases considered?
- Does the change break existing error contracts (exception types, return codes)?

**Regression risk**
- Does the change alter behavior visible to callers that the diff doesn't touch?
- Are there integration points (APIs, configs, environment) that could break?
- Does the change remove or weaken an invariant?

**Structure and maintainability**
- Does the change follow the existing style and patterns in the module?
- Is the change scoped appropriately, or is it a multi-concern diff?
- Are imports/exports clean and minimal?

**Tests**
- Are existing tests still valid after the change?
- Does the change warrant new tests? If so, what should they cover?

### 4. Produce the review

Structure the output as follows:

```markdown
## Review: <brief description of change>

**Files changed:** <list>
**Risk level:** Low / Medium / High

### Issues

1. **[Severity]** Short title — one-line explanation with file:line anchor.
2. ...

### Observations

- Positive notes or context-worthy observations (optional).

### Suggestions

- Concrete improvement ideas (optional).
```

Severity labels: **Critical** (will likely break something), **Warning** (risky
or unclear), **Info** (nice-to-fix or worth knowing).

Keep the review to the point. If there are no real issues, say so explicitly
rather than padding with style observations.

### 5. Flag regression risks explicitly

When a change touches a boundary, shared module, or public API, call out the
specific callers or consumers that might break. Name the exact invariant or
contract that could be violated. This is the highest-value part of the review.

## Notes

- Stay grounded in the diff and the code it touches. Do not invent problems or
  assume behavior that isn't visible.
- Focus on changed lines only. Ignore pre-existing issues, CI-only issues, and
  complaints about unmodified lines.
- Post only high-confidence findings. If you're unsure, skip it.
- If the diff is large (> 500 lines), summarize the major change areas first,
  then drill into the riskiest sections.
- If the user provides a PR URL or fork, fetch the relevant branch and diff
  before reviewing.
- For multi-file changes, evaluate whether the files are coherent as a unit or
  should be split.
