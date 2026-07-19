---
name: digivolve
description: >-
  Proactively improve repository instructions and skills when task work reveals durable, reusable guidance:
  unexpected setup or validation failures, misleading docs, non-obvious commands or constraints, repeated
  workarounds, or user corrections that future agents would otherwise rediscover. Use near task completion
  when such a signal appears, and when asked to digivolve, reflect, capture a repo learning, correct agent
  guidance, add narrowly scoped instructions, or improve a repository-owned SKILL.md. Inspect evidence and
  edit the narrowest instruction surface only when warranted. Not for routine successful tasks, generic
  retrospectives, initial instruction setup, user-facing docs, speculative advice, or one-off task notes.
---

# Digivolve

Keep a lightweight watch for durable learning while working. Run the reflection near task completion whenever
a meaningful signal appears; do not wait for the user to request it. Do not interrupt each turn or force an
edit. Treat a no-edit conclusion as valid, and never invent guidance merely because this skill was invoked.

## Workflow

1. Notice candidate learnings during the task. Trigger reflection when work exposes at least one strong signal:
   - an expected setup, build, test, validation, or tool command failed and required investigation;
   - existing instructions or a skill contradicted executable repository evidence;
   - a non-obvious command, path, dependency, safety constraint, or workflow rule was needed to succeed;
   - a workaround or correction is likely to recur for future agents;
   - the user corrected a durable repository convention or agent workflow.
   Routine debugging, ordinary code understanding, and interesting-but-task-specific details are not signals.
   Exclude generic advice, secrets, private data, and speculative preferences.
2. Inspect existing guidance and executable sources of truth before editing. Read the relevant instruction
   files, manifests, scripts, CI configuration, and deeper documentation needed to verify each candidate.
3. Record a fact only when at least one condition holds:
   - it was repeatedly rediscovered;
   - current guidance is inaccurate, incomplete, or contradicted by the repository;
   - recording it will materially prevent future failure, delay, or unsafe behavior.
4. Choose the narrowest correct surface:

   | Surface | Use for |
   | --- | --- |
   | Root `AGENTS.md` | Shared repository guidance |
   | Nested `AGENTS.md` | Verified guidance unique to one subtree |
   | `.github/copilot-instructions.md` | Copilot-specific behavior |
   | `.github/instructions/*.instructions.md` | Path-scoped guidance with an accurate `applyTo` |
   | Repository-owned `**/SKILL.md` | Stale or incomplete setup, workflow, safety, or routing instructions in that skill |

   When a root `CLAUDE.md` exists as a compatibility shim, keep its entire content exactly
   `@AGENTS.md` followed by a newline.
5. Correct or tighten existing text instead of duplicating it. Link to deeper documentation when details
   would bloat immediate instructions. Add a nested instruction file only when its narrower scope is real
   and useful.
6. Validate edited Markdown and YAML frontmatter with repository-provided checks when available. Inspect the
   final diff to confirm that only the intended guidance changed and that path-scoped instructions match
   their declared scope.
7. Make the outcome visible in the final response: name the durable learning and edited surface, or state
   plainly that reflection found no justified guidance edit.

## Boundaries

- Do not add hooks, hook configuration, per-prompt arming, stop blocking, marker or state files, forced
  continuations, generated prompts, silent-response rules, loop prevention, or fail-open behavior.
- Do not add plugin packaging.
- Do not replace a one-line root `CLAUDE.md` shim with duplicated guidance.
