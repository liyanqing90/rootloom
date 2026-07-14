# 架构

Rootloom `main` 是 Personal Core。架构目标是个人每天使用的单代理工程闭环，而不是企业审计与审批。

![Rootloom 个人核心授权与工程架构](diagram/architecture-zh.svg)

## 产品边界

```text
Rootloom Personal Core
├── Task Intelligence
│   ├── 静态任务 / 路径 / diff 信号
│   ├── 相关记忆信号
│   ├── 可解释最低 Tier
│   └── 工作流选择
├── Engineering Workflow
│   ├── Evidence
│   ├── Diagnosis
│   ├── Change Contract
│   ├── Implementation
│   ├── Verification Intelligence
│   └── Final Review Summary
├── Memory
│   ├── 架构不变量
│   ├── 已知风险与失败经验
│   ├── 持久决策索引
│   └── 相关性 / 生命周期过滤
└── Local Runtime
    ├── 可选 SessionStart 播种
    ├── Command Rules
    ├── 简单 setup 备份/回滚
    └── 轻量验证产物
```

拆分前的完整 Assurance 实现在 `codex/enterprise-assurance` 保留。`main` 不包含 Human Review、Decision Pair、protected-deletion approval、自定义代理路由、严格审计 Runner、加固 Artifact 事务或恢复日志。

## 所属路径

| 关注点 | 所属实现 |
| --- | --- |
| 全局任务策略与语义风险规则 | `plugins/rootloom/assets/system/AGENTS.md` |
| 静态风险与验证智能 | `plugins/rootloom/skills/engineering-change/scripts/runner/intelligence.py` |
| 个人端到端修改闭环 | `plugins/rootloom/skills/engineering-change/` |
| Tier 0/1 实施纪律 | `plugins/rootloom/skills/operating-coding-change/` |
| Tier 2 治理式修改 | `plugins/rootloom/skills/operating-high-risk-change/` |
| 仅审查工作流 | `plugins/rootloom/skills/operating-code-review/` |
| 项目/失败记忆 | `plugins/rootloom/skills/project-memory/` |
| 持久决策记录 | `plugins/rootloom/skills/record-engineering-decision/` |
| 确定性项目事实 | `plugins/rootloom/skills/seed-project-guidance/` |
| 语义指导精炼 | `plugins/rootloom/skills/refine-project-guidance/` |
| Codex-home setup | `plugins/rootloom/skills/setup-rootloom/` |
| 生命周期 Hook 门禁 | `plugins/rootloom/hooks/run_component_hook.py` |

## Task Intelligence

风险判断依据影响，而不只是任务大小。`analyze_change.py` 检查任务文本、预期/当前路径、Git 操作、有界 tracked patch、仓库命令和相关活跃项目记忆，输出具体信号、检测/有效风险、最低 Tier、置信度、匹配/过期记忆与验证计划。

路径上下文避免明显误判：单独的 `docs/auth.md` 或 auth 测试仍属于文档/测试范围，`src/auth/token.py` 等产品代码则会提高下限。持久状态、资金、认证/授权、并发、状态机、迁移、公共契约、基础设施、破坏性操作或跨越多个所属边界都会提高 Tier。人工风险声明只能提高、不能降低静态下限。

结果只是建议。语义判断继续由 Skills 和模型负责；消费者或影响未知时可以继续提高 Tier。确定性 Hook 不推断任务风险，扫描器也不授权任何操作。

## Engineering Workflow

`engineering-change` 是显式按需的指导工作流，不是自主多代理状态机或安装时门禁。当前 Codex 代理负责证据、诊断、范围、实现、验证和最终接受。普通 Tier 0/1 工作直接使用仓库证据与成比例测试；安装 Rootloom 永远不会启动 analyzer 或 finalizer。

缺陷的 `ROOT_CAUSE_ALIGNMENT: PASS` 必须包含触发方式、所属边界、被违反的不变量、有证据的根因以及对最强替代假设的否定。功能或机械任务使用 `NOT_APPLICABLE` 并明确目标不变量。

验证对应行为：主路径、所属边界不变量、相邻负向或替代路径。识别到对应风险时，还会要求 auth 边界、迁移共存、资金幂等、状态顺序、部署回滚或消费者兼容等检查。发现的 Make/test 命令只是建议；一个方便命令通过不等于验证完整，生成的计划也不会冒充已执行证据。

