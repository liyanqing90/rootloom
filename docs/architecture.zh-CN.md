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
    ├── operating-coding-change/
    ├── operating-code-review/
    ├── operating-high-risk-change/
    └── high-assurance-coding-change/
```

## 安装流

安装插件不会静默接管全局策略。显式 setup Skill 执行确定性事务：

```text
计划 → 冲突门禁 → 备份 → 原子写入 → 哈希清单 → 状态检查
                                      ↓
                       哈希校验 + 配置语义回滚
```

事务只管理所选能力映射出的资产，再加一份分别控制两个生命周期 Hook 的私有组件策略。`full` 事务包含完整全局 `AGENTS.md`、一个 profile、四个自定义 Agent 文件、一份 Rules，以及用户现有 `[agents]` 表中的三个限制键；其余 config 键全部保留。存在任一无托管冲突时，整个 apply 都会停止，除非用户明确授权替换。

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

扫描器仅依赖 Python 标准库，本地、确定、受限、零网络，并且从不执行仓库代码。它只拥有标记区间；遇到无标记指导、override、符号链接、不可信仓库、临时/vendor/cache 目录或退出项目时会跳过。

语义打磨由独立 Skill 负责，避免模型每次会话重写托管区块。嵌套指导只在真实模块边界按需创建。

## 工作流路由

全局工作协议按风险和请求类型路由：

- 普通非平凡实施 → `$operating-coding-change`；
- 只读审查 → `$operating-code-review`；
- 公开/持久化契约、安全、迁移、基础设施、部署或发布 → `$operating-high-risk-change`；
- 用户明确要求的受控多代理修改 → `$high-assurance-coding-change`。

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
2. 全局指导、Skills 与 `SubagentStart` Hook 维持每个父会话累计四个子代理的行为预算。
3. 高保障 Runner 用代码固定阶段图、唯一写代理、允许路径、结构化输出、修复轮数和验证顺序。

Hook 无法取消刚启动的子代理，只能向 UI 告警并注入开发者上下文。因此即使 `max_threads = 4`，截图仍可能出现十个已完成代理：这个上限控制并发，不控制累计数量。

## 确定性高保障路径

原生多代理很适合交互式工作，但编排仍由模型决定。内置 Runner 使用连续的 `codex exec` 阶段，并读取同一组自定义 Agent TOML。它强制：

- 仓库锁和私有产物目录；
- 干净基线与 Git 状态快照；
- 证据、诊断和评审阶段不可修改仓库；
- 唯一写代理且 Git index 不变；
- 精确允许路径与写代理报告一致；
- 不经 shell 的确定性验证命令；
- GO、完成、PASS 和 findings 的结构化语义门禁；
- 最多一次定向修复循环；
- 超时或中断时终止完整进程组。

生产关键工作仍需外部 OS/container、凭据、网络、分支保护和 CI 策略。

## 为什么核心不带 MCP

核心只需要本地 Git/文件证据和 Codex 原生配置。增加 MCP 会多出进程、协议、信任决策和故障点，却没有新增必需能力。

当某个角色确实需要外部系统——例如权威内部文档、Issue、可观测性或部署控制——MCP 才是正确扩展点。应把它只配置给那个窄角色并设置工具审批，而不是让所有编码任务继承。

## 威胁模型

插件把仓库内容、现有配置和子代理路由都视为不可信输入。防护包括受限解析、播种阶段不执行仓库命令、疑似密钥检测、符号链接和路径拒绝、用户文件冲突拒绝、原子写入、限制性权限、备份、apply 后哈希、一次性 Hook 信任审查、最小权限角色、Rules 和确定性测试。

这些控制不能替代平台策略、sandbox、操作系统权限、管理员托管配置、分支保护、代码审查或 CI。
