#!/usr/bin/env python3
"""Plan or create narrow repo scaffolding for logs and knowledge notes."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


LOG_TEMPLATE = """# 会话日志

## {entry_date}

### 任务
- 

### 动作
- 

### 结果
- 

### 反思
- 

### 下一步
- 
"""

KNOWLEDGE_TEMPLATE = """# 知识沉淀模板

## 背景
- 

## 结论
- 

## 证据 / 命令
- 

## 决策
- 

## 未决问题
- 
"""


def ensure_repo(path_str: str) -> Path:
    repo = Path(path_str).expanduser().resolve()
    if not repo.exists():
        raise FileNotFoundError(f"Repository not found: {repo}")
    if not repo.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {repo}")
    return repo


def build_plan(repo: Path, entry_date: str) -> dict:
    log_dir = repo / "log"
    knowledge_dir = repo / "knowledge"
    log_file = log_dir / f"{entry_date}.md"
    knowledge_file = knowledge_dir / "TEMPLATE.md"

    items = [
        {"path": str(log_dir), "kind": "dir", "exists": log_dir.exists()},
        {"path": str(log_file), "kind": "file", "exists": log_file.exists()},
        {"path": str(knowledge_dir), "kind": "dir", "exists": knowledge_dir.exists()},
        {"path": str(knowledge_file), "kind": "file", "exists": knowledge_file.exists()},
    ]

    return {
        "repo": str(repo),
        "entry_date": entry_date,
        "items": items,
        "creates": [item for item in items if not item["exists"]],
        "already_present": [item for item in items if item["exists"]],
    }


def render_plan(plan: dict) -> str:
    lines = [
        "# 脚手架计划",
        "",
        f"- 仓库：`{plan['repo']}`",
        f"- 日志日期文件：`log/{plan['entry_date']}.md`",
        "",
        "## 将创建",
    ]
    creates = plan["creates"]
    if creates:
        for item in creates:
            name = Path(item["path"]).name
            display = f"{name}/" if item["kind"] == "dir" else name
            lines.append(f"- `{display}` ({item['kind']})")
            lines.append(f"  路径：`{item['path']}`")
    else:
        lines.append("- 当前脚手架已齐全，无需创建。")

    lines.append("")
    lines.append("## 已存在")
    existing = plan["already_present"]
    if existing:
        for item in existing:
            lines.append(f"- `{item['path']}`")
    else:
        lines.append("- 无")
    return "\n".join(lines) + "\n"


def write_scaffold(plan: dict) -> list[str]:
    created = []
    entry_date = plan["entry_date"]
    for item in plan["creates"]:
        path = Path(item["path"])
        if item["kind"] == "dir":
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.name == f"{entry_date}.md":
            path.write_text(LOG_TEMPLATE.format(entry_date=entry_date), encoding="utf-8")
        else:
            path.write_text(KNOWLEDGE_TEMPLATE, encoding="utf-8")
        created.append(str(path))
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or create repo log/knowledge scaffolding.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("plan", "write"):
        sub = subparsers.add_parser(name)
        sub.add_argument("repo", help="Path to the target repository")
        sub.add_argument("--date", default=str(date.today()), help="Date for the log file in YYYY-MM-DD format")
        sub.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")

    args = parser.parse_args()

    try:
        repo = ensure_repo(args.repo)
        plan = build_plan(repo, args.date)
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    if args.command == "plan":
        if args.json:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
        else:
            print(render_plan(plan))
        return 0

    created = write_scaffold(plan)
    if args.json:
        print(json.dumps({"created": created, "plan": plan}, ensure_ascii=False, indent=2))
    else:
        print(render_plan(plan))
        if created:
            print("[OK] Created:")
            for item in created:
                print(f"- {item}")
        else:
            print("[OK] Nothing to create.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