## 轻量产物辅助工具

`engineering-change/scripts/finalize_change.py` 不使用 shell 执行操作方给定命令，并写入：

```text
run/
├── diff.patch
├── test.log
└── summary.json
```

只有明确要求严格 Tier 1/2 证据时，`begin_review.py` 才以事务方式创建仓库外 Intake，写入 `rootloom-change-baseline-v2`、可编辑的 `change-contract.draft.json` 与 `rootloom-review-run-v2`。除非显式允许全仓库范围，否则必须至少指定一个 Scope Path；默认要求干净 HEAD/Index，已有修改只能通过 `--allow-dirty-baseline` 显式纳入。发布使用平台的原子不可替换目录原语，因此不会覆盖并发创建的空目标目录。`seal_contract.py` 校验完成后的 Draft，再独占创建规范化 Final Contract 与 `rootloom-contract-seal-v1`。Seal 通过 Baseline Hash、Task Hash、Run ID 与 Nonce 绑定规范化 Contract 内容、最终 Contract 字节和 Review Manifest 字节，无需修改 Manifest。

Baseline v2 使用规范 UUID、Nonce、Hash 与 UTC Timestamp，并绑定 Repository Identity、HEAD、符号 HEAD Ref 与 Index。只有连续两次有界 Snapshot/Patch/Git Identity 采集完全一致，Repository Capture 才会被接受。Strict 会拒绝 Base 漂移，并在验证后重新校验证据字节、Seal、Git Base 与 Output Target。脏 Baseline 会记录既有修改；后续变化存在重叠时按保守范围检查，既有脏路径若消失则视为 Gate Failure，因为它无法表示为当前任务 Patch。Strict JSON Decoder 会拒绝重复 Key、非有限或超范围数值。

敏感发现采用有界路径枚举与共享的大小写不敏感分类器。内置精确名称/后缀与用户声明的目录 Root 都会按路径段边界递归保护后代。敏感的常规文件、目录、Symlink、Tracked/Ignored/Untracked 项及 Rename 两端都不读取内容；Symlink Target 只做 Hash 绑定，不保存原值。在读取普通内容前，Capture 会比较完整发现的敏感元数据集合与 Baseline 或验证前 Reference；因此 Git Status 遗漏的新 Ignored 敏感新增也会触发隔离。任何 Reference Drift 或 Git 可观察的敏感变化都会隔离所有变更端点，并停止 Project Memory/Makefile Discovery。被忽略的敏感新增、修改和删除会合成为 Risk、Scope 与 Summary 共用的 Task Change。元数据包含身份、链接数、大小、权限、修改时间与变更时间，并明确标记为 `metadata-observed`，而非内容完整性。

`rootloom-change-contract-v1` 使用路径段感知的 Repository Glob（`*`/`?` 不跨段，`**` 才跨段），要求根因对齐，并把行为 Claim 映射到显式执行命令。只有来自 Sealed Contract 的结构化 Binding 能完成 Strict Claim Coverage；CLI Claim 只作诊断声明。Summary 保持 `rootloom-engineering-summary-v1`，升级到 `schema_revision: 3`，保留 `risk_assessment`，并分开一般声明与合格 Claim。`semantic_coverage: reviewed` 是操作方断言；语义未知最高只能得到 `MECHANICALLY_VERIFIED`，`VERIFIED_CHANGE` 同时要求 Operator-sealed 机械证据与语义审查。Strict 默认采用 Quality Exit，`--strict-bundle-only` 是显式非阻断形式；Advisory 仍保持按需和 Bundle 导向。

所有命令字符串都会在第一条验证命令执行前完成解析。验证随后运行在受控本地 Process Group 或 Windows Job Object 中，并记录 `process_convergence` 与 `isolation: process-group-only`；无法分配 Job Object 时，Windows 会回退到 Parent/Pipe Observation 与系统进程树终止。这不是执行不可信命令的沙箱，也不保证控制 Detached Service、容器、特权后台管理器、非敏感 Ignored 文件、Git 管理状态或外部状态。命令参数与输出会原样保存在本地 Bundle 中。

