---
name: digivolve
description: >-
  Capture durable repository guidance after task work exposes recurring friction, failed setup, rediscovered
  validation steps, or stale and misleading instructions. Use when asked to digivolve or reflect before
  finishing, record hard-earned repo learnings, correct existing agent guidance, add a justified narrowly
  scoped instruction file, or fix setup and workflow guidance in an in-repo SKILL.md. Inspect repository
  evidence and edit the narrowest instruction surface only when warranted. Not a per-turn check, and not for
  ordinary task completion, generic retrospectives, initial instruction setup, general docs, or one-off notes.
---

# Digivolve

Run this reflection after the task, not on every turn. Treat a no-edit conclusion as a valid result. Never
invent guidance merely because this skill was invoked.

## Workflow

1. Review where the completed work caused friction: commands or paths that had to be rediscovered, setup or
   validation failures, misleading instructions, repeated workarounds, and repository-specific safety or
   convention surprises. Exclude generic advice, one-off task details, secrets, private data, and speculative
   preferences.
2. Inspect existing guidance and executable sources of truth before editing. Read the relevant instruction
   files, manifests, scripts, CI configuration, and deeper documentation needed to verify each candidate.
3. Record a fact only when at least one condition holds:
   - it was repeatedly rediscovered;
   - current guidance is inaccurate, incomplete, or contradicted by the repository;
   - recording it will materially help future agents.
4. Choose the narrowest correct surface:

   | Surface | Use for |
   | --- | --- |
   | Root `AGENTS.md` | Shared repository guidance |
   | Nested `AGENTS.md` | Verified guidance unique to one subtree |
   | `.github/copilot-instructions.md` | Copilot-specific behavior |
   | `.github/instructions/*.instructions.md` | Path-scoped guidance with an accurate `applyTo` |
   | In-repo `.github/skills/**/SKILL.md` or `plugins/*/skills/**/SKILL.md` | Stale setup or workflow instructions in that skill |

   When a root `CLAUDE.md` exists as a compatibility shim, keep its entire content exactly
   `@AGENTS.md` followed by a newline.
5. Correct or tighten existing text instead of duplicating it. Link to deeper documentation when details
   would bloat immediate instructions. Add a nested instruction file only when its narrower scope is real
   and useful.
6. Validate edited Markdown and YAML frontmatter with repository-provided checks when available. Inspect the
   final diff to confirm that only the intended guidance changed and that path-scoped instructions match
   their declared scope.
7. Report the durable learning and edited surface, or state plainly that no durable learning justified an
   edit.

## Boundaries

- Do not add hooks, hook configuration, per-prompt arming, stop blocking, marker or state files, forced
  continuations, generated prompts, silent-response rules, loop prevention, or fail-open behavior.
- Do not add plugin packaging.
- Do not replace a one-line root `CLAUDE.md` shim with duplicated guidance.
