# 架构

Rootloom `main` 是 Personal Core。架构目标是个人每天使用的单代理工程闭环，而不是企业审计与审批。

![Rootloom Personal Core 与 Enterprise Assurance 产品拆分](diagram/architecture.svg)

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

`engineering-change` 是指导工作流，不是自主多代理状态机。当前 Codex 代理负责证据、诊断、范围、实现、验证和最终接受。

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

它捕获 tracked Git 修改，只列出 untracked 路径而不读取内容；尚无首个提交的仓库使用 Git empty tree 作为 tracked 基线；输出必须位于被捕获仓库之外。patch 默认超过可配置的 16 MiB 上限即拒绝；命令数量、命令/风险文本和聚合验证日志都有界。工具自动计算风险，保留可选但只能更高的人工声明，并在现有 v1 摘要字段上增加 `risk_assessment` 与 `verification_plan`。验证命令必须保持 tracked patch 与已捕获的 changed/untracked 路径集合不变，否则 bundle 会标记为失败并重新检查危险删除。敏感删除要求精确确认。这是审查包，不是不可篡改审计记录。

Runner 辅助模块保持小型：

- `process.py`：有界子进程；
- `state.py`：修改路径与 tracked patch；
- `verification.py`：命令解析与顺序检查；
- `intelligence.py`：建议式风险、记忆匹配与验证规划；
- `contracts.py`：摘要/结果格式；
- `errors.py`：稳定本地失败。

## Memory

项目指导扫描器把可复现事实写入托管 `AGENTS.md` 区块。`.project-memory/` 保存可选、可审查的架构、风险、决策索引和失败经验。`project_memory.py context` 根据任务/路径做词法相关性选择，限制输出，并把过期/已解决/已替代条目与活跃上下文分开。新记录带确定性 ID、证据引用、生命周期状态与可选过期时间；完全重复会被抑制。记忆只会显式创建/更新，并且永远不能高于当前可执行证据。

持久 envelope 继续使用 `rootloom-project-memory-v1`。没有 ID 或生命周期元数据的旧条目继续可读，`context` 永远不会重写它们。集合、架构上下文、路径和符号链接边界都有约束，使它保持为小型仓库文件系统，而不是数据库或索引服务。

接受后的持久架构与契约决策仍应写入仓库决策记录；memory 中的 decision 文件只是简短索引。

## Setup 与 Hook 边界

个人 setup 管理全局指导、命令 Rules、Hook 策略、状态与备份。它先计划、拒绝冲突、使用 create-exclusive 普通锁串行、逐目标原子写入。回滚写入前会检查当前哈希与备份哈希，并拒绝覆盖安装后的修改。

该设计不提供跨文件崩溃原子性、敌对同用户保护或恢复日志重放。中断造成的部分 apply 会通过 `status` 暴露，备份内容仍可检查。

唯一生命周期 Hook 是 `SessionStart` 项目指导播种。组件策略缺失、损坏或为符号链接时会关闭执行。扫描器继续保持确定性、有界、仅标准库、无网络、仓库内执行与快照保留。

## 依赖与可移植性

运行时辅助工具只使用 Python 3.11+ 标准库。普通测试覆盖 Linux、macOS 与 Windows 兼容契约。可选 live smoke 需要已经安装并登录的 Codex CLI，只使用可丢弃 `CODEX_HOME`。
