<p align="center">
  <img src="plugins/rootloom/assets/icon.svg" width="112" alt="Rootloom 标志">
</p>

<h1 align="center">Rootloom</h1>

<p align="center">
  <strong>让 Codex 展示它是如何完成工作的。</strong>
</p>

<p align="center">
  面向 OpenAI Codex 的本地插件：约束代码变更、审查根因、<br>
  显式管理项目指导，并诚实记录验证证据。
</p>

<p align="center">
  <strong>简体中文</strong> · <a href="README.md">English</a>
</p>

<p align="center">
  <a href="https://github.com/liyanqing90/rootloom/actions/workflows/ci.yml"><img src="https://github.com/liyanqing90/rootloom/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/liyanqing90/rootloom?color=6D5EF7" alt="MIT 许可证"></a>
  <a href="https://github.com/liyanqing90/rootloom/releases"><img src="https://img.shields.io/github/v/release/liyanqing90/rootloom?display_name=tag&amp;sort=semver" alt="最新版本"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-39B98F" alt="Python 3.11+">
</p>

Coding Agent 可以跑过一个测试，却仍然修错了真正的不变量；也可能只是建议验证命令却没有执行，或者在命令执行后让仓库状态发生了变化。Rootloom 为 Codex 提供一套小而明确的工程工作流，让这些区别可以被检查。

Rootloom 帮助个人开发者：

- 修改前先追到真正拥有行为的边界；
- 把变更限制在显式、可审查的范围内；
- 根据行为变化与风险选择验证；
- 分开记录建议检查、实际执行命令、最终仓库状态与人工语义判断；
- 让可复用的 `AGENTS.md` 指导与项目记忆保持显式，而不是静默持久化。

> Rootloom 让工作流机制可检查，但不会证明模型的诊断一定正确、修改一定安全，也不会把测试通过等同于语义正确。参见[成熟度与保证](docs/maturity.zh-CN.md)。

## 真实案例：命令通过了，审查仍然失败

Rootloom 在开发自身时遇到过这样的情况：验证命令以退出码 0 结束，却在执行期间新建了被忽略的 `.env`，并把其中的合成值复制到普通文件。如果只根据命令成功判断任务完成，就会接受一份已经无法代表被审查状态的 Capture。

Rootloom 的验证后重新采集改变了最终决定：

- 新出现的敏感路径触发隔离；
- 变更内容没有进入 `diff.patch`；
- 被复制的文件只保留元数据；
- `capture_preserved` 变为 false；
- Strict Review 返回失败，而不是生成通过的完成声明。

当前可以直接运行对应回归：

```bash
python3 -m unittest \
  tests.test_engineering_change.EngineeringChangeTests.test_new_ignored_sensitive_path_is_a_scoped_task_change \
  tests.test_engineering_change.EngineeringChangeTests.test_verification_new_ignored_sensitive_path_quarantines_before_recapture
```

查看完整且带证据引用的[案例说明](docs/case-studies/passing-command-failed-review.zh-CN.md)。

## 60 秒开始使用

需要支持插件的 Codex CLI 或桌面端、Git 与 Python 3.11+。

```bash
codex plugin marketplace add liyanqing90/rootloom
codex plugin add rootloom@rootloom
```

两条命令完成后插件即安装完毕；任何可选层都不会被静默启用。

新建 Codex 任务，然后选择足够轻的工作流：

```text
$operating-coding-change
修复重连竞态，并验证重连、正常断开和取消路径。
```

如果明确需要机器证据 Bundle：

```text
$engineering-change
审查重连修改，并报告真正执行过的验证。
```

插件安装只会让 Skills 可用，不会写入 `~/.codex/AGENTS.md`、安装命令 Rules、启用 Hook、运行 Analyzer 或读取 Project Memory。

## 选择足够轻的工作流

| 需求 | Rootloom Skill | 默认层级 |
| --- | --- | --- |
| 普通实现或缺陷修复 | `$operating-coding-change` | Core |
| 审查 diff、PR、Migration 或架构修改 | `$operating-code-review` | Core |
| 治理公开 API、Migration、安全、基础设施、发布或破坏性修改 | `$operating-high-risk-change` | Core |
| 生成有界 Capture 与机器可读 Evidence Summary | `$engineering-change` | 显式启用 |
| 创建或精炼仓库 `AGENTS.md` 指导 | `$seed-project-guidance`、`$refine-project-guidance` | 显式写入 |
| 检索或记录可复用项目经验 | `$project-memory` | 实验性且显式 |

