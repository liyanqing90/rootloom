<p align="center">
  <img src="plugins/rootloom/assets/icon.svg" width="112" alt="Rootloom 标志">
</p>

<h1 align="center">Rootloom</h1>

<p align="center">
  <strong>从根部织起可靠的 Codex 工程。</strong>
</p>

<p align="center">
  <strong>简体中文</strong> · <a href="README.md">English</a>
</p>

<p align="center">
  <a href="https://github.com/liyanqing90/rootloom/actions/workflows/ci.yml"><img src="https://github.com/liyanqing90/rootloom/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/liyanqing90/rootloom?color=6D5EF7" alt="MIT 许可证"></a>
  <a href="https://github.com/liyanqing90/rootloom/releases"><img src="https://img.shields.io/github/v/release/liyanqing90/rootloom?display_name=tag&sort=semver" alt="最新版本"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-39B98F" alt="Python 3.11+">
</p>

![Rootloom 品牌图：证据根系穿过能力织架并抵达验证交付](assets/rootloom-brand.webp)

Rootloom 让用户只安装真正需要的 Codex 能力，不会被迫同时接受子代理、Hooks 或一份巨型提示词：

| 能力 | 实际交付物 |
| --- | --- |
| 全局策略 | 打磨完成、可直接安装的全局 [`AGENTS.md`](plugins/rootloom/assets/system/AGENTS.md) |
| 项目上下文 | 自动生成有证据的根指导，并按需生成嵌套指导 |
| 指导质量 | `$refine-project-guidance` 只补充持久语义不变量，不制造文件级文档噪音 |
| 工程工作流 | 普通修改、只读审查、高风险和显式高保障 Skills |
| 模型路由 | 四个明确模型、推理等级、角色和 sandbox 默认值的 Agent TOML |
| 运行与命令 | 质量优先 profile、四线程并发上限和经过测试的命令 Rules |
| 确定性交付 | 唯一写代理、范围门禁、真实验证和独立评审的 `codex exec` Runner |

仓库、marketplace 与插件统一使用稳定公开 ID：`rootloom`。

## 为什么叫 Rootloom

**Root** 是仓库事实：源码、Schema、测试、项目指导与根因证据。**Loom** 是织架：把 Skills、Hooks、Rules、Agents 和验证编织成完整能力层。播种上下文只是第一根线，而不是整个产品。

![Rootloom 能力图：五个可选层级](assets/hero.svg)

## 为什么是系统，而不是更长的提示词

