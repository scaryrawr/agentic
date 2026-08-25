# Repository Guidelines

## Project Structure & Module Organization

This repository maintains reusable personal agent skills that are not owned by a plugin repository. Each skill lives in `skills/<skill-name>/` with a required `SKILL.md`; optional support files belong in `scripts/`, `references/`, `assets/`, and `evals/`. `skills/skill-creator/` contains the validation, packaging, eval, and report tooling used by the other skills. `.github/skills/` exists for Copilot project-skill experiments but is currently empty; do not place normal personal skills there. `README.md` documents the committed skill inventory and externally owned plugin resources; keep it up to date when adding, removing, renaming, or materially changing either.

## Build, Test, and Development Commands

There is no repo-wide package manager or CI. Use targeted checks from the repo root:

- `python3 skills/skill-creator/scripts/quick_validate.py skills/<skill-name>` — validate one skill's frontmatter and naming.
- `git ls-files 'skills/*/SKILL.md' | while read -r f; do python3 skills/skill-creator/scripts/quick_validate.py "$(dirname "$f")"; done` — validate every committed skill.
- `git ls-files 'skills/*/SKILL.md' | while read -r f; do test -f "$(dirname "$f")/evals/evals.json" -o -f "$(dirname "$f")/evals/trigger-evals.json"; done` — confirm every committed skill has task or trigger evals.
- `git ls-files 'skills/*/evals/*.json' | while read -r f; do python3 -m json.tool "$f" >/dev/null; done` — validate committed eval JSON.
- `python3 -m py_compile skills/skill-creator/scripts/*.py skills/skill-creator/eval-viewer/*.py` — syntax-check Python tooling.
- `python3 skills/skill-creator/scripts/package_skill.py skills/<skill-name> /tmp/skill-dist` — package a skill; root `evals/`, caches, and `.DS_Store` are excluded.

## Coding Style & Naming Conventions

Skill folder names and frontmatter `name` values must match, use lowercase kebab-case, and stay under 64 characters. Keep `SKILL.md` concise; move long implementation details to `references/` and deterministic helpers to `scripts/`. Prefer `python3` in commands because `python` is not guaranteed on this machine. Prefer `uv run` Python helpers for new or substantially rewritten cross-platform scripts, especially when replacing Bash or `.mts` helpers that have Windows portability issues; keep Bash or `.mts` only when there is a clear reason and document the runtime dependency. Keep skill command examples shell-neutral when possible: prefer single-line commands, quote shell-sensitive literal values such as `"@Me"`, use helper-provided temp paths or `{absolute_path}` placeholders, and avoid POSIX-only paths, shell-expanded globs, Bash parameter expansion, and shell-specific line continuations unless the skill explicitly requires that shell.

## Testing Guidelines

When editing a skill, run `quick_validate.py` for that skill and keep any `evals/*.json` files valid. Also run language-specific syntax checks for touched helpers. Use `skills/<name>/evals/` only for objective eval prompts and fixtures; packaging intentionally omits root eval directories.

## Commit & Pull Request Guidelines

Existing history uses short imperative subjects such as `Add init skill` and `Improve image-gen skill`. In handoffs or PR notes, list the specific skill changed and the validation commands run.

## Security & Configuration Tips

Do not commit API keys, generated media, packaged `.skill` archives, or benchmark workspaces unless explicitly requested. Treat skill script arguments as prompt-controlled input: validate them before use, run output-path guards before creating directories or files, clear script-owned stale outputs on rerun, reject in-place input/output combinations when cleanup could delete source data, pass values to interpreters via argv/env instead of interpolating into inline code, and fail loudly on model/API errors rather than producing success-shaped artifacts.

## Agent Skills

- List only skills committed to this repository. Use `git ls-files 'skills/*/SKILL.md'` as the source of truth, and do not add local-only skill directories to `README.md` or this section.
- When related skills share most implementation, prefer consolidating them into one skill whose description spans every use case, with per-use-case reference files read on demand via an in-`SKILL.md` routing table. Only keep separate trigger-shim skills if trigger evals show a single consolidated description loses dispatch precision on some use case.
- When a single skill routes to on-demand reference files, keep command examples path-neutral (`./scripts/...` from the skill directory) so agents do not run non-existent commands.
- A broad consolidated skill description can over-trigger on conceptual/"explain X" queries that name a domain keyword (e.g. "explain WIQL"). Add an explicit negative-scope clause to the description (e.g. "not for general conceptual explanations that do not act on a specific resource, and not for GitHub/Jira/other tools"); it stops those false triggers without suppressing real action queries. Verify with `run_eval.py` before removing shims.
- `skills/code-review` — perform a thorough code review of diffs or branch comparisons for correctness, structure, regression risk, and edge-case coverage.
- `skills/better-init` — refresh repository `AGENTS.md` and skill guidance.
- `skills/skill-creator` — create, revise, evaluate, or package Copilot-focused SKILL.md-based skills.

## External Plugin Ownership

- `scaryrawr/scarypilot` is the sole source of truth for `plugins/azure-devops/skills/azure-devops`, `plugins/omlx-media/skills/blogify`, and `plugins/omlx-media/skills/image-gen`; do not restore copies under this repository's `skills/` directory.
- Document Copilot-specific installation through the ScaryPilot marketplace. Where direct cross-agent skill installation is relevant, use `gh skill install scaryrawr/scarypilot <path>` with the canonical path and do not point installers at `scaryrawr/agentic`.
