---
name: skill-creator
description: Use this skill to create, revise, package, evaluate, or optimize agent skills for Copilot, pi, Claude Code, Codex, or compatible SKILL.md-based harnesses. Use it whenever the user wants a new skill, edits to an existing skill, eval/test prompts, skill benchmarking, skill packaging, trigger-description optimization, or cross-harness comparison, even if they say “agent instructions”, “Copilot skill”, “Claude skill”, “pi skill”, or “make this reusable”.
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

This skill helps create, improve, evaluate, and package agent skills. It is a Copilot-compatible adaptation of Anthropic's Apache-2.0 `skill-creator` skill, with added multi-harness support. See `LICENSE.txt` and `NOTICE.md` for attribution and modification notes.

## First principles

A skill is a folder with a required `SKILL.md` file and optional bundled resources:

```text
skill-name/
├── SKILL.md      # required: YAML frontmatter + Markdown instructions
├── scripts/      # optional deterministic/repetitive helpers
├── references/   # optional docs loaded only when needed
├── assets/       # optional templates/media/examples
└── evals/        # optional eval prompts and fixtures, excluded from packages
```

Frontmatter should include at least:

```markdown
---
name: skill-name
description: Use this skill when ...
---
```

Keep the description specific and a bit assertive: it is the main signal that Copilot/pi/Claude use to decide whether to load the skill.

## Harness compatibility quick reference

| Harness | Native skill loading | Eval support in this skill |
| --- | --- | --- |
| Copilot CLI | Project skills in `.github/skills/`; personal skills from `~/.agents/skills/` | Trigger evals and task evals via `copilot -p ... --output-format json --allow-all` |
| pi | Explicit `--skill <path>` and discovered personal skills | Trigger evals and task evals via `pi --skill` and baseline via `--no-skills` |
| Claude Code | Native skills/commands depending on version | Trigger evals through temporary `.claude/commands`; task evals instruct Claude to read the skill |
| Codex CLI | No general SKILL.md trigger mechanism | Task evals inject the skill by instructing Codex to read `SKILL.md`; trigger evals are skipped |

Use this skill's bundled `scripts/run_eval.py --harness auto` for the current harness, or `--harness all` to run every available trigger-eval-capable harness. Use bundled `scripts/run_harness_eval.py --harness all` for task-output comparisons across harnesses.

## Creating a skill

### 1. Capture intent

Before writing, identify:

1. What task should the skill make easier or more reliable?
2. When should the skill trigger? Include user phrases, adjacent contexts, and near misses.
3. What output should the agent produce?
4. What dependencies or tools are expected?
5. Are objective evals useful? File transforms, data extraction, code generation, and fixed workflows usually benefit from evals; subjective writing/design tasks may rely more on human review.

Extract answers from the current conversation first, then ask only for missing details.

### 2. Draft `SKILL.md`

Use a structure like:

```markdown
---
name: example-skill
description: Use this skill for ...
---

# Example Skill

## When to use
...

## Workflow
1. ...
2. ...

## Output format
...

## References
- Read `references/foo.md` when ...
```

Writing guidance:

- Prefer clear imperatives over vague descriptions.
- Explain why steps matter so the agent can generalize.
- Keep `SKILL.md` lean; move long docs to `references/` and point to them.
- Bundle scripts when repeated deterministic work appears in eval transcripts.
- For bundled scripts, use narrowly scoped `allowed-tools` entries such as `Bash(python3 scripts/validate.py:*)` instead of broad `Bash`/`shell` approvals or machine-specific paths.
- Avoid surprising behavior, credential collection, data exfiltration, exploit code, or anything inconsistent with the user's stated intent.

### 3. Add evals

Create `evals/evals.json` with realistic prompts:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "name": "descriptive-case-name",
      "prompt": "User's realistic task prompt",
      "expected_output": "Human-readable success criteria",
      "files": [],
      "expectations": [
        "The output includes ...",
        "The generated file ..."
      ]
    }
  ]
}
```

See `references/schemas.md` for schemas used by the viewer and benchmark tools.

## Running task evals

Prefer `scripts/run_harness_eval.py` when you want actual task outputs from one or more harnesses. Do not hard-code install locations, copy scripts elsewhere, or use non-bundled wrappers.

```bash
python3 scripts/run_harness_eval.py \
  --evals /path/to/my-skill/evals/evals.json \
  --skill-path /path/to/my-skill \
  --workspace /path/to/my-skill-workspace \
  --iteration 1 \
  --harness copilot