OpenAI 当前 [GPT-5.6 指南](https://developers.openai.com/api/docs/guides/latest-model)建议精简提示词、规则只写一次，并清楚定义自主权、审批边界、约束和成功标准。Codex 已经为不同问题提供了更合适的位置：

- [`AGENTS.md`](https://developers.openai.com/codex/agent-configuration/agents-md)：稳定的全局和局部指导；
- [Skills](https://developers.openai.com/codex/build-skills)：渐进加载的可复用流程；
- [自定义 Agents](https://developers.openai.com/codex/agent-configuration/subagents)：角色、模型、推理、sandbox、MCP 和 Apps；
- [Rules](https://developers.openai.com/codex/agent-configuration/rules)：命令策略；
- [Hooks](https://developers.openai.com/codex/hooks)：确定性生命周期动作和审计；
- profiles、脚本、测试和 CI：运行默认值与可执行证据。

把一切都塞进 `AGENTS.md` 只会浪费上下文，并把建议伪装成强制执行。本项目让每一层保持狭窄，并明确它真正能保证什么。

## 安装

要求：

- 支持插件和生命周期 Hook 的 Codex CLI 或 Codex 桌面端；
- Git；
- Python 3.11 或更高版本。

添加 GitHub marketplace 并安装稳定包 ID：

```bash
codex plugin marketplace add liyanqing90/rootloom
codex plugin add rootloom@rootloom
```

新建 Codex 任务，先选择能力层级，再决定是否信任可选 Hooks：

| 预设 | 启用能力 | 子代理 |
| --- | --- | --- |
| `skills-only` | 只有内置 Skills；不写用户策略/运行资产；关闭生命周期 Hooks | 无 |
| `guidance` | 全局策略 + 自动项目上下文 | 无 |
| `engineering` | 指导层 + 命令安全；普通开发推荐 | 无 |
| `delegated` | 工程层 + 原子化四角色委派控制 | 有 |
| `full` | 委派层 + 配置完成的高保障 profile | 有 |

然后让 Codex 规划并应用所选层级，无需手动编辑：

```text
$setup-rootloom
先展示能力层级，再规划并应用 engineering 预设。
```

需要本仓库的整套系统时选择 `full`。高级用户可以组合稳定维度：`global-policy`、`project-context`、`command-safety`、`delegation-control` 和 `high-assurance`；依赖会自动补齐。

Setup 完成后打开 `/hooks` 审查两条命令；若所选层级启用了任一 Hook，再信任当前定义：

- `SessionStart`：仅在选择 `project-context` 时安全播种本地项目指导。
- `SubagentStart`：仅在选择 `delegation-control` 时审计累计子代理预算和命名角色/模型路由。

setup Skill 会先规划、备份替换、原子写入、记录哈希并支持回滚；没有明确授权时，它拒绝覆盖用户自有冲突文件。

完整契约见[安装、更新与回滚](docs/setup.zh-CN.md)。

## Setup 实际安装什么

| 能力 | 路径 | 用途 |
| --- | --- | --- |
| `global-policy` | `~/.codex/AGENTS.md` | 权限、自主权、工程、证据、路由、委派和沟通的精简全局协议 |
| `project-context` / Hooks | `~/.codex/.rootloom/components.json` | 分别启停项目播种与子代理审计 |
| `delegation-control` | `~/.codex/config.toml` | 只管理 `agents.max_threads = 4`、`max_depth = 1` 和中断可见性；其余键保留 |
| `high-assurance` | `~/.codex/high-assurance.config.toml` | Sol/high、on-request、workspace-write 的质量优先 CLI profile |
| `delegation-control` | `~/.codex/agents/*.toml` | Terra 证据调查 + Sol 根因、实施、验收的原子角色组 |
| `command-safety` | `~/.codex/rules/rootloom.rules` | 允许本地 commit，单独治理发布、基础设施和破坏性命令 |

Setup 不会改变你的普通默认模型、推理等级、审批策略、sandbox、供应商、MCP、插件或 Apps，也不会把 `delegation-control` 拆成容易误导人的半套角色。

## 两份 `AGENTS.md` 成果

仓库包含真实打磨成果，而不只是说明文字：

- [全局工作协议](plugins/rootloom/assets/system/AGENTS.md)：跨项目安装。
- [项目指导成品示例](examples/AGENTS.project.md)：托管事实 + 精简用户不变量。
- [本仓库自己的 AGENTS.md](AGENTS.md)：真实的生成与打磨示例。

### 全局指导只拥有稳定行为

它定义授权、可逆自主执行、任务分级、工作区保护、根因与范围默认值、证据标准、流程路由、自动项目指导、委派上限和精简沟通；不包含仓库命令、框架偏好、项目架构或人格扮演。

### 项目指导只拥有仓库事实

`SessionStart` Hook 确定性提取项目定位、事实来源文件、顶级结构、包管理器、标准命令、CI 和模块边界。它只写入带标记的托管区块，并保留区块外全部内容。

`$refine-project-guidance` 只添加会改变未来决策的持久、有路径证据的不变量：所有权方向、生成代码边界、公开或持久化契约，以及权威架构/迁移/验证文档。

只有具备独立 Manifest、命令、所有权或不变量的真实模块边界才会得到嵌套指导。系统绝不强制创建每文件 L3 注释。

## 分级任务入口与根因门禁

Rootloom 的全部工程工作流共用一套风险词汇：

| 等级 | 适用任务 | 入口与证据 |
| --- | --- | --- |
| Tier 0 Direct | 琐碎、低风险、可逆的机械工作 | 直接执行，只做最小相关检查 |
| Tier 1 Scoped | 普通 Bug、功能切片、重构和边界明确的多文件工作 | 内部补全 `Intent + Context + Tools + Constraints + Verification`，要求定向证据 |
| Tier 2 Governed | 跨边界、高风险、对外变更或根因存在实质不确定性的工作 | 展示治理任务包、影响图、兼容/回滚与显式门禁 |

行为缺陷默认至少是 Tier 1，除非修正可被证明为纯机械操作。Tier 1 沿“现象 → 触发条件 → 所有权路径 → 被破坏的不变量 → 根因”诊断；Tier 2 再加入竞争假设和 GO/NO_GO 门禁。可逆绕行必须标记为 `MITIGATION`，绝不能冒充完整根因修复。

Tier 0 和 Tier 1 的任务包默认只在内部使用；只有用户要求、需要交接、存在阻塞决策或进入 Tier 2 时才展示，避免把小修改官僚化。

## 完整工作流系列

| Skill | 触发场景 | 核心契约 |
| --- | --- | --- |
| `$setup-rootloom` | 显式安装、更新、审计、换层或回滚 | 选择能力预设；先计划；绝不静默替换用户策略 |
| `$seed-project-guidance` | 指导缺失或结构事实过期 | 只生成确定性事实 |
| `$refine-project-guidance` | 第一次非平凡任务、重复犯错或架构/契约变化 | 只补充持久项目不变量 |
| `$operating-coding-change` | Tier 0 Direct 与 Tier 1 Scoped 实施 | Software 3.0 入口、分级根因门禁、小范围 diff、成比例验证 |
| `$operating-code-review` | 只读审查 | 证据化 findings 优先，不修改 |
| `$operating-high-risk-change` | Tier 2 Governed 的 API、Schema、数据、安全、基础设施、部署、发布或不确定根因 | 治理任务包、ExecPlan、诊断、兼容、回滚、授权门禁 |
| `$high-assurance-coding-change` | 用户显式要求受控多代理 | 证据 → 根因门禁 → 唯一写代理 → 确定性验证 → 独立评审 |

普通任务保持单 Agent。高保障流程是显式选择，因为多个 Agent 会增加 Token、延迟和协调风险。

## 模型路由

选择 `delegation-control` 后，默认角色分配优化的是交付总成本，而不是单次调用价格：

```text
evidence_explorer       gpt-5.6-terra / medium / read-only
root_cause_reviewer     gpt-5.6-sol   / xhigh  / read-only
implementation_worker   gpt-5.6-sol   / high   / workspace-write
verification_reviewer   gpt-5.6-sol   / xhigh  / read-only
```

Terra 只负责压缩受限证据；Sol 负责昂贵的判断、代码实施和最终验收。较弱模型永远不拥有最终根因、实现或接受决策。

自定义 Agent TOML 是模型路由的唯一事实来源。Skills 决定顺序和门禁；Hooks 只审计。父任务的实时权限可能覆盖子代理默认值，因此需要硬阶段隔离时使用确定性 Runner。

## 为什么限制四个却还能看到十个

`agents.max_threads = 4` 限制的是**同时打开的线程**，不是整个任务累计创建的子代理数量。四个 Agent 完成并关闭后，可以再创建六个，全程仍未超过四个并发。

可选的 `delegation-control` 层再增加两层控制：

- 全局指导和 Skills 规定每任务累计四个子代理；
- `SubagentStart` 计数器向 UI 告警，并让第五个子代理停止工作、向父任务汇报。

当前 Hook API 不能在启动时取消子代理，所以这层明确标为行为提醒，不冒充硬保证。确定性高保障 Runner 才是严格路径。

## `git commit` 不再掉进审批死锁

Rules 经过测试会得到：

```text
git commit          → allow
git push            → prompt
git reset --hard    → forbidden
```

本地 commit 是可逆仓库历史，不是远程发布。push、Release、包发布、基础设施变更和破坏性操作仍单独治理。

Rules 采用最严格的匹配结果。如果另一条宽泛规则写了 `git → prompt`，它会覆盖 `git commit → allow`。同时，`approval_policy = "never"` 无法回答 prompt，所以非交互执行中的 prompt 命令只会失败。安装文档给出了使用 `codex execpolicy check` 排查这一问题的精确方法。

## 确定性高保障路径

当原生 spawn 表面无法证明指定角色/模型，或阶段顺序必须完全固定时，运行内置连续流水线：

```bash
python3 <high-assurance-skill-dir>/scripts/run_pipeline.py \
  --repo /absolute/path/to/repo \
  --task /absolute/path/to/task.md \
  --verify 'make focused-test' \
  --verify 'make check'
```

Runner 读取同一组四个 Agent TOML，并强制仓库锁、干净基线、只读阶段快照、唯一写代理、精确允许路径、Git index 不变、结构化输出、确定性验证、独立评审和最多一次修复循环。产物为私有，并且必须位于目标仓库之外。

完整边界见[架构](docs/architecture.zh-CN.md)。

## GEB：保留洞察，去掉提示词债务

[GEB 系统](https://chunxiang.space/geb-system)正确强调了分层局部上下文和代码/文档回环。本项目保留这些思想，转换为全局 → 根目录 → 真实模块的指导层级与自动播种。

本项目舍弃身份扮演、隐藏思考指令、通用文件行数法则、完整 L2 文件清单、强制 L3 源码头部，以及会阻塞无关工作的文档扩张。这些做法与精简提示词冲突，也会制造陈旧重复的“地形副本”。

详细分析见[官方指南与 GEB 对照](docs/guidance-design.zh-CN.md)。

## 为什么核心不带 MCP

核心只需要本地 Git/文件证据和 Codex 原生配置。增加 MCP 会多出进程和信任面，却没有新增缺失能力。

只有当某个自定义角色确实需要外部事实来源——内部文档、Issue、可观测性或部署——才应为这个窄角色配置 MCP 和工具审批。不要为了架构清单完整而让所有编码任务继承它。

## 安全模型

- 项目播种是本地、受限、确定性、仅标准库、零网络的。
- 无标记指导、override、符号链接、不可信仓库、退出项目、临时/vendor/cache 目录、疑似密钥和损坏托管区块都会被保留或拒绝。
- 全局 setup 是显式、原子、备份、哈希校验且可回滚的。
- 只读角色默认关闭 Apps；标准角色中只有一个可写。
- Rules、sandbox、Hooks、Skills 和模型指令是纵深防御，不能替代 OS 策略、凭据、分支保护、审查或 CI。

## 更新

```bash
codex plugin marketplace upgrade rootloom
codex plugin add rootloom@rootloom
```

重新审查更新后的 Hook 定义，新建任务，再次调用 `$setup-rootloom`。计划只会展示变化的托管资产。

## 本地开发

```bash
git clone https://github.com/liyanqing90/rootloom.git
cd rootloom
make check
```

`make check` 会验证 marketplace、插件、Hooks、全部 Skills 及 UI 元数据、setup 资产、Python/SVG 语法、链接、发布卫生、疑似密钥、命令 Rules、播种器、setup/rollback、子代理预算和确定性 Runner 门禁。

真实冒烟测试使用一次性 `CODEX_HOME`：

```bash
make smoke
```

## 文档

- [品牌系统与资产使用](docs/brand.zh-CN.md)
- [架构与执行边界](docs/architecture.zh-CN.md)
- [指导设计与 GEB 分析](docs/guidance-design.zh-CN.md)
- [安装、更新、回滚、commit 策略和子代理限制](docs/setup.zh-CN.md)
- [故障排查](docs/troubleshooting.zh-CN.md)
- [贡献指南](CONTRIBUTING.zh-CN.md)
- [安全策略](SECURITY.md)
- [更新日志](CHANGELOG.md)

## 许可证

[MIT](LICENSE) © 2026 liyanqing。
