# Skill Creator Workflows

This reference contains command details that are useful during skill evaluation and packaging but too long for `SKILL.md`.

## Copilot compatibility

| Harness | Native skill loading | Eval support |
| --- | --- | --- |
| Copilot CLI | Project skills in `.github/skills/`; personal skills from `~/.agents/skills/` | Trigger evals and task evals via `copilot -p ... --output-format json --allow-all` |

Focus new eval work on Copilot CLI. The scripts still have legacy `--harness pi`, `--harness claude`, `--harness codex`, and `--harness all` options for historical comparisons, but do not use them unless the user explicitly asks for non-Copilot data.

> **Safety: evals execute prompts with `--allow-all`.** `run_eval.py` (trigger evals), `run_harness_eval.py` (task evals), and `run_loop.py` (description optimization) launch real Copilot subprocesses that *carry out* each eval prompt with all permissions, mutating whatever git repo is their working directory. To contain this, the harnesses now default to an **isolated throwaway git sandbox** (`resolve_eval_root`/`create_sandbox_project_root` in `harnesses.py`) that is created per run and deleted on exit — so by default evals cannot touch a real repo. **Only pass `--project-root <dir>` when you deliberately want the eval to act on that directory**; pointing it at a real checkout (especially `~/.agents`) will let prompts create stray branches, bogus `upstream` remotes, and fetched refs there. This exact damage occurred historically before sandboxing was the default. If you do pass an explicit `--project-root`, check that repo for unexpected branches/remotes afterward.

## Task evals

Use task evals when you need actual outputs from Copilot:

```bash
python3 scripts/run_harness_eval.py \
  --evals /path/to/my-skill/evals/evals.json \
  --skill-path /path/to/my-skill \
  --workspace /path/to/my-skill-workspace \
  --iteration 1
```

Useful options:

- `--harness copilot` (default)
- `--model <model-id>`
- `--runs-per-config 3`
- `--no-baseline`
- `--project-root <dir>` — run in this real directory instead of the default disposable sandbox. Only use when the eval is meant to act on that repo; see the safety note above.

The script writes:

```text
<workspace>/iteration-N/
└── eval-<id>-<name>/
    ├── eval_metadata.json
    ├── copilot_with_skill/run-1/
    │   ├── transcript.md
    │   ├── timing.json
    │   └── outputs/
    └── copilot_without_skill/run-1/
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

Trigger evals test whether the frontmatter description causes Copilot to load the skill for realistic prompts:

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
  --runs-per-query 3 \
  --verbose
```

## Description optimization

After the user approves a trigger eval set, run:

```bash
python3 scripts/run_loop.py \
  --eval-set /path/to/trigger-evals.json \
  --skill-path /path/to/my-skill \
  --max-iterations 5 \
  --verbose \
  --results-dir /path/to/my-skill-workspace/description-runs
```

The loop splits train/test, evaluates current and proposed descriptions, writes a live HTML report, and prints JSON containing `best_description`.
