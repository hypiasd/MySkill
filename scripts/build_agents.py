#!/usr/bin/env python3
"""Inspect a repository and generate an adaptive AGENTS.md draft."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
from pathlib import Path


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    ".next",
    ".turbo",
    "dist",
    "build",
    "target",
    "coverage",
    ".venv",
    "venv",
}
RULE_FILE_NAMES = {"AGENTS.md", "CLAUDE.md", ".cursorrules", "RULES.md"}
MANIFEST_FILE_NAMES = {
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "Makefile",
}
README_PATTERN = re.compile(r"^README(?:\..+)?$", re.IGNORECASE)
SOURCE_DIR_CANDIDATES = {
    "src",
    "app",
    "lib",
    "cmd",
    "pkg",
    "internal",
    "packages",
    "services",
}
TEST_DIR_CANDIDATES = {"test", "tests", "__tests__"}
DOC_DIR_CANDIDATES = {"docs", "doc", "notes", "knowledge"}
ARTIFACT_DIR_CANDIDATES = {"dist", "build", "out", "output", "artifacts", "reports", "coverage"}
EXPERIMENT_KEYWORDS = {"experiment", "prototype", "sandbox", "spike", "poc", "demo", "trial"}
COMPETITION_KEYWORDS = {
    "competition",
    "contest",
    "hackathon",
    "kaggle",
    "challenge",
    "比赛",
    "竞赛",
    "赛题",
    "赛道",
    "挑战赛",
    "黑客松",
    "算法赛",
}
PROFILE_LABELS = {
    "empty": "空仓库",
    "competition": "比赛仓库",
    "experimental": "实验仓库",
    "mature": "成熟仓库",
}
PROFILE_ALIASES = {
    "empty": {"empty", "blank", "starter", "空仓库", "空项目", "新仓库", "初始化仓库"},
    "competition": {
        "competition",
        "contest",
        "hackathon",
        "kaggle",
        "challenge",
        "比赛",
        "竞赛",
        "赛题",
        "赛道",
        "挑战赛",
        "黑客松",
    },
    "experimental": {
        "experimental",
        "experiment",
        "prototype",
        "sandbox",
        "poc",
        "spike",
        "demo",
        "实验",
        "试验",
        "原型",
        "探索",
    },
    "mature": {
        "mature",
        "production",
        "stable",
        "maintained",
        "成熟",
        "正式",
        "生产",
        "稳定",
        "长期维护",
    },
}
CONFIRM_WORDS = {"confirm", "confirmed", "yes", "y", "ok", "对", "是", "正确", "可以", "没问题"}
NEGATIVE_WORDS = {"no", "not", "wrong", "不对", "不是", "不准确", "不太对", "有误"}
PERSONAL_HABITS = """## 个人习惯

