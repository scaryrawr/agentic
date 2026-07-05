# Repository Guidelines

## Project Structure & Module Organization
This repository stores reusable personal agent skills. Each skill lives in `skills/<skill-name>/` with a required `SKILL.md`; optional support files belong in `scripts/`, `references/`, `assets/`, and `evals/`. `skills/skill-creator/` contains the validation, packaging, eval, and report tooling used by the other skills. `.github/skills/` exists for Copilot project-skill experiments but is currently empty; do not place normal personal skills there. `README.md` documents the committed skill inventory; keep it up to date when adding, removing, renaming, or materially changing committed skills.

## Build, Test, and Development Commands
There is no repo-wide package manager or CI. Use targeted checks from the repo root:

- `python3 skills/skill-creator/scripts/quick_validate.py skills/<skill-name>` — validate one skill's frontmatter and naming.
- `git ls-files 'skills/*/SKILL.md' | while read -r f; do python3 skills/skill-creator/scripts/quick_validate.py "$(dirname "$f")"; done` — validate every committed skill.
- `git ls-files 'skills/*/SKILL.md' | while read -r f; do test -f "$(dirname "$f")/evals/evals.json" -o -f "$(dirname "$f")/evals/trigger-evals.json"; done` — confirm every committed skill has task or trigger evals.
- `git ls-files 'skills/*/evals/*.json' | while read -r f; do python3 -m json.tool "$f" >/dev/null; done` — validate committed eval JSON.
- `python3 -m py_compile skills/skill-creator/scripts/*.py skills/skill-creator/eval-viewer/*.py` — syntax-check Python tooling.
- `bash -n skills/image-gen/scripts/*.sh` — syntax-check image-generation shell helpers.
- `python3 skills/skill-creator/scripts/package_skill.py skills/<skill-name> /tmp/skill-dist` — package a skill; root `evals/`, caches, and `.DS_Store` are excluded.

## Coding Style & Naming Conventions
Skill folder names and frontmatter `name` values must match, use lowercase kebab-case, and stay under 64 characters. Keep `SKILL.md` concise; move long implementation details to `references/` and deterministic helpers to `scripts/`. Prefer `python3` in commands because `python` is not guaranteed on this machine. For Node/TypeScript skill helpers, document commands and `allowed-tools` as `node ./scripts/<name>.mts ...` instead of executing `./scripts/<name>.mts` directly, so examples work on Windows without shebang support. Keep skill command examples shell-neutral when possible: prefer single-line commands, helper-provided temp paths or `{absolute_path}` placeholders, and avoid POSIX-only paths, Bash parameter expansion, and shell-specific line continuations unless the skill explicitly requires that shell.

## Testing Guidelines
When editing a skill, run `quick_validate.py` for that skill and keep any `evals/*.json` files valid. Also run language-specific syntax checks for touched helpers. Use `skills/<name>/evals/` only for objective eval prompts and fixtures; packaging intentionally omits root eval directories.

## Commit & Pull Request Guidelines
Existing history uses short imperative subjects such as `Add init skill` and `Improve image-gen skill`. In handoffs or PR notes, list the specific skill changed and the validation commands run.

## Security & Configuration Tips
`image-gen` requires `$OMLX_BASE_URL`, `curl`, `jq`, and `base64`; its scripts intentionally refuse outputs inside the skill directory. Do not commit API keys, generated images, packaged `.skill` archives, or benchmark workspaces unless explicitly requested.
Treat skill script arguments as prompt-controlled input: validate them before use, run output-path guards before creating directories or files, clear script-owned stale outputs on rerun, reject in-place input/output combinations when cleanup could delete source data, pass values to interpreters via argv/env instead of interpolating into inline code, and fail loudly on model/API errors rather than producing success-shaped artifacts.

## Agent Skills
- List only skills committed to this repository. Use `git ls-files 'skills/*/SKILL.md'` as the source of truth, and do not add local-only skill directories to `README.md` or this section.
- `skills/ado-cli` — route Azure DevOps links and resource requests to the right Azure DevOps skill.
- `skills/ado-make-pr` — create Azure DevOps pull requests from current changes.
- `skills/ado-pr` — inspect and manage existing Azure DevOps pull requests.
- `skills/ado-review-pr` — review Azure DevOps pull requests and post high-confidence findings.
- `skills/ado-work-items` — inspect and manage Azure DevOps work items.
- `skills/blogify` — turn video or audio recordings into docs, blog posts, tutorials, changelogs, or notes.
- `skills/image-gen` — generate or edit PNG image artifacts through OMLX/OpenAI-compatible image APIs.
- `skills/init` — refresh repository `AGENTS.md` and skill guidance.
- `skills/skill-creator` — create, revise, evaluate, or package Copilot-focused SKILL.md-based skills.
