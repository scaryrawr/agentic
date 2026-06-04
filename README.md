# agentic

A collection of reusable agent skills for AI coding assistants. Skills work with GitHub Copilot, Claude Code, Cursor, Codex, Gemini CLI, and other agent hosts that support the [Agent Skills specification](https://agentskills.io/specification).

## Skills

| Skill | Description |
|---|---|
| [`init`](#init) | Create or improve `AGENTS.md` and project agent-skill guidance for a repository |
| [`skill-creator`](#skill-creator) | Create, revise, evaluate, or package `SKILL.md`-based skills |
| [`image-gen`](#image-gen) | Generate or edit PNG images via OMLX/OpenAI-compatible image APIs |
| [`ddserve-docs`](#ddserve-docs) | Look up DevDocs documentation using `ddserve` to ground coding work |

---

## Installing Skills

Use the [`gh skill`](https://cli.github.com/manual/gh_skill) CLI to install skills from this repository. Skills can be installed at **user scope** (available in all projects) or **project scope** (available only in the current project).

### Install all skills (user scope)

```sh
gh skill install scaryrawr/agentic init
gh skill install scaryrawr/agentic skill-creator
gh skill install scaryrawr/agentic image-gen
gh skill install scaryrawr/agentic ddserve-docs
```

### Install a skill for a specific project only

```sh
gh skill install --scope project scaryrawr/agentic init
```

### Search for skills in this repository

```sh
gh skill search scaryrawr/agentic
```

### Preview a skill before installing

```sh
gh skill preview scaryrawr/agentic image-gen
```

### Update installed skills

```sh
gh skill update scaryrawr/agentic
```

---

## Skill Details

### `init`

Create or improve `AGENTS.md` and project agent-skill guidance for a repository. Discovers repo structure, build commands, and existing instruction files to write concise, high-signal guidance.

```sh
gh skill install scaryrawr/agentic init
```

**Use when:** setting up a new repo, onboarding AI agents, or refreshing stale `AGENTS.md` content.

---

### `skill-creator`

Create, revise, evaluate, and package `SKILL.md`-based agent skills. Includes validation, packaging, eval, and report tooling.

```sh
gh skill install scaryrawr/agentic skill-creator
```

**Use when:** authoring new skills, improving existing ones, or packaging skills for distribution.

---

### `image-gen`

Generate images from text prompts or edit existing images via OMLX/OpenAI-compatible image APIs. Outputs saved PNG files.

```sh
gh skill install scaryrawr/agentic image-gen
```

**Requires:** `$OMLX_BASE_URL`, `curl`, `jq`, `base64`.

**Use when:** creating or editing images, product shots, icons, or illustrations.

---

### `ddserve-docs`

Look up installed [DevDocs](https://devdocs.io/) documentation using `ddserve` to ground coding work in up-to-date library and framework docs instead of relying on model memory.

```sh
gh skill install scaryrawr/agentic ddserve-docs
```

**Requires:** `ddserve` CLI installed and configured.

**Use when:** implementing, debugging, or configuring code that depends on version-specific framework or library behavior.
