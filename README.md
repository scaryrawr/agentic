# Agent Skills

This repository stores reusable personal agent skills. Skills live under `skills/<skill-name>/` and each committed skill has a required `SKILL.md`.

Only committed skills are documented here. Local-only skill directories may exist under `skills/`, but they are intentionally omitted from this README unless they are tracked in git. To refresh the committed inventory, use:

```bash
git ls-files 'skills/*/SKILL.md'
```

## Committed skills

| Skill | Purpose |
| --- | --- |
| `image-gen` | Generate or edit PNG image artifacts through OMLX/OpenAI-compatible image APIs. |
| `init` | Create or improve `AGENTS.md` and project agent-skill guidance for a repository. |
| `skill-creator` | Create, revise, package, evaluate, or optimize SKILL.md-based agent skills. |

## Validation

There is no repo-wide package manager or CI. Use targeted checks from the repository root:

```bash
python3 skills/skill-creator/scripts/quick_validate.py skills/<skill-name>
git ls-files 'skills/*/SKILL.md' | while read -r f; do python3 skills/skill-creator/scripts/quick_validate.py "$(dirname "$f")"; done
python3 -m py_compile skills/skill-creator/scripts/*.py skills/skill-creator/eval-viewer/*.py
bash -n skills/image-gen/scripts/*.sh
```
