# project-guide

项目指导 Skill——让 AI 以「项目领航员」身份，带着（多半不懂技术的）用户从一句想法走完**立项、产品设计、架构、规划、实现、验收、发布**的完整开发流程。

## 它解决什么问题

把开发直接丢给 AI 时常见三类失败：

1. 不先确定目标和范围就开工，做到一半返工；
2. 用流程压垮非技术用户，或反过来什么都不问就擅自扩大范围；
3. 把「测试全绿」当成「可以上线」，测试、人工验收、真实部署三种证据互相冒充。

project-guide 把一套交付纪律做成 AI 可执行的运行时规范：先决定做什么再决定怎么做、按任务大小裁剪流程、每类证据各归各位、外部动作必须显式授权、跨会话以项目状态文件为锚点。

## 触发方式

安装后，Agent 在以下情况自动加载本 Skill：

- 用户想新建项目：「我想做…」「带我做一个项目」「我不懂技术，你来」
- 恢复或继续项目：「继续」「接着做」
- 问下一步：「下一步做什么」「排期」「里程碑」「拆任务」「需求规划」
- 卡在调试中、跨会话交接，或问「能不能上线」「做完了吗」

也可以用 `$project-guide` 显式调用。

## 安装

`skill/project-guide/` 是一个标准 Agent Skill（`SKILL.md` + `references/`），复制到你所用 Agent 客户端的技能目录即可，例如：

```bash
git clone https://github.com/<你的账号>/project-guide.git
cp -r project-guide/skill/project-guide ~/.agents/skills/
# 或 ~/.claude/skills/ 等你客户端的技能目录
```

无需其他依赖；Skill 本身只有 Markdown。

## 仓库结构

```
project-guide/
├── README.md
├── LICENSE
├── skill/project-guide/   # Skill 本体（可直接复制安装）
│   ├── SKILL.md           # 主控规范：阶段地图、准出门、状态文件、汇报格式
│   └── references/        # 按情况加载的分阶段细则
│       ├── kickoff.md     # 立项引导
│       ├── planning.md    # 规划与任务拆解
│       ├── coding-loop.md # 实现阶段的 Coding 循环
│       ├── acceptance.md  # 验收与发布判定
│       ├── change-control.md # 新需求分类与跨会话交接
│       └── authority.md   # 操作权限边界
├── docs/
│   └── design.md          # 设计说明：原则、结构、来源与修订模型
└── eval/                  # 可复现评测：场景、评分标准、运行器
```

## 评测

`eval/` 提供一套可复现的端到端评测：7 个典型场景（新项目立项、小改动、范围突变、发布判定、状态漂移、参考缺失等），在临时 Git 工作区中运行真实 Agent 会话，再由三个独立人设（非技术用户 / 工程负责人 / 验收 QA）按 20 分制 rubric 评分，18 分以上视为达标。

```bash
cd eval
python run_eval.py                 # 运行全部场景，产物写入 eval/runs/<时间戳>/
python run_eval.py --only S01-implicit-new-nontechnical
python run_graders.py runs/<时间戳>   # 三人设评分
```

前提：Python 3.9+、`git`、已登录的 [Codex CLI](https://github.com/openai/codex)（评测通过 `codex exec` 驱动真实会话）。详见 [eval/README.md](eval/README.md)。

## 来源与许可

本 Skill 蒸馏自作者的《Vibe Coding 手册》（私有研究库，不随本仓库发布），修订方向为手册 → 技能，见 [docs/design.md](docs/design.md)。

[MIT License](LICENSE)
