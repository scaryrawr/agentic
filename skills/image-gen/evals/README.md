# image-gen evals

- `evals.json` contains task evals for text-to-image generation and image editing.
- `trigger-evals.json` contains description-trigger checks for prompts that should/should not load the skill.
- `files/edit-base.png` is a deterministic 512x512 PNG fixture for edit evals. It has a central blue square, green circle, orange triangle, grid, and border so each edit eval starts from the same base state.
- `files/edit-center-mask.png` is an optional matching mask fixture for future mask-capable edit evals. The current task eval does not require masks because the local `FLUX.2-klein-4B-mxfp8` edit model reports that masks are unsupported.

Example task eval run from the skill-creator directory:

```bash
cd "$HOME/.agents/skills/skill-creator"
python -m scripts.run_harness_eval \
  --evals "$HOME/.agents/skills/image-gen/evals/evals.json" \
  --skill-path "$HOME/.agents/skills/image-gen" \
  --workspace /tmp/image-gen-eval-workspace \
  --harness pi \
  --no-baseline \
  --iteration 1
```

Example trigger eval run:

```bash
cd "$HOME/.agents/skills/skill-creator"
python -m scripts.run_eval \
  --eval-set "$HOME/.agents/skills/image-gen/evals/trigger-evals.json" \
  --skill-path "$HOME/.agents/skills/image-gen" \
  --harness pi \
  --runs-per-query 1 \
  --verbose
```
