# 成熟度、保证与兼容性

Rootloom Personal Core 2.0 是早期、单维护者产品。目标是让 Codex 工程行为更审慎、更可检查；仓库目前还没有受控证据证明它能降低缺陷或审查时间。

`v2.0.0` 发布版已经通过 Linux Python 3.11–3.14、macOS、Windows 与固定 Codex CLI 契约矩阵。这只能证明这些环境中的已检查机制，不代表模型层面的工程质量保证。

## 可执行保证

- 确定性、有界、无网络的项目指导扫描；
- 由托管本地策略控制的 fail-closed Hook；
- 个人 setup 目标的 plan/apply/status/rollback；
- 普通本地锁串行与逐文件原子替换；
- 拒绝漂移的备份恢复；
- 不使用 shell、有界输出的验证命令；
- 敏感删除路径精确确认；
- 经过 Schema 检查的项目记忆集合；
- 仓库校验、单元测试与离线 Codex 兼容冒烟。

## 仍属于语义判断的部分

Rootloom 无法机械证明：

- 证据完整或真实；
- 根因判断正确；
- Change Contract 包含所有消费者；
- 选择的测试足够；
- 最终审查没有遗漏；
- 项目记忆仍然最新。

Skills 负责指导这些判断，当前仓库与运行时证据必须再次验证它们。

## 个人安全边界

个人 Artifact bundle 是可变的本地文件。setup 锁是普通协作锁。setup 逐文件原子，但整个目标集不是一个原子事务。备份/回滚用于普通本地失误，不面向掉电恢复、敌对同用户竞态、签名审批、不可变审计、合规保留或多操作方环境。

这些 Assurance 机制保留在 `codex/enterprise-assurance`，Personal Core 不隐含它们。

## 兼容性

普通 CI 在 Linux 验证 Python 3.11–3.14，并在 macOS/Windows 验证可移植契约。固定版本 Codex 兼容任务覆盖 marketplace 安装、插件发现、个人 setup 往返和命令 Rules。live smoke 因需要登录 Codex 与真实模型回合而保持手动。

Personal Core 2.0 有意破坏 1.2.19 的 high-assurance Skill、严格 Runner CLI、自定义代理/profile setup、Human Review 格式、protected-deletion approval 与恢复日志契约。迁移前先使用 1.2.19 回滚。
