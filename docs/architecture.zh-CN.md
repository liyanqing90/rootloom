# 架构

Rootloom 是分层插件，不是一份巨型提示词。每种 Codex 机制只负责它能可靠表达的控制，真正可执行的门禁仍然放在模型文案之外。

![Rootloom 架构](diagram/architecture.svg)

## 设计目标

- 让每个可信仓库从简洁、有证据的项目上下文开始。
- 交付打磨后的全局和项目 `AGENTS.md` 成品，而不只是生成器。
- 稳定路由普通实施、只读审查、高风险和受控多代理工作。
- 强模型负责判断，较便宜的模型只承担受限的只读证据收集。
- 严格区分本地可逆 Git 历史、远程发布和破坏性操作。
- 通过先计划、备份、哈希和回滚保护用户自有配置。
- 明确区分行为指导和硬性执行边界。

## 分层模型

| 层级 | 所有权 | 执行强度 |
| --- | --- | --- |
| 全局 `AGENTS.md` | 稳定的权限、自主权、工程、证据、路由、委派和沟通策略 | 模型可见的工作协议 |
| 项目 `AGENTS.md` | 已验证的仓库事实、命令、地图和持久局部不变量 | 分层项目指导 |
| 决策记录 | 已接受的架构、契约、依赖、安全、数据与运维决策 | 仓库内持久记忆；属于文档，不是执行门禁 |
| Skills | 安装、播种、打磨、编码、审查、高风险和受控多代理的可复用流程 | 渐进加载的工作流 |
| 自定义 Agents | 角色、模型、推理等级、sandbox 默认值、Apps 和开发者指令 | 子会话配置 |
| Config/profile | 并发线程、嵌套深度和高保障 CLI 默认运行模式 | 原生运行配置 |
| Rules | sandbox 外命令的 allow、prompt、forbidden 前缀策略 | 原生命令策略；最严格匹配优先 |
| Hooks | 确定性生命周期动作和审计提醒 | 脚本化护栏；受事件 API 能力限制 |
| Runner、测试、CI | 阶段顺序、diff 范围、命令结果和发布门禁 | 确定性可执行证据 |

## 能力层级

机制层解释“谁负责什么”，能力层解释用户实际安装什么：

```text
skills-only
    └─ guidance       = global-policy + project-context
         └─ engineering = guidance + command-safety
              └─ delegated = engineering + delegation-control
                   └─ full = delegated + high-assurance
```

`engineering` 是推荐的单 Agent 默认层。`delegation-control` 可选且不可拆：四个自定义角色、config 限制与子代理审计 Hook 必须一起安装；`high-assurance` 依赖它。`list-components` 仍展示底层产物映射供审计，但正式用户选择是完整能力，而不是任意残缺文件组合。

## 插件内容

仓库、marketplace 与插件统一使用公开 ID：`rootloom`。

```text
plugin
├── assets/system/
│   ├── AGENTS.md
│   ├── agents/*.toml
│   ├── profiles/high-assurance.config.toml
│   └── rules/rootloom.rules
├── hooks/
│   ├── hooks.json
│   ├── run_component_hook.py
│   └── subagent_budget.py
└── skills/
    ├── setup-rootloom/
    ├── seed-project-guidance/
    ├── refine-project-guidance/
    ├── record-engineering-decision/
    ├── operating-coding-change/
    ├── operating-code-review/
    ├── operating-high-risk-change/
    └── high-assurance-coding-change/
```

## 安装流

安装插件不会静默接管全局策略。显式 setup Skill 执行确定性事务：

```text
进程锁 → 计划 → 冲突门禁 → 预备备份与恢复清单
                                      ↓
                    原子写入 + 状态提交 → 状态检查
                                      ↓ 失败
                    完整补偿 + 恢复权限模式
```

事务只管理所选能力映射出的资产，再加一份分别控制两个生命周期 Hook 的私有组件策略。非阻塞跨进程锁会串行化同一 Codex home 的 setup 与 rollback；第一处目标修改前，备份与恢复清单已持久化。状态提交属于同一补偿边界，回滚会恢复记录的文件权限模式。`full` 事务包含完整全局 `AGENTS.md`、一个 profile、四个自定义 Agent 文件、一份 Rules，以及用户现有 `[agents]` 表中的三个限制键；其余 config 键全部保留。存在任一无托管冲突时，整个 apply 都会停止，除非用户明确授权替换。

策略缺失时两个 Hook 都关闭；显式托管策略会分别控制它们，策略损坏或被符号链接替换时同样会关闭并告警。因此在 setup 应用所选能力层之前，插件不会产生自动生命周期行为。

