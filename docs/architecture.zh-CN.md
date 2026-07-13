# 架构

Rootloom `main` 是 Personal Core。架构目标是个人每天使用的单代理工程闭环，而不是企业审计与审批。

![Rootloom Personal Core 与 Enterprise Assurance 产品拆分](diagram/architecture.svg)

## 产品边界

```text
Rootloom Personal Core
├── Task Intelligence
│   ├── Tier 判断
│   ├── 风险信号
│   └── 工作流选择
├── Engineering Workflow
│   ├── Evidence
│   ├── Diagnosis
│   ├── Change Contract
│   ├── Implementation
│   ├── Verification Intelligence
│   └── Final Review Summary
├── Memory
│   ├── 项目指导
│   ├── 失败经验
│   └── 持久决策
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
| 全局任务策略与风险信号 | `plugins/rootloom/assets/system/AGENTS.md` |
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

风险判断依据影响，而不只是任务大小。持久状态、资金、认证/授权、并发、状态机、迁移、共享 API、破坏性操作和大量消费者都会提高 Tier。机械修改保持 Tier 0；有边界的行为或缺陷使用 Tier 1；公共/持久契约或影响范围显著不确定时使用 Tier 2。

语义判断留在 Skills 和模型中。确定性 Hook 不推断任务风险。

## Engineering Workflow

`engineering-change` 是指导工作流，不是自主多代理状态机。当前 Codex 代理负责证据、诊断、范围、实现、验证和最终接受。

缺陷的 `ROOT_CAUSE_ALIGNMENT: PASS` 必须包含触发方式、所属边界、被违反的不变量、有证据的根因以及对最强替代假设的否定。功能或机械任务使用 `NOT_APPLICABLE` 并明确目标不变量。

验证对应行为：主路径、所属边界不变量、相邻负向或替代路径。一个方便命令通过不等于验证完整。

## 轻量产物辅助工具

`engineering-change/scripts/finalize_change.py` 不使用 shell 执行操作方给定命令，并写入：

```text
run/
├── diff.patch
├── test.log
└── summary.json
```

它捕获 tracked Git 修改，只列出 untracked 路径而不读取内容；尚无首个提交的仓库使用 Git empty tree 作为 tracked 基线；输出有界。验证命令必须保持 tracked patch 与已捕获的 changed/untracked 路径集合不变，否则 bundle 会标记为失败并重新检查危险删除。敏感删除要求精确确认。这是审查包，不是不可篡改审计记录。

Runner 辅助模块保持小型：

- `process.py`：有界子进程；
- `state.py`：修改路径与 tracked patch；
- `verification.py`：命令解析与顺序检查；
- `contracts.py`：摘要/结果格式；
- `errors.py`：稳定本地失败。

## Memory

项目指导扫描器把可复现事实写入托管 `AGENTS.md` 区块。`.project-memory/` 保存可选、可审查的架构、风险、决策索引和失败经验。记忆只会显式创建/更新，并且永远不能高于当前可执行证据。

接受后的持久架构与契约决策仍应写入仓库决策记录；memory 中的 decision 文件只是简短索引。

## Setup 与 Hook 边界

个人 setup 管理全局指导、命令 Rules、Hook 策略、状态与备份。它先计划、拒绝冲突、使用 create-exclusive 普通锁串行、逐目标原子写入。回滚写入前会检查当前哈希与备份哈希，并拒绝覆盖安装后的修改。

该设计不提供跨文件崩溃原子性、敌对同用户保护或恢复日志重放。中断造成的部分 apply 会通过 `status` 暴露，备份内容仍可检查。

唯一生命周期 Hook 是 `SessionStart` 项目指导播种。组件策略缺失、损坏或为符号链接时会关闭执行。扫描器继续保持确定性、有界、仅标准库、无网络、仓库内执行与快照保留。

## 依赖与可移植性

运行时辅助工具只使用 Python 3.11+ 标准库。普通测试覆盖 Linux、macOS 与 Windows 兼容契约。可选 live smoke 需要已经安装并登录的 Codex CLI，只使用可丢弃 `CODEX_HOME`。
