# Skill Creator Workflows

This reference contains command details that are useful during skill evaluation and packaging but too long for `SKILL.md`.

## Harness compatibility

| Harness | Native skill loading | Eval support |
| --- | --- | --- |
| Copilot CLI | Project skills in `.github/skills/`; personal skills from `~/.agents/skills/` | Trigger evals and task evals via `copilot -p ... --output-format json --allow-all` |
| pi | Explicit `--skill <path>` and discovered personal skills | Trigger evals and task evals via `pi --skill` and baseline via `--no-skills` |
| Claude Code | Native skills/commands depending on version | Trigger evals through temporary `.claude/commands`; task evals instruct Claude to read the skill |
| Codex CLI | No general SKILL.md trigger mechanism | Task evals inject the skill by instructing Codex to read `SKILL.md`; trigger evals are skipped |

## Task evals

Use task evals when you need actual outputs from one or more harnesses:

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
- `--model <model-id>`
- `--runs-per-config 3`
- `--no-baseline`
- `--project-root <dir>`

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

After task runs, grade each run against `eval_metadata.json` assertions, aggregate, then generate a review page:

```bash
python3 scripts/aggregate_benchmark.py /path/to/workspace/iteration-1 --skill-name my-skill
python3 eval-viewer/generate_review.py \
  /path/to/workspace/iteration-1 \
  --skill-name my-skill \
  --benchmark /path/to/workspace/iteration-1/benchmark.json \
  --static /path/to/workspace/iteration-1/review.html
```

If a desktop browser is available, omit `--static` to start a local server.

## Trigger-description evals

Trigger evals test whether the frontmatter description causes a harness to load the skill for realistic prompts:

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

Use `--harness all` to compare Copilot, pi, and Claude Code where installed.

## Description optimization

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

The loop splits train/test, evaluates current and proposed descriptions, writes a live HTML report, and prints JSON containing `best_description`.
