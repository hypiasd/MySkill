# Adaptive Repo AGENTS

`adaptive-agents-md` 是一个给 Codex 用的 skill，用来为“当前仓库”创建或更新根目录 `AGENTS.md`。

默认是 **纯 LLM** 流程：先探测、再判断、先确认、再提问、先给计划、确认后写入。核心流程不依赖本地脚本，也不提供脚本入口。

## 核心流程

1. 先探测仓库事实（规则文件、README、清单文件、关键目录）。
2. 对 `完整度 / 稳定性 / 规则清晰度` 做连续评分并判断仓库类型（`empty / competition / experimental / mature`）。
3. 先把“判断 + 依据”告诉你，并等待你确认或纠正。
4. 仅在类型确认后，再按轮次提 1-3 个缺失的高价值问题。
5. 关键答案未补齐时停下，不自行假设。
6. 写入前先展示计划（要改哪些文件、依据是什么、会不会建 `log/` 和 `knowledge/`）。
7. 你确认后再写 `AGENTS.md`；脚手架也要单独确认后再创建。

## 内置个人习惯约定

生成的 `AGENTS.md` 前半段固定写这些约定：

- 所有有效会话都要记录日志
- 默认日志路径：`log/YYYY-MM-DD.md`
- 日志是 Markdown，按日期追加
- 每条日志至少包含：`时间`、`任务`、`动作`、`结果`、`反思`（需要时加 `下一步`）
- `log/` 不存在时，先提示计划再创建
- 可复用结论、踩坑、命令配方、方案比较沉淀到 `knowledge/KNOWLEDGE.md`
- 一个仓库只维护一个知识文件
- 知识结构保持“总览索引 + 主题分组”
- 主题自动归类应保持粗粒度，并合并同义主题避免碎片化（如 `RAG` 与 `检索链路`）
- 每条知识至少包含：`背景`、`结论`、`证据 / 命令`、`决策`、`未决问题`，并关联日志
- `knowledge/` 不存在时，先提示计划再创建

不会写“保持沟通”“注意安全”这类通用废话。

## 在 Codex 中使用

示例提示词：

```text
Use $adaptive-agents-md to inspect the current repository first, show your repo-type judgement with evidence, wait for my confirmation, then ask only missing high-value questions and propose an AGENTS.md write plan.
```

如果你还希望它同时处理脚手架计划：

```text
Use $adaptive-agents-md to inspect this repo, confirm repo type with me first, then propose AGENTS.md changes and list exact log/knowledge files to create before writing anything.
```

## 生成结果结构

输出的 `AGENTS.md` 固定是：

```md
# AGENTS

## 个人习惯
...

## 仓库说明
...
```

其中：

- `个人习惯`：固定写你的仓库协作约定
- `仓库说明`：只写当前仓库真实信息（用途、目录、命令、规则入口、产物位置）

## 仓库结构

```text
adaptive-agents-md/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
└── (no runtime scripts)
```

## 可移植性

这个 skill 不要求任何本地脚本命令，也不依赖机器专属绝对路径。复制到任意环境后，直接按对话协议使用即可。