Status 与 Git Diff 在保留前即通过字节/路径上限流式捕获。验证输出增量读取；超时、输出超限或残留子进程会终止受控 POSIX Process Group 或 Windows Job Object。证据和输出路径先对词法路径及父目录链执行无 Symlink 检查，再进行 Resolve 后的包含关系判断。Evidence 与 Output 必须同时位于 Repository Worktree 和解析后的 Git Common Directory 之外；Output 还必须不存在、为空或由 Rootloom 标记拥有。这样 Linked Worktree 的证据不会进入 Refs、Objects 或其他 Git 管理区。复用自有输出时，会先失效旧 Summary，避免新运行早退后留下过期权威结果。完整 Patch 默认上限为可配置的 16 MiB。敏感删除要求精确确认。这仍是可变审查包，不是不可篡改审计记录。

Runner 辅助模块保持小型：

- `process.py`：有界子进程；
- `state.py`：有界 Git 状态、untracked 指纹与 patch；
- `baseline.py`：修改前敏感/状态生产者—消费者契约；
- `change_contract.py`：路径范围与验证 claim 门禁；
- `review_run.py`：Review Manifest 与 Contract Seal 的精确 Schema；
- `evidence_paths.py`：证据路径的词法无 Symlink 检查；
- `strict_json.py`：拒绝重复 Key 且只接受有限数值的 Evidence JSON Decoder；
- `verification.py`：命令解析与顺序检查；
- `intelligence.py`：建议式风险、记忆匹配与验证规划；
- `contracts.py`：摘要/结果格式；
- `errors.py`：稳定本地失败。

## Memory

项目指导扫描器把可复现事实写入托管 `AGENTS.md` 区块。`.project-memory/` 保存可选、可审查的架构、风险、决策索引和失败经验。`project_memory.py context` 根据任务/路径做词法相关性选择，限制输出，并把过期/已解决/已替代条目与活跃上下文分开。新记录带确定性 ID、证据引用、生命周期状态与可选过期时间；完全重复会被抑制。记忆只会显式创建/更新，并且永远不能高于当前可执行证据。

持久 envelope 继续使用 `rootloom-project-memory-v1`。没有 ID 或生命周期元数据的旧条目继续可读，`context` 永远不会重写它们。CLI 与 Analyzer 共用同一套严格 no-follow descriptor reader、Schema、条目上限、Legacy ID、相关性、状态与过期契约；某个消费者不会再静默截断另一个消费者判为非法的文件。显式写入会在持有 `.project-memory/memory.lock` 时重新读取、去重并原子替换。

接受后的持久架构与契约决策仍应写入仓库决策记录；memory 中的 decision 文件只是简短索引。

## Setup 与 Hook 边界

Codex 添加插件后安装即完成：Skills 可用，但全局指导、命令 Rules、Hook 策略与 setup 状态仍不存在。只有用户明确要求时，可选 Personal setup 才管理这些复制的全局资产。其 `install` 负责首次 setup；`upgrade` 保持已安装 capability，只有版本变化时不创建多余资产备份，资产变化时先备份，并安全退役已从新版目录移除且未漂移的目标。`status` 与 `upgrade` 都会校验已安装路径、对照已安装 Hash 并拒绝安装后漂移。兼容命令 `apply` 继续保留。setup 先计划、拒绝冲突、使用 create-exclusive 普通锁串行、逐目标原子写入。

复制后的全局指导负责语义授权：普通权限跨任务持久，覆盖每个明确目标的非高危步骤；本条命令与所有权限分别是单动作和当前任务的提升。静态命令规则无法携带这些上下文，因此 `command-safety` 总会包含 `global-policy`；命令规则只负责避免重复弹窗，并保留灾难性递归删除的硬拒绝。详见[分级授权决策](decisions/2026-07-14-tiered-authorization-modes.md)。

该设计不提供跨文件崩溃原子性、敌对同用户保护或恢复日志重放。中断造成的部分 apply 会通过 `status` 暴露，备份内容仍可检查。

唯一生命周期 Hook 是 `SessionStart` 项目指导播种。组件策略缺失、损坏或为符号链接时会关闭执行。扫描器继续保持确定性、有界、仅标准库、无网络、仓库内执行与快照保留。

## 依赖与可移植性

运行时辅助工具只使用 Python 3.11+ 标准库。普通测试覆盖 Linux、macOS 与 Windows 兼容契约。可选 live smoke 需要已经安装并登录的 Codex CLI，只使用可丢弃 `CODEX_HOME`。
