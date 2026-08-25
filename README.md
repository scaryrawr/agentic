# Agent Skills

This repository maintains reusable personal agent skills that are not owned by a plugin repository. Skills live under `skills/<skill-name>/` and each committed skill has a required `SKILL.md`.

Only committed skills are documented here. Local-only skill directories may exist under `skills/`, but they are intentionally omitted from this README unless they are tracked in git. To refresh the committed inventory, use:

```bash
git ls-files 'skills/*/SKILL.md'
```

## Committed skills

| Skill           | Purpose                                                                                                                             |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `better-init`   | Create or improve `AGENTS.md` and project agent-skill guidance for a repository.                                                    |
| `code-review`   | Perform a thorough code review of diffs or branch comparisons for correctness, structure, regression risk, and edge-case coverage. |
| `skill-creator` | Create, revise, package, evaluate, or optimize Copilot SKILL.md-based skills.                                                       |

## ScaryPilot-owned plugins

[ScaryPilot](https://github.com/scaryrawr/scarypilot) is the canonical source for the skills that previously lived here:

| Plugin          | Canonical skill paths                                                                 |
| --------------- | -------------------------------------------------------------------------------------- |
| `azure-devops`  | `plugins/azure-devops/skills/azure-devops`                                             |
| `omlx-media`    | `plugins/omlx-media/skills/blogify`, `plugins/omlx-media/skills/image-gen`              |

For GitHub Copilot CLI, install the plugins from the ScaryPilot marketplace:

```bash
copilot plugin marketplace add scaryrawr/scarypilot
copilot plugin install azure-devops@scarypilot
copilot plugin install omlx-media@scarypilot
```

To install an individual skill for another compatible agent:

```bash
gh skill install scaryrawr/scarypilot plugins/azure-devops/skills/azure-devops --scope user
gh skill install scaryrawr/scarypilot plugins/omlx-media/skills/blogify --scope user
gh skill install scaryrawr/scarypilot plugins/omlx-media/skills/image-gen --scope user
```

If a skill was previously installed from `scaryrawr/agentic`, add `--force` once so the installer replaces its source-tracking metadata.

## Validation

There is no repo-wide package manager or CI. Use targeted checks from the repository root:

```bash
python3 skills/skill-creator/scripts/quick_validate.py skills/<skill-name>
git ls-files 'skills/*/SKILL.md' | while read -r f; do python3 skills/skill-creator/scripts/quick_validate.py "$(dirname "$f")"; done
git ls-files 'skills/*/SKILL.md' | while read -r f; do test -f "$(dirname "$f")/evals/evals.json" -o -f "$(dirname "$f")/evals/trigger-evals.json"; done
git ls-files 'skills/*/evals/*.json' | while read -r f; do python3 -m json.tool "$f" >/dev/null; done
python3 -m py_compile skills/skill-creator/scripts/*.py skills/skill-creator/eval-viewer/*.py
```