普通工作仍沿用仓库原有的编辑与测试路径；深度 Evidence 闭环不会成为安装时自动启用的门禁。

## Rootloom 如何工作

```text
任务
  ↓
风险与范围
  ↓
证据 → 根因 → Change Contract → 实现
  ↓
基于行为的验证 → 诚实的完成声明
```

日常 Tier 0/1 任务由当前 Codex Agent 直接使用仓库证据和比例化测试完成。对于高风险或显式治理的审查，Rootloom 还可以绑定：

- 变更前的仓库与 Git 状态；
- 允许与禁止修改的路径；
- 行为 Claim 与真正执行过的命令；
- 验证后的最终仓库 Capture；
- 机器观察证据与操作方语义判断。

<p align="center">
  <img src="docs/diagram/architecture-zh.svg" width="980" alt="Rootloom Personal Core 架构：Change、Review、Guidance、可选 Autonomy/Evidence 与实验性 Project Memory">
</p>

## 什么是 Evidence-honest

- 自动生成的验证计划只标记为“建议”，不会冒充已经执行。
- 只有 Rootloom 观察到命令成功后，才会把它记录为通过。
- 当仓库状态、范围、证据或 Capture 已变化时，单个命令成功不足以完成审查。
- 敏感材料按路径分类并只保留元数据；Rootloom 不是内容感知型 Secret Scanner。
- `REVIEW_EVIDENCE_COMPLETE` 只表示文档化的证据链完整，不表示正确性已经被证明。
- 验证命令属于可信操作方输入，受有界进程树约束执行，但不是运行不可信代码的沙箱。

Wire Format 与详细边界参见[架构](docs/architecture.zh-CN.md)、[成熟度与保证](docs/maturity.zh-CN.md)和[排障](docs/troubleshooting.zh-CN.md)。

<details>
<summary><strong>技术合同速查</strong></summary>

Rootloom Personal Core 仍是**面向 Codex 的可检查个人工程工作流。** 可选层包括 Optional Autonomy、Optional Evidence 与 Experimental Project Memory（也可通过 `$project-memory` 使用）。其中 Engineering Memory 只提供线索，当前仓库证据始终优先。

显式启用的 `$engineering-change` 使用 `analyze_change.py` 做建议式分析。`analyze_change.py --write-baseline` 可写 Analyzer-only 证据；治理 Intake 则通过 `seal_contract.py` 发布精确合同。Strict Review 使用 `--strict`；机器消费方应读取 `quality_status` 与稳定能力字段 `evidence_complete`。`REVIEW_EVIDENCE_COMPLETE` 表示证据链完整，`REVIEW_REQUIRED_WITH_REDACTIONS` 表示材料脱敏阻止了这一声明。

仓库状态只有在**连续两次有界采集**一致后才会被接受；每个采集生命周期受 `--max-capture-seconds` 约束。任何**材料元数据变化**——包括**新发现的 Ignored 新增**——都会在普通内容采集前启用仅元数据隔离。分类使用 `is_sensitive_material_path`；Rootloom 不是内容感知型 Secret Scanner。

`--reviewable-path` 是 Intake-only 的精确文件声明。它会拒绝 Ignored 文件、Symlink、Hardlink、歧义重复项、强秘密材料，以及标记为 `assume-unchanged` 或 `skip-worktree` 的 Git 条目。Summary 中的 `reviewability_policy` 会记录精确路径与 `policy_provenance`；历史声明不再符合当前策略时，会在读取内容前返回 `reintake-required`。

Evidence 与 Bundle 路径必须同时位于仓库 Worktree 和解析后的 Git Common Directory 之外。可选授权模式为本条命令、普通权限与所有权限：普通权限**跨任务持久**，但每个任务仍需要明确目标与范围；**所有权限绝不会被自动推断**。Archived Assurance Edition 继续保存在 `codex/enterprise-assurance`，但不承诺活跃维护。

</details>

## 可选 Personal Setup

