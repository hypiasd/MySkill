---
name: adaptive-agents-md
description: Create or update a repository-root `AGENTS.md` by first inspecting the current repo, classifying whether it is empty, experimental, or mature, asking only the missing high-value questions, then proposing a write plan before creating `AGENTS.md` and optional `log/` plus `knowledge/` scaffolding. Use when a user wants repo-specific agent instructions, personal workflow conventions, or bootstrapped logging and knowledge directories for the current repository.
---

# Adaptive AGENTS MD

## Overview

Use this skill to generate a Chinese `AGENTS.md` that starts with the user's personal habits and then adds concise, repo-specific operating guidance. Do not write the file directly from intuition: inspect first, ask only the missing questions, show a write plan, and wait for confirmation before mutating the target repository.

## Workflow

1. Inspect the repository first.
   - Run:
   ```bash
   python3 scripts/build_agents.py analyze /path/to/repo
   ```
   - This scores the repo on `完整度 / 稳定性 / 规则清晰度`, labels it as closer to empty, experimental, or mature, and returns the first round of high-value questions.

2. Ask only the missing questions.
   - Ask 1-3 questions per round.
   - Respect the analyzer's first priority:
     - Empty repo: ask for project goal and expected output.
     - Experimental repo: ask for experiment goal and stop condition.
     - Mature repo: ask for existing conventions and conflicts with the user's habits.
   - If a critical answer is missing, stop. Do not silently assume it.

3. Build a plan before any write.
   - Convert the user's answers into `--answer key=value` flags and run:
   ```bash
   python3 scripts/build_agents.py plan /path/to/repo --answer key=value
   ```
   - Show the resulting plan to the user before writing. The plan lists:
     - repo classification and evidence
     - files that will be written
     - scaffold files that would be created if approved
     - the `AGENTS.md` draft

4. Write `AGENTS.md` only after explicit confirmation.
   - Run:
   ```bash
   python3 scripts/build_agents.py write /path/to/repo --answer key=value
   ```
   - This writes only `AGENTS.md`.

5. Bootstrap `log/` and `knowledge/` only after explicit confirmation.
   - Preview:
   ```bash
   python3 scripts/bootstrap_scaffold.py plan /path/to/repo
   ```
   - Apply:
   ```bash
   python3 scripts/bootstrap_scaffold.py write /path/to/repo
   ```

## Personal Habits To Embed

Always render the `## 个人习惯` section exactly around these repo-level conventions instead of generic agent advice:

- Record every meaningful repository session in `log/YYYY-MM-DD.md`.
- Use Markdown logs and append by date instead of creating arbitrary filenames.
- Keep each log entry concrete: `任务`、`动作`、`结果`、`反思`，and add `下一步` when useful.
- Before creating `log/` or any log file, tell the user which files will be created and wait for confirmation.
- When the work produces reusable conclusions, pitfalls, command recipes, or option comparisons, write them into `knowledge/<topic>.md`.
- Before creating `knowledge/` or any knowledge file, tell the user which files will be created and wait for confirmation.

Do not replace these habits with generic wording such as "communicate clearly" or "be safe". Those are baseline agent abilities, not the user's personal repo conventions.

## AGENTS.md Shape

Generate a concise Chinese document with this fixed high-level structure:

```markdown
# AGENTS

## 个人习惯
...

## 仓库说明
...
```

Rules for `## 仓库说明`:

- Include only repo facts that can be grounded in discovered files or in the user's answers.
- Prefer concise sections such as repo purpose, key directories, commands, rule entrypoints, and artifact locations.
- If the repo lacks enough evidence, keep the section short rather than padding it with generic advice.
- If `AGENTS.md` already exists, preserve useful repo-specific guidance and merge the personal habits section in front.
- If older guidance uses headings, keep it readable by nesting it under the new `## 仓库说明` section rather than pasting it as a second full document.

## Bundled Scripts

### `scripts/build_agents.py`

Use this for repo inspection, missing-question generation, plan rendering, draft generation, and final `AGENTS.md` writes.

Commands:

```bash
python3 scripts/build_agents.py analyze /path/to/repo
python3 scripts/build_agents.py plan /path/to/repo --answer project_goal="..."
python3 scripts/build_agents.py write /path/to/repo --answer project_goal="..." --answer expected_output="..."
```

Exit behavior:

- `analyze`: returns repo facts plus the current question set.
- `plan`: renders a write plan and draft; exits non-zero if critical answers are missing.
- `write`: writes `AGENTS.md`; exits non-zero if critical answers are missing.

### `scripts/bootstrap_scaffold.py`

Use this for deterministic scaffold previews and creation.

Commands:

```bash
python3 scripts/bootstrap_scaffold.py plan /path/to/repo
python3 scripts/bootstrap_scaffold.py write /path/to/repo
```

The scaffold script only manages:

- `log/YYYY-MM-DD.md`
- `knowledge/TEMPLATE.md`

It is intentionally narrow so the agent can tell the user exactly what will be created.

## Validation

- Validate the skill itself with:
```bash
python3 /Users/tian/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/tian/.codex/skills/adaptive-agents-md
```
- Before trusting a repo draft, run at least one `analyze` pass and one `plan` pass.
- For existing `AGENTS.md`, inspect the merged draft before `write` so preserved guidance still reads cleanly.
