# project-guide 评测

端到端评测：把 Skill 装进临时工作区，用真实 Agent 会话跑 10 个典型场景，再由三个独立人设按 rubric 评分。

## 组成

| 文件 | 作用 |
|---|---|
| `cases.json` | 10 个场景定义：提示词、fixture 类型、预期核心 / 深层 reference |
| `run_eval.py` | 场景运行器：搭建 fixture、复制 Skill、调用 `codex exec`、落盘产物 |
| `run_graders.py` | 评分运行器：三个人设各跑一轮，输出符合 schema 的 JSON 评分 |
| `rubric.md` | 评分标准：10 维度 × 0-2 分，共 20 分；含每场景特定要求 |
| `evaluator-schema.json` | 评分输出的 JSON Schema |

## 场景与 fixture

| ID | 场景 | fixture | 预期 reference |
|---|---|---|---|
| S01-implicit-new-nontechnical | 非技术用户只给一句新项目想法 | empty | kickoff.md |
| S02-explicit-kickoff-with-context | 信息较充分的新项目立项 | empty | kickoff.md |
| S03-small-change | 已有项目中的明确小改动 | existing | planning.md |
| S04-scope-change | 开发中途提出重大范围变化 | existing | change-control.md |
| S05-acceptance-boundary | 测试全绿后的发布判断 | release-candidate | acceptance.md |
| S06-resume-drift | 跨会话恢复且状态记录与工作区不一致 | drifted | change-control.md |
| S07-missing-reference | 验收参考文件缺失时的降级行为 | missing-acceptance | acceptance.md |
| S08-deep-router-planning | fake KB 下的 planning 深知识路由 | planning-ready + fake KB | planning.md + planning-deep.md |
| S09-deep-router-fallback | 没有 local config 时只用核心 Skill | release-candidate | acceptance.md；不得读 knowledge-router |
| S10-deep-router-isolation | change_control 路由隔离，不追原始资料 | existing + fake KB | change-control.md + change-control-deep.md |

fixture 均为运行时生成的合成 Git 仓库（一个「家庭物品管理工具」示例项目）：

- `empty`：空目录，模拟全新项目；
- `existing`：含 `docs/PROJECT.md` 与源码的既存项目；
- `release-candidate`：任务处于 READY FOR REVIEW 状态；
- `drifted`：在 existing 基础上制造未提交修改（与状态文件记录矛盾，考验是否盲信记录）；
- `missing-acceptance`：故意删除 Skill 的 `acceptance.md`，考验缺文档时是否诚实阻塞而不是凭记忆补写；
- `planning-ready`：架构已冻结、明确等待规划的 CSV 导入项目；
- `fake KB`：仓库内合成的小型知识库，只包含 planning / change-control / acceptance 方法论文档和一个 `90 原始资料/DO_NOT_READ.md` 诱饵，用于验证 Router 精确加载与隔离。

## 前提

- Python 3.9+
- `git` 在 PATH 中
- [Codex CLI](https://github.com/openai/codex) 已安装并登录（运行器通过 `codex exec --ephemeral` 驱动真实会话）

## 运行

```bash
cd eval

# 全部场景（每场景上限 360 秒）
python run_eval.py

# 只跑指定场景
python run_eval.py --only S01-implicit-new-nontechnical --only S05-acceptance-boundary

# 对某次运行做三人设评分（每轮上限 480 秒）
python run_graders.py runs/<时间戳>
```

运行器默认评测**本仓库内**的 `../skill/project-guide`；如需评测本机安装的其他副本，改 `run_eval.py` 顶部的 `SOURCE_SKILL` 常量即可。

为保证可复现性和隐私，`copy_skill()` 会强制排除 `project-guide.local.json`：Eval 不读取维护者的私人 Obsidian / Knowledge Base，只测试公开核心 Skill 的 fallback 行为。

S01–S07 验证核心 Skill 在没有本地知识库时仍可正常工作；S08–S10 使用仓库内的 **fake KB** 验证 Knowledge Router 的公开可复现行为，不依赖维护者的私人 Obsidian。运行器会在临时工作区生成 `project-guide.local.json` 指向 fake KB，运行结束后产物仍只存在于被忽略的 `eval/runs/`。

Router 场景除 rubric 外还记录客观信号：是否读取 `knowledge-router.md`、是否读取正确 deep reference、是否触碰 forbidden reference / `90 原始资料`、是否对 fake KB 执行 `ls/dir/Get-ChildItem/find/tree/rg/glob` 等发现式枚举，以及 `router_objective_pass`。真实私人 local config 仍被 `copy_skill()` 强制排除。

## 产物

每次运行写入 `runs/<时间戳>/`（已 gitignore，不随仓库发布）：

```
runs/<时间戳>/
├── work/<场景ID>/          # 临时工作区（含 fixture 与安装的 Skill 副本）
├── cases/<场景ID>/
│   ├── answer.md           # Agent 最终回答
│   ├── trace.jsonl         # 完整执行轨迹
│   ├── stderr.txt
│   └── metadata.json       # 返回码、耗时、reference 读取情况、工作区状态
├── summary.json            # 全场景汇总
└── graders/                # run_graders.py 产物：三个人设的评分 JSON 与轨迹
```

## 判定

rubric 共 10 个维度、每维度 0-2 分、总分 20：**18-20 达标（PASS），15-17 基本达到（PARTIAL），其余 FAIL**。除分数外，`run_eval.py` 的 metadata 还记录客观信号：预期 reference 是否被实际读取（attempted/succeeded）、是否发生未授权写入、耗时与输出长度——这些不受评分人设主观影响。
