---
name: adaptive-agents-md
description: "Create or update a repository-root `AGENTS.md` in a pure LLM flow: inspect repo facts first, infer empty/competition/experimental/mature profile, ask for profile confirmation, ask only missing high-value questions, then show a write plan and wait for confirmation before writing `AGENTS.md` or scaffolding `log/` and `knowledge/`."
---

# Adaptive AGENTS MD

## Overview

Use this skill to generate or update a Chinese `AGENTS.md` for the current repository.

This skill is pure LLM: do not depend on local scripts. The required protocol is:

1. inspect first,
2. show initial repo-type judgement and evidence,
3. wait for confirmation or correction,
4. ask only missing high-value questions,
5. show write plan,
6. write only after explicit confirmation.

This protocol belongs to the skill behavior only. Do not copy the protocol text into the final `AGENTS.md`.

## LLM-Native Protocol (Script-Free)

### 1) Inspect repository facts first

Inspect directly with normal repo exploration (`rg --files`, directory listing, focused file reads). Prioritize:

- `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `RULES.md`
- `README*`
- manifest/build files such as `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Makefile`
- existing `log/`, `knowledge/`, `docs/`, `notes/` directories

Collect concrete facts only (modules, commands, outputs, constraints, existing rules).

Hard rule:

- Do not call local `scripts/*.py`.
- Do not require users to pass `--answer` style CLI inputs.
- Keep all reasoning and questioning in natural conversation.

### 2) Score and classify before asking broad questions

Score the repo along:

- `完整度`
- `稳定性`
- `规则清晰度`

Then infer the closest profile:

- `empty`
- `competition`
- `experimental`
- `mature`

When reporting the judgement, always include:

- inferred type
- 2-5 concrete evidence points
- short confidence note

### 3) Confirm or correct repo type first

Before any follow-up questions, ask for repo-type confirmation.

Rules:

- If user confirms, continue with that type.
- If user corrects, switch to corrected type immediately.
- If user is uncertain or ambiguous, stay in confirmation step and ask one concise clarification.
- Do not treat arbitrary non-empty replies as confirmation.

### 4) Ask only missing high-value questions (1-3 per round)

After profile confirmation, ask only what is still missing. Keep each round to 1-3 questions.

First-priority question focus:

- Empty repo: project goal + expected output
- Competition repo: competition context + submission form + hard constraints
- Experimental repo: experiment goal + stop condition
- Mature repo: existing conventions + conflict points with personal habits

If critical answers are still missing, stop and ask; do not silently assume.

### 5) Show write plan before any mutation

Before writing anything, show a concrete plan containing:

- files to create/update
- why each change is needed (repo facts or user answers)
- whether `log/` / `knowledge/` scaffolding will be created
- exact scaffold paths
- a concise preview of `AGENTS.md` structure

Then wait for explicit confirmation.

### 6) Write in two confirmation gates

Gate A:

- create/update `AGENTS.md` only after explicit confirmation.

Gate B:

- create scaffold files (`log/`, `knowledge/`) only after explicit confirmation.

Do not auto-create scaffolding without that second confirmation.

## Personal Habits To Embed (Fixed Contract)

`## 个人习惯` is fixed to the user's concrete conventions; do not infer it from repo content.

Must include:

- every meaningful repository session is logged
- log path default: `log/YYYY-MM-DD.md`
- log format: Markdown; append by date
- each log entry includes at least: `时间`、`任务`、`动作`、`结果`、`反思` (and `下一步` when useful)
- before creating missing `log/` files, first show creation plan, then create after confirmation
- reusable conclusions/pitfalls/command recipes/option comparisons are captured in `knowledge/KNOWLEDGE.md`
- one repository uses one knowledge file (do not split into many files)
- knowledge structure stays as `总览索引 + 主题分组`
- theme classification should be coarse and adaptive, and synonym themes should be merged to avoid fragmentation (for example `RAG` and `检索链路`)
- each knowledge entry includes `背景`、`结论`、`证据 / 命令`、`决策`、`未决问题` plus a related log reference
- before creating missing `knowledge/` files, first show creation plan, then create after confirmation

Explicitly forbid filler text in this section:

- generic agent common sense such as “保持沟通 / 注意安全 / 先理解需求”

## AGENTS.md Output Shape

Always produce:

```markdown
# AGENTS

## 个人习惯
...

## 仓库说明
...
```

Rules for `## 仓库说明`:

- include only facts grounded in repository evidence or user answers
- keep it concise and practical:
  - repo purpose / module overview
  - key directories
  - start/build/test/check commands
  - rule entry files
  - delivery/artifact locations
- avoid generic padding language
- if existing `AGENTS.md` exists, do not overwrite wholesale; merge and refine useful repo-specific content
- if only `CLAUDE.md` / `.cursorrules` / `RULES.md` exist, extract repo-factual parts into `仓库说明`

## Merge and Scaffold Strategy

When no `AGENTS.md` exists:

- create a new Chinese `AGENTS.md`
- put `个人习惯` first
- generate concise `仓库说明` from facts

When `AGENTS.md` already exists:

- do not replace the whole page
- insert or update `个人习惯` near the front
- preserve useful existing repo guidance
- deduplicate and merge old content into cleaner concise sections

Scaffold defaults (after confirmation only):

- `log/YYYY-MM-DD.md`
- `knowledge/KNOWLEDGE.md`

Suggested default sections:

- Log entry: `时间 / 任务 / 动作 / 结果 / 反思 / 下一步`
- Knowledge entry: `背景 / 结论 / 证据或命令 / 决策 / 未决问题`

## Verification Expectations

Recommended smoke checks for this skill behavior:

- empty repo
- competition/experimental repo
- mature repo
- repo with existing `AGENTS.md` or other rules files

Acceptance expectations:

- inspect first, then confirm repo type
- block when critical answers are missing
- show plan before write
- `个人习惯` remains stable
- `仓库说明` contains only repo facts
- scaffold creation is always preview-first, confirm-then-write
- no local command or machine-specific path is required anywhere in the normal workflow
