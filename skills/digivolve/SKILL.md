---
name: digivolve
description: >-
  Use whenever the user explicitly says to digivolve; requests end-of-task reflection that records durable
  repository knowledge; asks to record durable repo learnings or correct stale, missing, or misleading
  repository agent instructions; identifies a needed narrowly scoped nested AGENTS.md; or asks to fix stale
  setup or workflow guidance in an in-repo SKILL.md. Inspect repository evidence and edit the narrowest
  instruction surface only when warranted. Not for ordinary task completion, generic retrospectives, initial
  repository instruction setup, general documentation, or one-off notes.
---

# Digivolve

Treat a no-edit conclusion as a valid result. Never invent guidance merely because this skill was invoked.

## Workflow

1. Review the completed work and identify candidate facts about repository-specific setup, validation,
   workflow, safety, or conventions. Exclude generic advice, one-off task details, secrets, private data,
   and speculative preferences.
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