- 所有进入仓库的有效会话都要记录到 `log/YYYY-MM-DD.md`。
- 日志必须使用 Markdown，并按日期文件追加，而不是随意新建命名。
- 每条日志至少包含：`任务`、`动作`、`结果`、`反思`；有明确后续时补 `下一步`。
- 如果仓库里还没有 `log/`，先说明将创建哪些日志文件，再等待确认后创建。
- 只要形成了可复用的新结论、踩坑、命令配方或方案比较，就沉淀到 `knowledge/<topic>.md`。
- 如果仓库里还没有 `knowledge/`，先说明将创建哪些知识文件，再等待确认后创建。
"""


def relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def walk_repo(repo: Path, max_depth: int = 3) -> tuple[list[Path], list[Path]]:
    files: list[Path] = []
    dirs: list[Path] = []
    for current_root, dirnames, filenames in os.walk(repo):
        current_path = Path(current_root)
        rel_parts = current_path.relative_to(repo).parts
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        if len(rel_parts) > max_depth:
            dirnames[:] = []
            continue
        dirs.extend(current_path / name for name in dirnames)
        files.extend(current_path / name for name in filenames)
    return files, dirs


def safe_read_text(path: Path, limit: int = 200_000) -> str:
    try:
        data = path.read_bytes()[:limit]
    except OSError:
        return ""
    return data.decode("utf-8", errors="ignore")


def collect_top_level_dirs(repo: Path) -> list[str]:
    names = []
    for child in sorted(repo.iterdir(), key=lambda item: item.name.lower()):
        if child.is_dir() and child.name not in SKIP_DIRS:
            names.append(child.name)
    return names


def find_named_files(repo: Path, predicate) -> list[Path]:
    files, _ = walk_repo(repo)
    return sorted([path for path in files if predicate(path.name)], key=lambda p: relative(p, repo))


def extract_readme_summary(readmes: list[Path]) -> tuple[str | None, str | None]:
    for readme in readmes:
        content = safe_read_text(readme)
        if not content.strip():
            continue
        title = None
        paragraph_lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                if paragraph_lines:
                    break
                continue
            if stripped.startswith("# ") and not title:
                title = stripped[2:].strip()
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith("```"):
                break
            paragraph_lines.append(stripped)
            if sum(len(part) for part in paragraph_lines) > 220:
                break
        summary = " ".join(paragraph_lines).strip() or None
        if title or summary:
            return title, summary
    return None, None


def extract_keyword_hits(samples: str, keywords: set[str]) -> set[str]:
    hits = set()
    lowered = samples.lower()
    for keyword in keywords:
        needle = keyword.lower()
        if needle in lowered:
            hits.add(keyword)
    return hits


def profile_label(profile: str) -> str:
    return PROFILE_LABELS.get(profile, profile)


def detect_profile_from_text(text: str) -> str | None:
    lowered = text.strip().lower()
    for profile in ("competition", "experimental", "mature", "empty"):
        for alias in PROFILE_ALIASES[profile]:
            if alias.lower() in lowered:
                return profile
    return None


def resolve_profile_confirmation(raw_value: str | None, suggested_profile: str) -> dict:
    if not raw_value or not raw_value.strip():
        return {
            "is_resolved": False,
            "effective_profile": suggested_profile,
            "raw_value": raw_value or "",
            "note": "还没有用户确认当前判断。",
        }

    value = raw_value.strip()
    lowered = value.lower()
    override = detect_profile_from_text(value)
    has_negative = any(word in lowered for word in NEGATIVE_WORDS)
    has_confirm = any(word in lowered for word in CONFIRM_WORDS)

    if override:
        note = (
            "用户接受了当前判断。"
            if override == suggested_profile
            else f"用户将仓库类型从 {profile_label(suggested_profile)} 修正为 {profile_label(override)}。"
        )
        return {
            "is_resolved": True,
            "effective_profile": override,
            "raw_value": value,
            "note": note,
        }

    if has_confirm and not has_negative:
        return {
            "is_resolved": True,
            "effective_profile": suggested_profile,
            "raw_value": value,
            "note": "用户接受了当前判断。",
        }

    if has_negative:
        return {
            "is_resolved": False,
            "effective_profile": suggested_profile,
            "raw_value": value,
            "note": "用户否认了当前判断，但还没有给出可解析的新类型。",
        }

    return {
        "is_resolved": True,
        "effective_profile": suggested_profile,
        "raw_value": value,
        "note": "用户补充了说明，但没有改动当前判断。",
    }


def build_profile_confirmation_prompt(suggested_profile: str, facts: dict, confirmation: dict) -> str:
    evidence_preview = "；".join(facts["evidence"][:2]) if facts["evidence"] else "当前证据较少"
    if confirmation["raw_value"] and not confirmation["is_resolved"]:
        return (
            f"我初步判断这更像 `{profile_label(suggested_profile)}`，依据是：{evidence_preview}。"
            "你刚才否认了这个判断，但还没有给出更贴近的类型。"
            "请直接确认，或者明确纠正为 `empty / competition / experimental / mature` 中更贴近的一种，并补一句原因。"
        )
    return (
        f"我初步判断这更像 `{profile_label(suggested_profile)}`，依据是：{evidence_preview}。"
        "这个判断对吗？如果不对，请直接纠正为 `empty / competition / experimental / mature` 中更贴近的一种，并补一句原因。"
    )


def parse_package_commands(path: Path) -> list[dict[str, str]]:
    content = safe_read_text(path)
    if not content:
        return []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return []
    package_manager = str(data.get("packageManager", "")).lower()
    runner = "npm run"
    if package_manager.startswith("pnpm@"):
        runner = "pnpm"
    elif package_manager.startswith("yarn@"):
        runner = "yarn"
    commands = []
    preferred = ["dev", "start", "build", "test", "lint", "check", "format"]
    keys = [name for name in preferred if name in scripts]
    if not keys:
        keys = list(scripts.keys())[:5]
    for key in keys:
        command = f"{runner} {key}" if runner != "npm run" else f"npm run {key}"
        commands.append({"label": key, "command": command, "source": path.name})
    return commands


def parse_pyproject_commands(path: Path) -> list[dict[str, str]]:
    raw = path.read_bytes()
    try:
        data = tomllib.loads(raw.decode("utf-8", errors="ignore"))
    except tomllib.TOMLDecodeError:
        return []
    commands: list[dict[str, str]] = []
    tool = data.get("tool", {})
    if isinstance(tool, dict):
        poe = tool.get("poe", {})
        if isinstance(poe, dict):
            tasks = poe.get("tasks", {})
            if isinstance(tasks, dict):
                for name in list(tasks.keys())[:5]:
                    commands.append({"label": name, "command": f"poe {name}", "source": path.name})
        if "pytest" in tool:
            commands.append({"label": "test", "command": "pytest", "source": path.name})
        if "ruff" in tool:
            commands.append({"label": "check", "command": "ruff check .", "source": path.name})
    return dedupe_commands(commands)


def parse_makefile_commands(path: Path) -> list[dict[str, str]]:
    content = safe_read_text(path)
    if not content:
        return []
    targets = []
    for line in content.splitlines():
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.-]+):(?:\s|$)", line)
        if not match:
            continue
        target = match.group(1)
        if target.startswith("."):
            continue
        targets.append(target)
    commands = []
    preferred = ["dev", "run", "build", "test", "lint", "check", "format"]
    selected = [name for name in preferred if name in targets]
    if not selected:
        selected = targets[:5]
    for target in selected:
        commands.append({"label": target, "command": f"make {target}", "source": path.name})
    return commands


def parse_cargo_commands(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return [
        {"label": "build", "command": "cargo build", "source": path.name},
        {"label": "test", "command": "cargo test", "source": path.name},
        {"label": "run", "command": "cargo run", "source": path.name},
    ]


def parse_go_commands(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return [
        {"label": "build", "command": "go build ./...", "source": path.name},
        {"label": "test", "command": "go test ./...", "source": path.name},
    ]


def dedupe_commands(commands: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    result = []
    for item in commands:
        key = (item["label"], item["command"])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def collect_commands(repo: Path, manifests: dict[str, list[Path]]) -> list[dict[str, str]]:
    commands: list[dict[str, str]] = []
    for path in manifests.get("package.json", []):
        commands.extend(parse_package_commands(path))
    for path in manifests.get("pyproject.toml", []):
        commands.extend(parse_pyproject_commands(path))
    for path in manifests.get("Makefile", []):
        commands.extend(parse_makefile_commands(path))
    for path in manifests.get("Cargo.toml", []):
        commands.extend(parse_cargo_commands(path))
    for path in manifests.get("go.mod", []):
        commands.extend(parse_go_commands(path))
    return dedupe_commands(commands)


def collect_repo_facts(repo: Path) -> dict:
    files, _ = walk_repo(repo)
    file_count = len(files)
    readmes = find_named_files(repo, lambda name: bool(README_PATTERN.match(name)))
    rules = find_named_files(repo, lambda name: name in RULE_FILE_NAMES)
    manifests = {
        name: find_named_files(repo, lambda file_name, target=name: file_name == target)
        for name in MANIFEST_FILE_NAMES
    }
    top_dirs = collect_top_level_dirs(repo)
    title, summary = extract_readme_summary(readmes)
    commands = collect_commands(repo, manifests)
    artifact_dirs = [name for name in top_dirs if name in ARTIFACT_DIR_CANDIDATES]
    source_dirs = [name for name in top_dirs if name in SOURCE_DIR_CANDIDATES]
    test_dirs = [name for name in top_dirs if name in TEST_DIR_CANDIDATES]
    doc_dirs = [name for name in top_dirs if name in DOC_DIR_CANDIDATES]

    readme_body_samples = " ".join(safe_read_text(path)[:2000] for path in readmes[:2])
    joined_samples = " ".join(
        [
            repo.name.lower(),
            title.lower() if title else "",
            summary.lower() if summary else "",
            " ".join(top_dirs).lower(),
            " ".join(relative(path, repo).lower() for path in readmes[:2]),
            readme_body_samples.lower(),
        ]
    )
    experiment_hits = extract_keyword_hits(joined_samples, EXPERIMENT_KEYWORDS)
    competition_hits = extract_keyword_hits(joined_samples, COMPETITION_KEYWORDS)

    completeness = 0
    completeness += 15 if readmes else 0
    completeness += 25 if any(manifests.values()) else 0
    completeness += 20 if source_dirs else 0
    completeness += 15 if test_dirs else 0
    completeness += 10 if doc_dirs else 0
    completeness += 10 if rules else 0
    completeness += 5 if file_count >= 20 else 0
    completeness += 5 if file_count >= 100 else 0
    completeness = min(100, completeness)

    stability = 10
    stability += 15 if any(manifests.values()) else 0
    stability += 20 if test_dirs else 0
    stability += 10 if doc_dirs else 0
    stability += 10 if rules else 0
    stability += 10 if artifact_dirs else 0
    stability += 10 if file_count >= 50 else 0
    stability -= 25 if experiment_hits else 0
    stability -= 10 if file_count < 10 else 0
    stability = max(0, min(100, stability))

    rule_clarity = 0
    rule_clarity += 20 if readmes else 0
    rule_clarity += min(45, len(rules) * 15)
    rule_clarity += 10 if doc_dirs else 0
    rule_clarity += 10 if commands else 0
    rule_clarity += 5 if "log" in top_dirs else 0
    rule_clarity += 5 if "knowledge" in top_dirs else 0
    rule_clarity = min(100, rule_clarity)

    if completeness < 20 and file_count <= 5 and not any(manifests.values()) and not rules:
        repo_profile = "empty"
    elif competition_hits:
        repo_profile = "competition"
    elif (
        (stability >= 55 and completeness >= 60)
        or (any(path.name == "AGENTS.md" for path in rules) and completeness >= 60)
        or (len(rules) >= 2 and completeness >= 55)
    ):
        repo_profile = "mature"
    else:
        repo_profile = "experimental"

    repo_title = title or repo.name
    purpose = summary
    if not purpose:
        if manifests["package.json"]:
            content = safe_read_text(manifests["package.json"][0])
            try:
                purpose = json.loads(content).get("description") or None
            except json.JSONDecodeError:
                purpose = None
        if not purpose and manifests["Cargo.toml"]:
            raw = manifests["Cargo.toml"][0].read_bytes()
            try:
                cargo_data = tomllib.loads(raw.decode("utf-8", errors="ignore"))
                package = cargo_data.get("package", {})
                if isinstance(package, dict):
                    purpose = package.get("description") or None
            except tomllib.TOMLDecodeError:
                purpose = None

    evidence = []
    if readmes:
        evidence.append(f"发现 README：{', '.join(relative(path, repo) for path in readmes[:3])}")
    if any(manifests.values()):
        manifest_hits = [name for name, paths in manifests.items() if paths]
        evidence.append(f"发现清单文件：{', '.join(manifest_hits)}")
    if rules:
        evidence.append(f"发现规则入口：{', '.join(relative(path, repo) for path in rules)}")
    if source_dirs:
        evidence.append(f"关键源码目录：{', '.join(source_dirs)}")
    if test_dirs:
        evidence.append(f"测试目录：{', '.join(test_dirs)}")
    if competition_hits:
        evidence.append(f"命中比赛关键词：{', '.join(sorted(competition_hits))}")
    if experiment_hits:
        evidence.append(f"命中实验性关键词：{', '.join(sorted(experiment_hits))}")
    if not evidence:
        evidence.append("未发现足够多的仓库特征文件，当前更接近空仓库。")

    sources = sorted(
        {
            *(relative(path, repo) for path in readmes),
            *(relative(path, repo) for path in rules),
            *(
                relative(path, repo)
                for paths in manifests.values()
                for path in paths
            ),
        }
    )

    return {
        "repo": str(repo),
        "repo_name": repo.name,
        "repo_title": repo_title,
        "purpose": purpose,
        "top_dirs": top_dirs,
        "source_dirs": source_dirs,
        "test_dirs": test_dirs,
        "doc_dirs": doc_dirs,
        "artifact_dirs": artifact_dirs,
        "has_log_dir": "log" in top_dirs,
        "has_knowledge_dir": "knowledge" in top_dirs,
        "rules": [relative(path, repo) for path in rules],
        "readmes": [relative(path, repo) for path in readmes],
        "manifests": {name: [relative(path, repo) for path in paths] for name, paths in manifests.items()},
        "commands": commands,
        "file_count": file_count,
        "scores": {
            "completeness": completeness,
            "stability": stability,
            "rule_clarity": rule_clarity,
        },
        "profile": repo_profile,
        "profile_label": profile_label(repo_profile),
        "evidence": evidence,
        "competition_hits": sorted(competition_hits),
        "experiment_hits": sorted(experiment_hits),
        "sources": sources,
    }


def question_spec(
    suggested_profile: str,
    effective_profile: str,
    facts: dict,
    answers: dict[str, str],
    confirmation: dict,
) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    if not confirmation["is_resolved"]:
        return [
            {
                "id": "repo_profile_confirmation",
                "prompt": build_profile_confirmation_prompt(suggested_profile, facts, confirmation),
                "why": "先确认仓库性质，再继续追问细节，避免把比赛仓库误当成实验仓库。",
            }
        ]

    profile = effective_profile
    if profile == "empty":
        if "project_goal" not in answers:
            specs.append(
                {
                    "id": "project_goal",
                    "prompt": "这个仓库要完成什么目标？请用一句话说明它最终要解决的问题。",
                    "why": "空仓库缺少最基本的项目目标，无法生成有信息量的仓库说明。",
                }
            )
        if "expected_output" not in answers:
            specs.append(
                {
                    "id": "expected_output",
                    "prompt": "你期望这个仓库最终交付什么？例如应用、脚本、实验报告或模板。",
                    "why": "需要知道产出形态，才能写清 `AGENTS.md` 的仓库说明与交付约定。",
                }
            )
        if not any(facts["manifests"].values()) and "tech_stack" not in answers:
            specs.append(
                {
                    "id": "tech_stack",
                    "prompt": "如果你已经有倾向，请补一句计划使用的技术栈或主要语言。",
                    "why": "空仓库没有清单文件时，这能帮助补足最小的仓库事实。",
                }
            )
    elif profile == "competition":
        if "competition_context" not in answers:
            specs.append(
                {
                    "id": "competition_context",
                    "prompt": "这是哪个比赛、赛题或赛道？请用一句话说明当前仓库对应的比赛背景。",
                    "why": "比赛仓库需要先明确赛事上下文，避免误套实验项目的话术。",
                }
            )
        if "submission_form" not in answers:
            specs.append(
                {
                    "id": "submission_form",
                    "prompt": "这次比赛最终要提交什么？例如代码、模型、报告、演示或组合交付。",
                    "why": "交付形态会直接影响 `AGENTS.md` 里关于目录、产物和日志沉淀的要求。",
                }
            )
        if "competition_constraints" not in answers:
            specs.append(
                {
                    "id": "competition_constraints",
                    "prompt": "这次比赛有没有特别重要的限制或评分重点？例如截止时间、格式、评测指标、禁止事项。",
                    "why": "这些约束通常比通用工程习惯更重要，应该优先写进仓库说明。",
                }
            )
    elif profile == "experimental":
        if "experiment_goal" not in answers:
            specs.append(
                {
                    "id": "experiment_goal",
                    "prompt": "这个实验当前在验证什么？请用一句话描述核心假设或实验目标。",
                    "why": "实验仓库的 `AGENTS.md` 需要围绕实验目标组织日志和知识沉淀。",
                }
            )
        if "stop_condition" not in answers:
            specs.append(
                {
                    "id": "stop_condition",
                    "prompt": "什么情况下可以判定这次实验成功、失败或该停止？",
                    "why": "判停条件会影响日志、复盘和知识沉淀的重点。",
                }
            )
    else:
        if "convention_conflicts" not in answers:
            specs.append(
                {
                    "id": "convention_conflicts",
                    "prompt": "当前仓库已有约定里，哪些地方要保留，哪些地方需要让位给你的个人习惯？",
                    "why": "成熟仓库通常已经有规则，需要先明确冲突与保留项再合并。",
                }
            )
    return specs[:3]


def required_answer_ids(profile: str, confirmation: dict) -> list[str]:
    if not confirmation["is_resolved"]:
        return ["repo_profile_confirmation"]
    if profile == "empty":
        return ["repo_profile_confirmation", "project_goal", "expected_output"]
    if profile == "competition":
        return ["repo_profile_confirmation", "competition_context", "submission_form"]
    if profile == "experimental":
        return ["repo_profile_confirmation", "experiment_goal", "stop_condition"]
    return ["repo_profile_confirmation", "convention_conflicts"]


def missing_required_answers(profile: str, answers: dict[str, str], confirmation: dict) -> list[str]:
    if not confirmation["is_resolved"]:
        return ["repo_profile_confirmation"]
    return [answer_id for answer_id in required_answer_ids(profile, confirmation) if not answers.get(answer_id)]


def parse_answers(raw_answers: list[str]) -> dict[str, str]:
    answers = {}
    for item in raw_answers:
        if "=" not in item:
            raise ValueError(f"Invalid --answer value: {item!r}. Use key=value.")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError("Answer key cannot be empty.")
        answers[key] = value
    return answers


def format_commands(commands: list[dict[str, str]]) -> list[str]:
    lines = []
    for item in commands[:8]:
        lines.append(f"- `{item['command']}`")
        lines.append(f"  来源：`{item['source']}`，用途标签：`{item['label']}`")
    return lines


def render_repo_overview(facts: dict, answers: dict[str, str]) -> list[str]:
    lines = ["### 仓库概览"]
    summary_bits = []
    current_profile = facts.get("effective_profile", facts["profile"])
    if facts["purpose"]:
        summary_bits.append(facts["purpose"])
    if current_profile == "empty":
        goal = answers.get("project_goal")
        output = answers.get("expected_output")
        if goal:
            summary_bits.append(goal)
        if output:
            summary_bits.append(f"预期交付：{output}")
        if answers.get("tech_stack"):
            summary_bits.append(f"计划技术栈：{answers['tech_stack']}")
    elif current_profile == "competition":
        if answers.get("competition_context"):
            summary_bits.append(f"比赛背景：{answers['competition_context']}")
        if answers.get("submission_form"):
            summary_bits.append(f"提交物：{answers['submission_form']}")
        if answers.get("competition_constraints"):
            summary_bits.append(f"关键约束：{answers['competition_constraints']}")
    elif current_profile == "experimental":
        goal = answers.get("experiment_goal")
        stop = answers.get("stop_condition")
        if goal:
            summary_bits.append(f"实验目标：{goal}")
        if stop:
            summary_bits.append(f"判停条件：{stop}")
    else:
        summary_bits.append(f"仓库名称：{facts['repo_title']}")
        if answers.get("convention_conflicts"):
            summary_bits.append(f"合并关注点：{answers['convention_conflicts']}")
    if summary_bits:
        for bit in summary_bits:
            lines.append(f"- {bit}")
    else:
        lines.append("- 当前仓库上下文仍较少，优先参考本文件列出的规则入口和清单文件。")
    return lines


def render_key_dirs(facts: dict) -> list[str]:
    if not facts["top_dirs"]:
        return []
    interesting = [
        name
        for name in facts["top_dirs"]
        if name in SOURCE_DIR_CANDIDATES
        or name in TEST_DIR_CANDIDATES
        or name in DOC_DIR_CANDIDATES
        or name in {"scripts", "log", "knowledge", "examples", "data"}
    ]
    if not interesting:
        interesting = facts["top_dirs"][:8]
    lines = ["### 关键目录"]
    for name in interesting:
        lines.append(f"- `{name}/`")
    return lines


def render_commands(facts: dict) -> list[str]:
    if not facts["commands"]:
        return []
    return ["### 常用命令", *format_commands(facts["commands"])]


def render_rule_entrypoints(facts: dict) -> list[str]:
    lines = []
    rule_paths = facts["rules"]
    if rule_paths or facts["readmes"]:
        lines.append("### 规则入口")
        for path in rule_paths:
            lines.append(f"- `{path}`")
        for path in facts["readmes"][:2]:
            lines.append(f"- `{path}`")
    return lines


def render_artifact_locations(facts: dict) -> list[str]:
    if not facts["artifact_dirs"]:
        return []
    lines = ["### 交付与产物"]
    for name in facts["artifact_dirs"]:
        lines.append(f"- `{name}/`")
    return lines


def strip_personal_section(text: str) -> str:
    stripped = text.strip()
    stripped = re.sub(r"^#\s+AGENTS\s*\n+", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(
        r"^##\s+个人习惯\s*$.*?(?=^##\s+|\Z)",
        "",
        stripped,
        flags=re.MULTILINE | re.DOTALL,
    )
    stripped = re.sub(r"^##\s+仓库说明\s*$", "", stripped, count=1, flags=re.MULTILINE)
    return stripped.strip()


def demote_headings(text: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        marks = match.group(1)
        title = match.group(2)
        return f"{'#' * min(len(marks) + 1, 6)} {title}"

    return re.sub(r"^(#{1,5})\s+(.+)$", _replace, text, flags=re.MULTILINE)


def render_existing_guidance(repo: Path) -> list[str]:
    path = repo / "AGENTS.md"
    if not path.exists():
        return []
    content = safe_read_text(path)
    if not content.strip():
        return []
    cleaned = demote_headings(strip_personal_section(content))
    if not cleaned:
        return []
    return [
        "### 现有约定（保留并并入）",
        "以下内容来自仓库原有 `AGENTS.md`，保留其仓库特定约定：",
        cleaned,
    ]


def render_repo_section(repo: Path, facts: dict, answers: dict[str, str]) -> str:
    chunks = [
        render_repo_overview(facts, answers),
        render_key_dirs(facts),
        render_commands(facts),
        render_rule_entrypoints(facts),
        render_artifact_locations(facts),
        render_existing_guidance(repo),
    ]
    lines = ["## 仓库说明", ""]
    for block in chunks:
        if not block:
            continue
        lines.extend(block)
        lines.append("")
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def render_agents(repo: Path, facts: dict, answers: dict[str, str]) -> str:
    repo_section = render_repo_section(repo, facts, answers)
    return "\n".join(
        [
            "# AGENTS",
            "",
            PERSONAL_HABITS.strip(),
            "",
            repo_section.strip(),
            "",
        ]
    )


def scaffold_plan(facts: dict) -> list[str]:
    plan = []
    if not facts["has_log_dir"]:
        plan.append("`log/` 目录")
    plan.append("`log/YYYY-MM-DD.md`")
    if not facts["has_knowledge_dir"]:
        plan.append("`knowledge/` 目录")
    plan.append("`knowledge/TEMPLATE.md`")
    return plan


def render_plan(repo: Path, facts: dict, answers: dict[str, str], draft: str) -> str:
    lines = [
        "# AGENTS 生成计划",
        "",
        "## 仓库判断",
        f"- 初步判断：`{facts['profile']}`（{profile_label(facts['profile'])}）",
        f"- 当前采用：`{facts['effective_profile']}`（{profile_label(facts['effective_profile'])}）",
        f"- 完整度：`{facts['scores']['completeness']}`",
        f"- 稳定性：`{facts['scores']['stability']}`",
        f"- 规则清晰度：`{facts['scores']['rule_clarity']}`",
        "",
        "## 依据",
    ]
    for item in facts["evidence"]:
        lines.append(f"- {item}")
    lines.extend(["", "## 判断确认"])
    lines.append(f"- {facts['confirmation_note']}")
    lines.extend(["", "## 将写入的文件", "- `AGENTS.md`", "", "## 可能创建的脚手架"])
    for item in scaffold_plan(facts):
        lines.append(f"- {item}")
    if answers:
        lines.extend(["", "## 已使用的回答"])
        for key, value in answers.items():
            lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## 探测来源",
        ]
    )
    for item in facts["sources"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## AGENTS 草稿", "", draft.rstrip()])
    return "\n".join(lines) + "\n"


def build_analysis(repo: Path, answers: dict[str, str]) -> dict:
    facts = collect_repo_facts(repo)
    confirmation = resolve_profile_confirmation(answers.get("repo_profile_confirmation"), facts["profile"])
    effective_profile = confirmation["effective_profile"]
    facts["effective_profile"] = effective_profile
    facts["effective_profile_label"] = profile_label(effective_profile)
    facts["confirmation_note"] = confirmation["note"]
    questions = question_spec(facts["profile"], effective_profile, facts, answers, confirmation)
    return {
        "repo": str(repo),
        "profile": facts["profile"],
        "effective_profile": effective_profile,
        "scores": facts["scores"],
        "evidence": facts["evidence"],
        "sources": facts["sources"],
        "confirmation": confirmation,
        "questions": questions,
        "required_answer_ids": required_answer_ids(effective_profile, confirmation),
        "missing_required_answers": missing_required_answers(effective_profile, answers, confirmation),
        "facts": facts,
    }


def print_analysis(analysis: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(analysis, ensure_ascii=False, indent=2))
        return
    facts = analysis["facts"]
    lines = [
        "# 仓库探测结果",
        "",
        f"- 仓库：`{analysis['repo']}`",
        f"- 初步判断：`{analysis['profile']}`（{profile_label(analysis['profile'])}）",
        f"- 当前采用：`{analysis['effective_profile']}`（{profile_label(analysis['effective_profile'])}）",
        f"- 完整度：`{analysis['scores']['completeness']}`",
        f"- 稳定性：`{analysis['scores']['stability']}`",
        f"- 规则清晰度：`{analysis['scores']['rule_clarity']}`",
        "",
        "## 依据",
    ]
    for item in analysis["evidence"]:
        lines.append(f"- {item}")
    lines.extend(["", "## 当前事实"])
    lines.append(f"- 顶层目录：{', '.join(facts['top_dirs']) or '无'}")
    lines.append(f"- 规则入口：{', '.join(facts['rules']) or '无'}")
    lines.append(f"- 清单文件：{', '.join(name for name, paths in facts['manifests'].items() if paths) or '无'}")
    lines.extend(["", "## 先确认这个判断"])
    lines.append(f"- {analysis['confirmation']['note']}")
    lines.extend(["", "## 当前建议问题"])
    if analysis["questions"]:
        for item in analysis["questions"]:
            lines.append(f"- `{item['id']}`: {item['prompt']}")
            lines.append(f"  原因：{item['why']}")
    else:
        lines.append("- 当前关键问题已满足，可以进入 `plan`。")
    print("\n".join(lines))


def ensure_repo(path_str: str) -> Path:
    repo = Path(path_str).expanduser().resolve()
    if not repo.exists():
        raise FileNotFoundError(f"Repository not found: {repo}")
    if not repo.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {repo}")
    return repo


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an adaptive AGENTS.md draft.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("analyze", "plan", "write"):
        sub = subparsers.add_parser(name)
        sub.add_argument("repo", help="Path to the target repository")
        sub.add_argument("--answer", action="append", default=[], help="Answer override in key=value format")
        sub.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")

    args = parser.parse_args()

    try:
        repo = ensure_repo(args.repo)
        answers = parse_answers(args.answer)
        analysis = build_analysis(repo, answers)
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    if args.command == "analyze":
        print_analysis(analysis, args.json)
        return 0

    missing = analysis["missing_required_answers"]
    if missing:
        prompts = {item["id"]: item["prompt"] for item in analysis["questions"]}
        lines = ["# 仍需回答的问题", ""]
        for key in missing:
            lines.append(f"- `{key}`: {prompts.get(key, '需要补充这个答案后才能继续。')}")
        output = "\n".join(lines) + "\n"
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "missing_answers",
                        "missing_required_answers": missing,
                        "questions": analysis["questions"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(output)
        return 2

    draft = render_agents(repo, analysis["facts"], answers)
    plan_output = render_plan(repo, analysis["facts"], answers, draft)

    if args.command == "plan":
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "ready",
                        "plan": plan_output,
                        "draft": draft,
                        "facts": analysis["facts"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(plan_output)
        return 0

    target = repo / "AGENTS.md"
    target.write_text(draft, encoding="utf-8")
    if args.json:
        print(
            json.dumps(
                {
                    "status": "written",
                    "path": str(target),
                    "facts": analysis["facts"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(plan_output)
        print(f"[OK] Wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