不运行 Setup 也可以使用插件。如果明确需要跨项目工作协议，再调用：

```text
$setup-rootloom
规划并安装可选的 personal preset。
```

| Preset | 增加内容 |
| --- | --- |
| `skills-only` | 不增加全局资产；项目指导 Hook 关闭 |
| `guidance` | 全局工作协议与有界、只读项目 Context |
| `personal` | Guidance 与可选低确认 Autonomy |

托管 Preset 只会涉及 `~/.codex/AGENTS.md`、`~/.codex/rules/rootloom.rules` 和 Rootloom 的小型组件/状态文件，不会修改模型、推理强度、沙箱、审批策略、MCP Server、Provider、插件或 App。Setup 会先显示计划、拒绝冲突、建立备份，并在文档化边界内支持回滚。

## 产品边界

```text
Rootloom Personal Core
├── Core：Change / Review / Guidance
├── Optional Autonomy：授权模式 / Command Rules
├── Optional Evidence：Analyzer / Baseline / Contract / Seal / Finalizer
└── Experimental：Project Memory
```

Rootloom 默认采用单代理。Human Review 状态机、不可篡改 Audit Chain、多代理审计 Runner 与 Recovery Journal 不属于 `main`。不再维护的 1.2.19 实现保留为[Archived Assurance Edition](https://github.com/liyanqing90/rootloom/tree/codex/enterprise-assurance)，但不是活跃产品线。

## Rootloom 与其他工作流的关系

Rootloom 与相邻的 AI Coding 工作流是互补关系：

| 主要需求 | 建议起点 |
| --- | --- |
| 规格驱动的规划与任务拆解 | [GitHub Spec Kit](https://github.com/github/spec-kit) 或 [OpenSpec](https://github.com/Fission-AI/OpenSpec) |
| 广泛、多代理的软件开发方法论 | [Superpowers](https://github.com/obra/superpowers) |
| Codex 专属范围约束、根因审查、项目指导与诚实完成证据 | Rootloom |
| 测试、Lint、安全扫描或 CI | 使用原生工具；Rootloom 记录并分析其证据 |

Rootloom 不会取代需求规格、测试、Lint、Security Scanner、CI 或人工审查。

## 常见问题

### Rootloom 是 OpenAI Codex 插件吗？

是。它提供 Codex Skills、可选全局指导、可选命令 Rules 与一个有界、只读的 SessionStart Hook。运行时辅助工具保持本地、无网络，并仅使用 Python 标准库。

### Rootloom 支持 Claude Code、Cursor 或其他 Coding Agent 吗？

目前不支持。Rootloom 有意针对 Codex 插件与 `AGENTS.md` 模型；工程思想可以移植，但当前发布的集成只面向 Codex。

### Rootloom 是 Spec Kit、OpenSpec 或 Superpowers 的替代品吗？

不是。Spec Kit 与 OpenSpec 专注 Spec-driven Development，Superpowers 提供更广泛的开发方法论。Rootloom 专注执行与审查边界：修改了什么、为什么修改、实际运行了什么，以及完成声明依赖什么证据。

### Rootloom 能证明修改一定正确或安全吗？

不能。它可以机械观察有界仓库状态、命令结果、范围、Provenance 与 Drift；诊断、语义审查、正确性和安全性仍需要可信证据与人工判断。

### 安装 Rootloom 会修改我的全局 Codex 配置吗？

不会。安装只会暴露 Skills。全局指导、Rules 与 Hook 必须通过显式 `$setup-rootloom` 请求和已经审查的计划启用。

### 我可以只使用轻量工作流吗？

可以。Core Change、Review 与 Guidance 是日常路径；Analyzer、Baseline、Contract、Seal、Finalizer、Autonomy 与 Project Memory 仍保持可选或实验性。

## 文档

- [架构](docs/architecture.zh-CN.md)
- [安装、升级与回滚](docs/setup.zh-CN.md)
- [成熟度与保证](docs/maturity.zh-CN.md)
- [指导设计](docs/guidance-design.zh-CN.md)
- [排障](docs/troubleshooting.zh-CN.md)
- [参与贡献](CONTRIBUTING.zh-CN.md)

## 开发

```bash
make validate
make test
make check
make compatibility-smoke
```

## 许可证

[MIT](LICENSE)
