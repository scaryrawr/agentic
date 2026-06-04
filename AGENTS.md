# Repository Guidelines

## Project Structure & Module Organization
This repository stores reusable personal agent skills. Each skill lives in `skills/<skill-name>/` with a required `SKILL.md`; optional support files belong in `scripts/`, `references/`, `assets/`, and `evals/`. `skills/skill-creator/` contains the validation, packaging, eval, and report tooling used by the other skills. `.github/skills/` exists for Copilot project-skill experiments but is currently empty; do not place normal personal skills there.

## Build, Test, and Development Commands
There is no repo-wide package manager or CI. Use targeted checks from the repo root:

- `python3 skills/skill-creator/scripts/quick_validate.py skills/<skill-name>` — validate one skill's frontmatter and naming.
- `for d in skills/*; do [ -d "$d" ] && python3 skills/skill-creator/scripts/quick_validate.py "$d"; done` — validate every skill.
- `python3 -m py_compile skills/skill-creator/scripts/*.py skills/skill-creator/eval-viewer/*.py` — syntax-check Python tooling.
- `bash -n skills/image-gen/scripts/*.sh` — syntax-check image-generation shell helpers.
- `python3 skills/skill-creator/scripts/package_skill.py skills/<skill-name> /tmp/skill-dist` — package a skill; root `evals/`, caches, and `.DS_Store` are excluded.

## Coding Style & Naming Conventions
Skill folder names and frontmatter `name` values must match, use lowercase kebab-case, and stay under 64 characters. Keep `SKILL.md` concise; move long implementation details to `references/` and deterministic helpers to `scripts/`. Prefer `python3` in commands because `python` is not guaranteed on this machine.

## Testing Guidelines
When editing a skill, run `quick_validate.py` for that skill. Also run language-specific syntax checks for touched helpers. Use `skills/<name>/evals/` only for objective eval prompts and fixtures; packaging intentionally omits root eval directories.

## Commit & Pull Request Guidelines
Existing history uses short imperative subjects such as `Add init skill` and `Improve image-gen skill`. In handoffs or PR notes, list the specific skill changed and the validation commands run.

## Security & Configuration Tips
`image-gen` requires `$OMLX_BASE_URL`, `curl`, `jq`, and `base64`; its scripts intentionally refuse outputs inside the skill directory. Do not commit API keys, generated images, packaged `.skill` archives, or benchmark workspaces unless explicitly requested.

## Agent Skills
- `skills/init` — refresh repository `AGENTS.md` and skill guidance.
- `skills/skill-creator` — create, revise, evaluate, or package SKILL.md-based skills.
- `skills/image-gen` — generate or edit PNG image artifacts through OMLX/OpenAI-compatible image APIs.
- `skills/playwright-cli` — drive browser automation and Playwright-style checks.
