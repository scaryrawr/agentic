---
name: better-init
description: Create or improve AGENTS.md and project agent-skill guidance for a repository. Use when the user asks to initialize, bootstrap, or set up agent instructions, repo guidelines, AGENTS.md, or reusable skills. Discovers repo structure, commands, existing instruction files, and .agents/skills, then writes concise, high-signal guidance.
disable-model-invocation: true
---

# Repository Initialization Skill

Every line should answer: "Would an agent likely miss this without help?" If not, leave it out.

## Workflow

### 1. Capture user intent

Honor any user-provided focus or constraints first, such as "make this Python-specific", "include PR workflow", or "add a validation skill". If the user names a file or path, prioritize that scope.

Do not ask questions before reading the repository unless the user's request is impossible to interpret.

### 2. Investigate the repository

Read the highest-value sources first — prefer executable sources of truth over prose:

- `README*`, root manifests (`package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, etc.), workspace config, lockfiles
- Build, test, lint, formatter, typecheck, and codegen config
- CI workflows (`.github/workflows/`, `.gitlab-ci.yml`, etc.) and pre-commit / task runner config
- Existing instruction files: `AGENTS.md`, nested `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/`, `.cursorrules`
- Repo-local agent config such as `opencode.json`, `.pi/settings.json`, `.claude/settings.json`, or equivalent
- Existing project skills in `.agents/skills/*/SKILL.md`

If architecture is still unclear after reading config and docs, inspect a small number of representative code files to find real entrypoints, package boundaries, and execution flow.

If docs conflict with executable sources, trust the executable source and keep only what can be verified.

### 3. Extract high-signal facts

Capture only what an agent would need to work effectively:

- **Exact developer commands** — especially non-obvious ones (e.g., `make test` vs `pytest`). Include at least one narrow validation command when available.
- **Command order** when it matters, e.g. `lint → typecheck → test`.
- **Monorepo / multi-package boundaries**, ownership of major directories, and real app/library entrypoints.
- **Framework or toolchain quirks** — generated code, migrations, codegen, build artifacts, special env loading, dev servers, infra deploy flow.
- **Repo-specific style or workflow conventions** that differ from language/framework defaults.
- **Testing quirks** — fixtures, integration test prerequisites, snapshot workflows, required services, flaky or expensive suites.
- **Safety and review constraints** — security requirements, approval workflows, risky commands, environment limits.
- **Existing instruction file content worth preserving** — reconcile before adding new rules.
- **Existing skill affordances** — project skills in `.agents/skills` that agents should know exist, especially validation, setup, PR hygiene, or common generation workflows.

Good `AGENTS.md` content is usually hard-earned context that took reading multiple files to infer.

### 4. Choose the smallest durable instruction surface

1. **Root `AGENTS.md`** — repo-wide context, commands, architecture, conventions, safety rules, and a brief skill inventory.
2. **Nested `AGENTS.md`** — subtree-specific commands, generated-code rules, prerequisites, or safety constraints that would distract from root guidance.
3. **`.agents/skills/<skill-name>/SKILL.md`** — reusable multi-step workflows with clear trigger conditions and repeatable outputs.
4. **`CLAUDE.md`** — optional compatibility shim containing only `@AGENTS.md`.

Merge or remove overlapping instruction files that duplicate root guidance or conflict with verified sources. When in doubt, omit.

### 5. Write AGENTS.md

- Title it clearly (e.g., "Repository Guidelines" or the repo name).
- Use Markdown headings (`#`, `##`) for structure.
- Keep it **200–400 words** — be concise.
- Place sections in this order when applicable:
  1. **Project Structure & Module Organization** — where source, tests, assets live.
  2. **Build, Test, and Development Commands** — key commands with brief explanations.
  3. **Coding Style & Naming Conventions** — indentation, style prefs, formatting/linting tools.
  4. **Testing Guidelines** — frameworks, coverage requirements, test naming, how to run.
  5. **Commit & Pull Request Guidelines** — commit conventions, PR requirements.
  6. **(Optional) Security & Configuration Tips** — env vars, secrets, deployment.
  7. **(Optional) Agent-Specific Instructions** — any tooling or workflow quirks for AI agents.
  8. **(Optional) Agent Skills** — project skills available in `.agents/skills`, when to use them, and where new reusable skills should be saved.
- Keep explanations short, direct, and specific to this repository.
- Provide examples where helpful (commands, directory paths, naming patterns).

If the repo is simple, keep the file simple. If the repo is large, summarize only the structural facts that change how an agent should work.

### 6. Add nested AGENTS.md files only when useful

- Live at the boundary they describe, such as `frontend/AGENTS.md`, `packages/api/AGENTS.md`, or `services/billing/AGENTS.md`
- Contain only guidance specific to that subtree
- Avoid repeating root `AGENTS.md`; rely on root guidance remaining applicable unless contradicted locally
- Stay concise and verifiable, usually shorter than the root guide

Do not add nested `AGENTS.md` files just to mirror the directory tree or split generic advice.

### 7. Handle project skills

Use `.agents/skills` as the project skill location for all new project skills.

When `.agents/skills` exists:

- Read each `SKILL.md` frontmatter and skim instructions for purpose.
- Mention only skills that are relevant to normal repo work; avoid listing generic personal skills or experiments.
- Include each skill by folder/name and a short trigger, e.g. "`/skill:better-init` — refreshes repo instructions and project skills."

When creating or improving a project skill:

- Save it as `.agents/skills/<skill-name>/SKILL.md`.
- Follow the Agent Skills specification: a directory containing `SKILL.md`, YAML frontmatter, required `name` and `description`, and Markdown instructions.
- Keep `name` lowercase, hyphenated, under 64 characters, and matching the parent directory.
- Use a specific description that says both what the skill does and when to use it.
- You may include broadly supported frontmatter extensions such as `disable-model-invocation: true` when the skill should be invoked explicitly rather than auto-loaded.
- Put scripts in `scripts/`, detailed docs in `references/`, and templates/examples in `assets/` using relative paths from the skill root.
- When pre-approving bundled scripts, use narrow `allowed-tools` entries for the exact script commands, such as `Bash(python3 scripts/validate.py:*)`; avoid broad `Bash`/`shell` approvals and machine-specific paths.
- Add evals only when the skill has objective behavior worth testing, such as file transforms, fixed workflows, or code generation.

Prioritize project skills that reduce time-to-first-success:

- Repo bootstrap and setup verification
- Fast validation paths for format, lint, typecheck, and tests
- PR hygiene and contribution workflow
- Common creation workflows such as new package, module, component, migration, or release

Do not create skills that duplicate existing skills or general-purpose agent behavior.

### 8. Ask questions sparingly

Only ask the user if the repo cannot answer something important. Use one short batch at most.

**Good questions:**
- Undocumented team conventions
- Branch / PR / release expectations
- Missing setup or test prerequisites that are known but not written down

**Do not ask** about anything the repo already makes clear.

## Output

Write the final `AGENTS.md` to the repository root. If the file already exists, update it in place. If you create or update skills, save them under `.agents/skills/<skill-name>/SKILL.md`. Print a brief summary of what was added, changed, or removed.
