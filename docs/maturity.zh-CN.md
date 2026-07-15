# 成熟度、保证与兼容性

Rootloom Personal Core 是早期、单维护者产品。目标是在不把深度审查成本强加给安装与普通工作的前提下，让 Codex 工程行为更审慎、更可检查；仓库目前还没有受控证据证明它能降低缺陷或审查时间。

`v2.0.0` 发布版已经通过 Linux Python 3.11–3.14、macOS、Windows 与固定 Codex CLI 契约矩阵。这只能证明这些环境中的已检查机制，不代表模型层面的工程质量保证。

## 可执行保证

- 确定性、有界、无网络的项目指导扫描；
- 由托管本地策略控制的 fail-closed Hook；
- 个人 setup 目标的显式 install/upgrade/status/rollback，以及已安装 Hash 漂移拒绝；
- 普通本地锁串行与逐文件原子替换；
- 拒绝漂移的备份恢复；
- 所有命令先完成解析，再以不使用 Shell 的方式执行；验证与 Git Capture 共享流式输出/时间上限及残留子进程清理；
- 仓库外、带 ownership marker 的 review bundle，以及有界 status、patch、指纹、命令数量与聚合日志；
- 显式按需、原子且不可替换发布的修改前 Baseline，以及 Draft → Seal 的严格 Tier 1/2 Contract；
- 两次一致的稳定 Repository Capture、Strict Evidence JSON、路径段感知 Scope Glob 与 HEAD/Ref/Index 不变绑定；
- 普通 Untracked 内容指纹、按任务分区的可应用有界文本 Patch 与风险信号，以及具有独立定向候选/分类结果上限、递归的 Metadata-observed 敏感捕获与敏感变化隔离；
- 证据诚实的 Revision 4 审查状态：操作方语义断言独立表达，发生遮蔽的审查不通过；
- 敏感删除路径精确确认；
- 综合任务、路径、Tracked/非敏感 Untracked Diff、操作与活跃记忆信号的可解释静态风险下限；
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

个人 Artifact Bundle 是可变的本地文件。验证命令属于可信的操作方输入，不是沙箱工作负载；命令参数与输出会原样保留，因此不能携带 Credential。Capture 不覆盖非敏感 Ignored 文件、Git 管理文件、外部状态、Detached Manager，也无法识别敏感源没有可观察变化时复制到普通路径的 Secret。Setup 锁是普通协作锁。Setup 逐文件原子，但整个目标集不是一个原子事务。备份/回滚用于普通本地失误，不面向掉电恢复、敌对同用户竞态、签名审批、不可变审计、合规保留或多操作方环境。

这些 Assurance 机制保留在 `codex/enterprise-assurance`，Personal Core 不隐含它们。

## 兼容性

普通 CI 在 Linux 验证 Python 3.11–3.14，并在 macOS/Windows 验证可移植契约。固定版本 Codex 兼容任务先证明 marketplace/插件安装没有全局策略或审查门禁副作用，再独立覆盖可选个人 setup 往返和命令 Rules。live smoke 因需要登录 Codex 与真实模型回合而保持手动。

Personal Core 2.0 有意破坏 1.2.19 的 high-assurance Skill、严格 Runner CLI、自定义代理/profile setup、Human Review 格式、protected-deletion approval 与恢复日志契约。迁移前先使用 1.2.19 回滚。

Personal Core 2.1 保持 `rootloom-project-memory-v1` envelope 与旧条目可读；新增的 ID、证据、状态、路径和过期字段都是附加字段。原有 `rootloom-engineering-summary-v1` 字段继续保留，`risk_assessment` 与 `verification_plan` 为附加内容，旧的 `--risk low|medium|high` 调用仍然有效；但人工风险不能再压低静态检测下限。

Personal Core 2.2 保留 Summary Format 名称，并在 Revision 3 收紧显式治理证据。Advisory Finalization 默认仍不阻断。Strict 采用 Draft → Seal 生命周期、两次一致的稳定 Capture、Strict JSON、验证后 Evidence/Base 复检、Reference-aware 敏感变化隔离、Worktree 与 Git Common Directory 双边界包含检查、HEAD/Ref/Index 不变绑定及来自 Sealed Contract 的结构化 Claim，并默认使用 Quality Exit；`--strict-bundle-only` 保留显式非阻断 Strict Bundle。`semantic_coverage: reviewed` 是操作方断言，不是机器证明；语义未知最高只能得到 `MECHANICALLY_VERIFIED`，只有封存完整的机械证据加上该断言才能得到 `VERIFIED_CHANGE` 与 `passed: true`。纯验证必须使用 `--allow-no-change`，但非法证据和进程/Capture 错误优先于 `NO_CHANGE`。

Summary Revision 4 有意把最高状态的精确值从 `VERIFIED_CHANGE` 改为 `REVIEW_EVIDENCE_COMPLETE`，并独立暴露 `semantic_review: operator-asserted`。没有封存链的断言是 `SEMANTIC_REVIEW_ASSERTED`；发生敏感隔离时，原本完整的结果最高只能是 `REVIEW_REQUIRED_WITH_REDACTIONS` 与 `passed: false`。Strict Quality Exit 只有 `REVIEW_EVIDENCE_COMPLETE` 返回 0；Advisory Bundle Exit 继续保持非阻断。依赖 Revision 3 精确值的消费者必须按 `schema_revision` 分支。Git 现在与验证共用受控进程树所有者、关闭标准输入并使用显式时间预算；敏感发现使用共享定向 Pathspec 与独立的候选/分类结果上限；脏 Baseline 的风险与 Patch 输出复用同一任务分区；精确的 `seal_contract --recover` 只补全匹配的中断发布。
