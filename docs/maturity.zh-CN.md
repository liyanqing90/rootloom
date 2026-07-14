# 成熟度、保证与兼容性

Rootloom Personal Core 2.2 是早期、单维护者产品。目标是在不把深度审查成本强加给安装与普通工作的前提下，让 Codex 工程行为更审慎、更可检查；仓库目前还没有受控证据证明它能降低缺陷或审查时间。

`v2.0.0` 发布版已经通过 Linux Python 3.11–3.14、macOS、Windows 与固定 Codex CLI 契约矩阵。这只能证明这些环境中的已检查机制，不代表模型层面的工程质量保证。

## 可执行保证

- 确定性、有界、无网络的项目指导扫描；
- 由托管本地策略控制的 fail-closed Hook；
- 个人 setup 目标的显式 install/upgrade/status/rollback，以及已安装 Hash 漂移拒绝；
- 普通本地锁串行与逐文件原子替换；
- 拒绝漂移的备份恢复；
- 不使用 shell、流式输出上限和残留子进程清理的验证命令；
- 仓库外、带 ownership marker 的 review bundle，以及有界 status、patch、指纹、命令数量与聚合日志；
- 显式按需的修改前敏感/ignored baseline 与严格 Tier 1/2 机器路径/验证契约；
- 普通 untracked 内容指纹和有界文本 patch，以及只含元数据的敏感捕获；
- 敏感删除路径精确确认；
- 综合任务、路径、tracked diff、操作与活跃记忆信号的可解释静态风险下限；
- 与已执行测试证据分离的风险专属验证建议；
- 有界、相关性检索、过期感知的项目记忆上下文、加锁显式更新与统一严格 reader contract；
- 仓库校验、单元测试与离线 Codex 兼容冒烟。

## 仍属于语义判断的部分

Rootloom 无法机械证明：

- 证据完整或真实；
- 根因判断正确；
- Change Contract 包含所有消费者；
- 选择的测试足够；
- 最终审查没有遗漏；
- 静态风险判断包含所有语义影响；
- 建议验证命令安全、充分或已经执行；
- 项目记忆仍然最新或正确。

Skills 负责指导这些判断，当前仓库与运行时证据必须再次验证它们。

## 个人安全边界

个人 Artifact bundle 是可变的本地文件。setup 锁是普通协作锁。setup 逐文件原子，但整个目标集不是一个原子事务。备份/回滚用于普通本地失误，不面向掉电恢复、敌对同用户竞态、签名审批、不可变审计、合规保留或多操作方环境。

这些 Assurance 机制保留在 `codex/enterprise-assurance`，Personal Core 不隐含它们。

## 兼容性

普通 CI 在 Linux 验证 Python 3.11–3.14，并在 macOS/Windows 验证可移植契约。固定版本 Codex 兼容任务先证明 marketplace/插件安装没有全局策略或审查门禁副作用，再独立覆盖可选个人 setup 往返和命令 Rules。live smoke 因需要登录 Codex 与真实模型回合而保持手动。

Personal Core 2.0 有意破坏 1.2.19 的 high-assurance Skill、严格 Runner CLI、自定义代理/profile setup、Human Review 格式、protected-deletion approval 与恢复日志契约。迁移前先使用 1.2.19 回滚。

Personal Core 2.1 保持 `rootloom-project-memory-v1` envelope 与旧条目可读；新增的 ID、证据、状态、路径和过期字段都是附加字段。原有 `rootloom-engineering-summary-v1` 字段继续保留，`risk_assessment` 与 `verification_plan` 为附加内容，旧的 `--risk low|medium|high` 调用仍然有效；但人工风险不能再压低静态检测下限。

Personal Core 2.2 保留 Summary format 名称与旧 CLI 参数，同时把“真实性”与“阻断”分开。只有 `VERIFIED_CHANGE` 才令 `passed` 为 true，新增字段分别表达 `commands_passed`、`capture_preserved`、`verification_coverage` 与 `quality_status`。默认 advisory finalization 不会因缺少治理证据而阻断：命令通过且捕获稳定时可以退出 0，但质量仍为 `UNVERIFIED`。显式 `--strict` 才要求 Tier 1/2 提供修改前 baseline 与 `rootloom-change-contract-v1`，覆盖不足时返回非零。纯验证必须使用 `--allow-no-change`。
