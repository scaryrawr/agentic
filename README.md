# Agent Skills

This repository stores reusable personal agent skills. Skills live under `skills/<skill-name>/` and each committed skill has a required `SKILL.md`.

Only committed skills are documented here. Local-only skill directories may exist under `skills/`, but they are intentionally omitted from this README unless they are tracked in git. To refresh the committed inventory, use:

```bash
git ls-files 'skills/*/SKILL.md'
```

## Committed skills

| Skill | Purpose |
| --- | --- |
| `azure-devops` | Single Azure DevOps skill: create/inspect/review/manage pull requests, Azure Boards work items and WIQL, URL routing, and PR attachments, with on-demand reference files per use case. |
| `blogify` | Turn video or audio recordings into docs, blog posts, tutorials, changelogs, or notes. |
| `copilot-job-queue` | Coordinate durable coding-job handoffs between Microsoft Scout and GitHub Copilot through a shared SQLite queue. |
| `image-gen` | Generate or edit PNG image artifacts through OMLX/OpenAI-compatible image APIs. |
| `playwright-cli` | Automate browser interactions, test web pages, and work with Playwright tests. |
| `better-init` | Create or improve `AGENTS.md` and project agent-skill guidance for a repository. |
| `skill-creator` | Create, revise, package, evaluate, or optimize Copilot SKILL.md-based skills. |

## Validation

There is no repo-wide package manager or CI. Use targeted checks from the repository root:

```bash
python3 skills/skill-creator/scripts/quick_validate.py skills/<skill-name>
git ls-files 'skills/*/SKILL.md' | while read -r f; do python3 skills/skill-creator/scripts/quick_validate.py "$(dirname "$f")"; done
git ls-files 'skills/*/SKILL.md' | while read -r f; do test -f "$(dirname "$f")/evals/evals.json" -o -f "$(dirname "$f")/evals/trigger-evals.json"; done
git ls-files 'skills/*/evals/*.json' | while read -r f; do python3 -m json.tool "$f" >/dev/null; done
python3 -m py_compile skills/skill-creator/scripts/*.py skills/skill-creator/eval-viewer/*.py
python3 -c "import glob, py_compile; [py_compile.compile(f, doraise=True) for p in ('skills/image-gen/scripts/*.py','skills/blogify/scripts/*.py','skills/ado-*/scripts/*.py') for f in glob.glob(p)]"
```
