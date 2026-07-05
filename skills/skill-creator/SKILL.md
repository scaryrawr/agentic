---
name: skill-creator
description: Use this skill to create, revise, package, evaluate, or optimize GitHub Copilot skills and reusable SKILL.md-based agent instructions. Use it whenever the user wants a new Copilot skill, edits to an existing skill, eval/test prompts, skill benchmarking, skill packaging, trigger-description optimization, or reusable agent instructions.
license: Apache-2.0
allowed-tools: >-
  Bash(python3 scripts/quick_validate.py:*)
  Bash(python3 scripts/package_skill.py:*)
  Bash(python3 scripts/run_eval.py:*)
  Bash(python3 scripts/run_harness_eval.py:*)
  Bash(python3 scripts/run_loop.py:*)
  Bash(python3 scripts/improve_description.py:*)
  Bash(python3 scripts/aggregate_benchmark.py:*)
  Bash(python3 scripts/generate_report.py:*)
  Bash(python3 eval-viewer/generate_review.py:*)
---

# Skill Creator

Use this file as the operating checklist after the skill has loaded. Attribution and modification notes are in `LICENSE.txt` and `NOTICE.md`.

## First principles

A skill is a folder with a required `SKILL.md` file and optional bundled resources:

```text
skill-name/
├── SKILL.md
├── scripts/
├── references/
├── assets/
└── evals/
```

Frontmatter must include `name` and `description`. Keep `name` lowercase kebab-case and matching the folder. Keep `description` specific because Copilot uses it for trigger decisions, but do not repeat that description in the body. Quote or block-scalar descriptions that contain YAML-sensitive punctuation such as `: `.

Keep `SKILL.md` lean. Move long explanations to `references/`, deterministic helpers to `scripts/`, templates or examples to `assets/`, and objective eval prompts or fixtures to `evals/`. Body and reference files should assume they are already loaded or intentionally opened: explain how to proceed, not why the skill or reference should be used.

## Workflow

1. Capture intent from the conversation before asking questions: task, trigger conditions, expected output, dependencies, near misses, and whether objective evals are useful.
2. Draft or revise `SKILL.md` with clear imperatives, concise workflow steps, and only the context the agent needs after the skill has loaded.
3. Add or maintain `evals/evals.json` for objective behaviors such as file transforms, fixed workflows, code generation, benchmark comparisons, and trigger-sensitive descriptions.
4. Prefer bundled scripts when repeated deterministic work appears in eval transcripts. Use narrowly scoped `allowed-tools` entries such as `Bash(python3 scripts/validate.py:*)`, and make sure every command shown in the workflow is covered by `allowed-tools` or a bundled helper.
5. Validate, run the smallest useful eval set, review failures across cases, then revise for general behavior rather than overfitting one prompt.
6. Package only after validation and eval review are satisfactory.

## Evals and optimization

- Use `scripts/run_harness_eval.py` for Copilot task-output evals.
- Use `scripts/run_eval.py` for Copilot trigger-description evals.
- Use `scripts/run_loop.py` only after the trigger eval set is approved; apply a proposed description only after checking that it remains accurate.
- Grade task runs against `eval_metadata.json` assertions. Programmatic checks are best when practical; otherwise use `agents/grader.md`.
- If an eval prompt says a file is provided, include that fixture in `evals/files/` and list it in `evals/evals.json`; otherwise write the prompt so it is runnable without input files.

Read `references/workflows.md` for exact Copilot eval commands, output layout, aggregation, and review-page generation.

## Safety and quality

- Avoid surprising behavior, credential collection, data exfiltration, exploit code, or anything inconsistent with the user's stated intent.
- Do not hard-code machine-specific install paths or copy bundled scripts elsewhere.
- Keep baselines honest: Copilot cannot fully disable personal skills via a public flag, so prefer unique working-copy skill names when strict baselines matter.

## Packaging

```bash
python3 scripts/quick_validate.py /path/to/my-skill
python3 scripts/package_skill.py /path/to/my-skill /path/to/dist
```

The packager creates a `.skill` zip archive and excludes root `evals/`, `__pycache__`, `node_modules`, `.DS_Store`, and `*.pyc`.

## Reference files

- `references/workflows.md` — commands for task evals, trigger evals, description optimization, aggregation, and reports.
- `references/schemas.md` — JSON schemas.
- `agents/grader.md` — grade assertions against outputs.
- `agents/comparator.md` — blind A/B comparison instructions.
- `agents/analyzer.md` — benchmark pattern analysis and post-hoc comparison analysis.
- `eval-viewer/generate_review.py` — static/server review page generator.