改变能力层级必须先执行 `rollback --all`，再重新 plan/apply。事务链回滚会恢复安装前基线，不会猜测新层级未包含的资产应该删除还是保留。

## 项目指导流

选择 `project-context` 后，自动路径刻意保持更窄：

```text
SessionStart
    ↓
受限仓库证据
    ↓
信任 / 路径 / 所有权 / 密钥 / 大小门禁
    ↓
原子生成 AGENTS.md 托管事实
    ↓
只有语义不变量确有价值时才运行 $refine-project-guidance
```

扫描器仅依赖 Python 标准库，本地、确定、受限、零网络，并且从不执行仓库代码，也不会跟随符号链接读取仓库外证据。Git 公共目录中的锁会串行化各 worktree 写入；扫描器在锁内重新探测，并在落盘前比较指导文件的精确快照，若其他工具已修改则安全跳过。它只拥有标记区间；遇到无标记指导、override、符号链接、不可信仓库、临时/vendor/cache 目录或退出项目时会跳过。

语义打磨由独立 Skill 负责，避免模型每次会话重写托管区块。嵌套指导只在真实模块边界按需创建。

## 工作流路由

全局工作协议先补全最小可用的 `Intent + Context + Tools + Constraints + Verification` 契约，再使用一套统一分级路由：

- Tier 0 Direct 机械工作 → 通过 `$operating-coding-change` 直接执行，只读取最小上下文并提供最小证据；
- Tier 1 Scoped 的普通 Bug、功能、重构和边界明确的多文件工作 → `$operating-coding-change`，内部使用任务包和分级根因门禁；
- Tier 2 Governed 的公开/持久化契约、安全、迁移、基础设施、部署、发布或根因存在实质不确定性的工作 → `$operating-high-risk-change`，展示治理任务包并维护 ExecPlan；
- 只读审查 → `$operating-code-review`；
- 用户明确要求的受控多代理修改 → `$high-assurance-coding-change`。

行为修复默认至少是 Tier 1，除非可证明为机械修正。普通诊断必须让修改位置与所有者边界中被破坏的不变量一致；治理诊断再增加竞争假设与 GO/NO_GO 门禁。代码审查输出 `ROOT_CAUSE_ALIGNMENT: PASS | FAIL | NOT_APPLICABLE`；透明标注的 `MITIGATION` 不能满足“完整修复”声明。

关键运行时或外部证据携带精简来源记录：稳定 ID、来源、环境、观察时间或时间窗、稳定引用、新鲜度/脱敏，以及事实/推断状态。严格 Runner 中每条观察事实和复现记录都必须引用这些 ID。行为验证从被破坏的不变量推导，覆盖原始失败路径、所有者边界不变量和相邻负向或替代路径。

已接受的持久决策路由到 `$record-engineering-decision`。记录在仓库内保存上下文、备选方案、证据、后果和重新评估条件；`AGENTS.md` 可以指向它，但不应复制全文。

系统不再需要另一个常驻 Gatekeeper Skill。稳定分级属于全局策略，详细行为属于渐进加载的工程 Skills，确定性证据属于测试、验证器、CI 和可选高保障 Runner。Hooks 不负责判断语义根因。

高保障角色如下：

| 角色 | 模型 | 推理 | 默认权限 |
| --- | --- | --- | --- |
| 证据调查 | `gpt-5.6-terra` | medium | read-only |
| 根因评审 | `gpt-5.6-sol` | xhigh | read-only |
| 实施代理 | `gpt-5.6-sol` | high | workspace-write |
| 验证评审 | `gpt-5.6-sol` | xhigh | read-only |

只有一个角色可写。父任务的实时权限覆盖仍可能重新施加到子代理，因此原生角色隔离不能当成硬 sandbox 边界。

## 可选子代理控制有三层

以下控制只存在于 `delegation-control` 能力中：

1. `agents.max_threads = 4` 硬限制同时打开的线程。
2. 全局指导、Skills 与 `SubagentStart` Hook 维持每个父会话累计四个子代理的建议式行为预算。第五个子代理已经启动；Hook 只能要求它停止，不能强制执行。
3. 高保障 Runner 用代码固定阶段图、唯一写代理、允许路径、结构化输出、修复轮数和验证顺序。

Hook 无法取消刚启动的子代理，只能向 UI 告警并注入开发者上下文。因此即使 `max_threads = 4`，截图仍可能出现十个已完成代理：这个上限控制并发，不控制累计数量。

## 确定性高保障路径

原生多代理很适合交互式工作，但编排仍由模型决定。内置 Runner 使用连续的 `codex exec` 阶段，并读取同一组自定义 Agent TOML。它强制：

