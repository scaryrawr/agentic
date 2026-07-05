# Agent Skills

This repository stores reusable personal agent skills. Skills live under `skills/<skill-name>/` and each committed skill has a required `SKILL.md`.

Only committed skills are documented here. Local-only skill directories may exist under `skills/`, but they are intentionally omitted from this README unless they are tracked in git. To refresh the committed inventory, use:

```bash
git ls-files 'skills/*/SKILL.md'
```

## Committed skills

| Skill | Purpose |
| --- | --- |
| `ado-cli` | Route Azure DevOps links and resource requests to the right Azure DevOps skill. |
| `ado-make-pr` | Create Azure DevOps pull requests from current changes. |
| `ado-pr` | Inspect and manage existing Azure DevOps pull requests. |
| `ado-review-pr` | Review Azure DevOps pull requests and post high-confidence findings. |
| `ado-work-items` | Inspect and manage Azure DevOps work items. |
| `blogify` | Turn video or audio recordings into docs, blog posts, tutorials, changelogs, or notes. |
| `image-gen` | Generate or edit PNG image artifacts through OMLX/OpenAI-compatible image APIs. |
| `init` | Create or improve `AGENTS.md` and project agent-skill guidance for a repository. |
| `skill-creator` | Create, revise, package, evaluate, or optimize Copilot SKILL.md-based skills. |

## Validation

There is no repo-wide package manager or CI. Use targeted checks from the repository root:

```bash
python3 skills/skill-creator/scripts/quick_validate.py skills/<skill-name>
git ls-files 'skills/*/SKILL.md' | while read -r f; do python3 skills/skill-creator/scripts/quick_validate.py "$(dirname "$f")"; done
git ls-files 'skills/*/SKILL.md' | while read -r f; do test -f "$(dirname "$f")/evals/evals.json" -o -f "$(dirname "$f")/evals/trigger-evals.json"; done
git ls-files 'skills/*/evals/*.json' | while read -r f; do python3 -m json.tool "$f" >/dev/null; done
python3 -m py_compile skills/skill-creator/scripts/*.py skills/skill-creator/eval-viewer/*.py
bash -n skills/image-gen/scripts/*.sh
```
