# Notices

This `skill-creator` skill is adapted from Anthropic's `skill-creator` skill in the `anthropics/skills` repository:

- Source: https://github.com/anthropics/skills/tree/main/skills/skill-creator
- License: Apache License, Version 2.0
- Upstream copyright notice: Copyright 2026 Anthropic, PBC.

The Apache-2.0 license text is preserved in `LICENSE.txt`.

## Modification notice

This copy has been modified for GitHub Copilot CLI compatibility and broader agent-harness awareness. Notable changes include:

- Rewrote `SKILL.md` to describe Copilot/pi/Claude/Codex-compatible workflows.
- Added `scripts/harnesses.py` for harness detection, command construction, Copilot project-skill staging, and trigger detection.
- Reworked `scripts/run_eval.py` to run trigger evals against Copilot, pi, Claude Code, or all supported trigger-eval harnesses.
- Reworked `scripts/improve_description.py` and `scripts/run_loop.py` to use the selected harness instead of requiring `claude -p`.
- Added `scripts/run_harness_eval.py` to run task-output evals across harnesses and produce the workspace layout expected by the viewer/benchmark tools.
- Modified `scripts/utils.py` and `scripts/quick_validate.py` to remove the PyYAML dependency for basic skill validation.

Files copied from the upstream project but not substantively modified remain under the upstream Apache-2.0 license.