```

Useful options:

- `--harness auto|all|copilot|pi|claude|codex`
- `--model <model-id>` to pass a model to the harness
- `--runs-per-config 3` for variance analysis
- `--no-baseline` when baseline is not meaningful
- `--project-root <dir>` to control where Copilot/Claude/Codex run

The script writes:

```text
<workspace>/iteration-N/
└── eval-<id>-<name>/
    ├── eval_metadata.json
    ├── <harness>_with_skill/run-1/
    │   ├── transcript.md
    │   ├── timing.json
    │   └── outputs/
    └── <harness>_without_skill/run-1/
```

After task runs:

1. Grade each run against `eval_metadata.json` assertions. Use `agents/grader.md` for the expected grading JSON format. Programmatic checks are best when possible.
2. Aggregate:
   ```bash
   python3 scripts/aggregate_benchmark.py /path/to/workspace/iteration-1 --skill-name my-skill
   ```
3. Generate a review page:
   ```bash
   python3 eval-viewer/generate_review.py \
     /path/to/workspace/iteration-1 \
     --skill-name my-skill \
     --benchmark /path/to/workspace/iteration-1/benchmark.json \
     --static /path/to/workspace/iteration-1/review.html
   ```

If a desktop browser is available, omit `--static` to start a local server.

## Running trigger-description evals

Trigger evals test whether a skill's `description` causes the harness to load the skill for realistic queries.

Create a JSON eval set:

```json
[
  {"query": "realistic prompt that should use the skill", "should_trigger": true},
  {"query": "near-miss prompt that should not use it", "should_trigger": false}
]
```

Run:

```bash
python3 scripts/run_eval.py \
  --eval-set /path/to/trigger-evals.json \
  --skill-path /path/to/my-skill \
  --harness copilot \
  --runs-per-query 3 \
  --verbose
```

Use `--harness all` to compare Copilot, pi, and Claude Code where installed. Codex is skipped for trigger evals because it has no native SKILL.md trigger mechanism.

## Optimizing descriptions

After the user approves a trigger eval set, run:

```bash
python3 scripts/run_loop.py \
  --eval-set /path/to/trigger-evals.json \
  --skill-path /path/to/my-skill \
  --harness copilot \
  --max-iterations 5 \
  --verbose \
  --results-dir /path/to/my-skill-workspace/description-runs
```

The loop splits train/test, evaluates current and proposed descriptions, writes a live HTML report, and prints JSON containing `best_description`. Apply the best description to `SKILL.md` only after reviewing scores and checking that it still accurately describes the skill.

## Iteration loop

1. Draft or revise the skill.
2. Run a small set of evals with skill and baseline.
3. Generate the viewer so the human can inspect outputs before you over-correct.
4. Read feedback and grading results.
5. Improve instructions, examples, or scripts based on patterns across evals.
6. Repeat with a new iteration directory.
7. Package when the user is satisfied.

Generalize from feedback instead of overfitting to a single test case. If multiple evals independently cause the agent to write the same helper code, bundle that helper in `scripts/`.

## Packaging

Validate and package a skill with:

```bash
python3 scripts/quick_validate.py /path/to/my-skill
python3 scripts/package_skill.py /path/to/my-skill /path/to/dist
```

The packager creates a `.skill` zip archive and excludes root `evals/`, `__pycache__`, `node_modules`, `.DS_Store`, and `*.pyc`.

## Copilot-specific notes

- Copilot project skills live under `.github/skills/<skill-name>/SKILL.md`.
- Copilot personal skills are loaded from `~/.agents/skills/` in this environment.
- For non-interactive evals, this skill uses `copilot -p ... --allow-all --output-format json --silent` based on `copilot help`.
- Baseline Copilot runs cannot currently disable personal skills via a public CLI flag. The eval script avoids staging the skill for baseline and tells the agent not to use a task-specific skill, but if the same skill is installed globally the baseline may still see it. Prefer testing a working copy with a unique name when strict baselines matter.

## Reference files

- `agents/grader.md` — grade assertions against outputs.
- `agents/comparator.md` — blind A/B comparison instructions.
- `agents/analyzer.md` — benchmark pattern analysis and post-hoc comparison analysis.
- `references/schemas.md` — JSON schemas.
- `eval-viewer/generate_review.py` — static/server review page generator.
