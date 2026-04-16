# Adaptive Repo AGENTS

`adaptive-agents-md` 是一个给 Codex 用的 skill，用来为当前仓库生成或更新根目录 `AGENTS.md`。

它不会一上来就写文件，而是先探测仓库状态，再只问缺失的关键问题，先展示计划，最后在确认后写入 `AGENTS.md`，并按需创建 `log/` 与 `knowledge/` 脚手架。

## 适合什么场景

- 空仓库，需要先把 agent 协作规范和个人习惯立起来
- 实验仓库，需要围绕实验目标、判停条件、日志和知识沉淀组织规则
- 成熟仓库，需要保留现有约定，同时把你的个人习惯融合进新的 `AGENTS.md`
- 已经有 `AGENTS.md`、`RULES.md`、`CLAUDE.md` 或 `.cursorrules`，想做提炼和合并

## 核心特点

- 先探测，再提问，再计划，再写入
- 只问 1-3 个高价值问题，不做大段无关追问
- 关键答案缺失时直接停下，不靠猜
- 生成的 `AGENTS.md` 固定分成两段：
  - `## 个人习惯`
  - `## 仓库说明`
- `个人习惯` 是固定的 repo 约定，不会被泛化成空话
- `仓库说明` 只保留真实仓库信息，不用“保持沟通”“注意安全”之类通用废话填充

## 个人习惯约定

这个 skill 会把以下习惯写进生成的 `AGENTS.md`：

- 所有进入仓库的有效会话都要记录到 `log/YYYY-MM-DD.md`
- 日志必须使用 Markdown，并按日期文件追加
- 每条日志至少包含：`任务`、`动作`、`结果`、`反思`
- 有明确后续时补 `下一步`
- 可复用的新结论、踩坑、命令配方、方案比较要沉淀到 `knowledge/<topic>.md`
- 创建 `log/` 或 `knowledge/` 前要先展示计划并等待确认

## 安装

把这个仓库放到 Codex 的技能目录下：

```bash
git clone git@github.com:hypiasd/MySkill.git ~/.codex/skills/adaptive-agents-md
```

如果你已经在本地有这个目录，也可以直接把仓库内容同步进去。

## 在 Codex 里使用

可以直接这样调用：

```text
Use $adaptive-agents-md to inspect the current repository, ask only the missing questions, and propose an AGENTS.md.
```

如果你想连同脚手架一起做，也可以这样说：

```text
Use $adaptive-agents-md to inspect this repo, propose AGENTS.md, and tell me what log/knowledge files you would create.
```

## 本地脚本

### 1. 探测仓库

```bash
python3 scripts/build_agents.py analyze /path/to/repo
```

作用：

- 读取 `README*`、`AGENTS.md`、`RULES.md`、`CLAUDE.md`、`.cursorrules`
- 读取常见清单文件，如 `package.json`、`pyproject.toml`、`Cargo.toml`、`go.mod`、`Makefile`
- 对仓库做连续评分：
  - `完整度`
  - `稳定性`
  - `规则清晰度`
- 把仓库归到更接近 `empty`、`experimental` 或 `mature`
- 给出当前轮最值得问的 1-3 个问题

### 2. 生成计划

```bash
python3 scripts/build_agents.py plan /path/to/repo --answer key=value
```

这个命令会输出：

- 仓库判断
- 探测依据
- 将写入的文件
- 可能创建的脚手架
- `AGENTS.md` 草稿

如果关键答案没给全，它会直接停下并告诉你还缺什么。

### 3. 写入 `AGENTS.md`

```bash
python3 scripts/build_agents.py write /path/to/repo --answer key=value
```

这个命令只写 `AGENTS.md`，不会顺手创建 `log/` 或 `knowledge/`。

### 4. 预览脚手架

```bash
python3 scripts/bootstrap_scaffold.py plan /path/to/repo
```

它会列出将创建的内容：

- `log/`
- `log/YYYY-MM-DD.md`
- `knowledge/`
- `knowledge/TEMPLATE.md`

### 5. 创建脚手架

```bash
python3 scripts/bootstrap_scaffold.py write /path/to/repo
```

## 生成结果长什么样

生成的 `AGENTS.md` 会是这种结构：

```md
# AGENTS

## 个人习惯
...

## 仓库说明
...
```

其中：

- `个人习惯` 固定写你的 repo 约定
- `仓库说明` 根据当前仓库真实情况生成
- 如果仓库原本就有 `AGENTS.md`，会保留有价值的仓库约定并合并进去

## 仓库结构

```text
adaptive-agents-md/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
└── scripts/
    ├── build_agents.py
    └── bootstrap_scaffold.py
```

## 验证

```bash
python3 /Users/tian/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/tian/.codex/skills/adaptive-agents-md
```

## 设计原则

- 不把通用 agent 能力误写成“你的个人习惯”
- 不靠想象补全仓库事实
- 不在用户没确认前直接创建脚手架
- 不用空泛措辞填满 `AGENTS.md`