- 仓库锁和私有产物目录；
- 干净基线与 Git 状态快照；
- 对已跟踪文件和普通可见未跟踪交付物做完整内容指纹；
- 在内容指纹前完成分类：所有 ignored 路径以及已知或调用者配置的敏感可见未跟踪路径只记录不含内容哈希的元数据，其内容不进入产物或 Reviewer 提示；
- Writer 对上述 metadata-only 路径的任何变化默认在 Delta 捕获前被拒绝；唯一例外是提前精确授权的删除，而且最终必须以非零人工验收状态停止；
- 显式、关闭式失败的 ignored 路径枚举预算；
- 证据、诊断和评审阶段不可修改仓库；
- 唯一写代理且 Git index 不变；
- 在内容型 Delta 捕获前检查精确允许路径，并与写代理报告一致；
- 不经 shell 的确定性验证命令、稳定命令 ID、每项诊断验证要求对应的成功命令记录、至少一条超出格式检查 `verify-0` 的用户命令映射、按命令关联且真实存在的操作方 harness 路径，以及对直接执行的仓库脚本、`make` 文件、JavaScript package manifest、pytest 配置文件、缺失常见候选、仓库内每个 symlink 路径组件和最终目标进行逐命令指纹稳定性检查；
- GO、完成、PASS 和 findings 的结构化语义门禁；
- 在启动、每次 Writer 后、确定性验证后和最终 Review 后检查 topology，不在每个只读阶段重复完整遍历；
- 最多一次定向修复循环；
- 在超时、中断，或父进程成功/失败退出但仍遗留子进程时终止完整进程组。

这里是流程确定性，不是结果确定性。JSON Schema 约束输出形状，本地语义门禁约束部分一致性；二者都不能证明证据真实、根因正确、所选验证命令充分或修改在生产环境安全。内置敏感名称识别是有限清单，仓库专有缺口应使用精确/递归自定义规则或可选 dotfile 脱敏。验证入口指纹消费仓库的 ignored/敏感分类，并在内容访问前拒绝 protected harness。它覆盖直接入口、常见入口和按命令绑定的操作方稳定性依赖，但不是能识别隐藏 CLI 路径的通用解析器，也不能证明命令在语义上真实使用了绑定依赖。pytest 位置参数会被视为选择范围，而不是可执行入口。每条验证命令前后都会检查入口和仓库状态，因此一条命令产生变更后，批次会在下一条命令运行前停止。产物脱敏不是文件访问隔离，因为每个模型阶段仍获得可读取仓库的 sandbox。已授权 protected 删除只能证明路径已移除，不能证明旧内容，因此不能自动验收；Rootloom 会把这类任务保持为 deletion-only，防止 protected 内容在同一次任务中通过 rename 或 move 混入普通 Delta。严格 Runner 支持 Linux、macOS 和 WSL；由于仓库锁与进程组终止依赖 POSIX 语义，原生 Windows 会被明确拒绝。

生产关键工作仍需外部 OS/container、凭据、网络、分支保护和 CI 策略。

## 为什么核心不带 MCP

核心只需要本地 Git/文件证据和 Codex 原生配置。增加 MCP 会多出进程、协议、信任决策和故障点，却没有新增必需能力。

当某个角色确实需要外部系统——例如权威内部文档、Issue、可观测性或部署控制——MCP 才是正确扩展点。应把它只配置给那个窄角色并设置工具审批，而不是让所有编码任务继承。

严格 Runner 会关闭外部工具与网络，因此应在运行前收集已授权运行时证据，只传入受限且脱敏的材料。Rootloom 统一的是来源契约，不是供应商专用的采集机制。

## 成熟度与兼容边界

Rootloom 目前处于早期阶段，且只有一名维护者。普通 CI 中固定的 Codex CLI 契约是受支持、可复现的基线；另一条非阻塞定时任务负责探测最新版本的上游漂移。两者都会演练离线 marketplace 安装、插件发现、完整 setup/status/验证、profile 解析、Rules 决策、回滚和既有配置保留。适用场景、学习成本、平台耦合和治理边界见[成熟度、保证边界与兼容性](maturity.zh-CN.md)。

## 威胁模型

插件把仓库内容、现有配置和子代理路由都视为不可信输入。防护包括受限解析、播种阶段不执行仓库命令、疑似密钥检测、符号链接和路径拒绝、用户文件冲突拒绝、原子写入、限制性权限、备份、apply 后哈希、一次性 Hook 信任审查、最小权限角色、Rules 和确定性测试。

这些控制不能替代平台策略、sandbox、操作系统权限、管理员托管配置、分支保护、代码审查或 CI。
