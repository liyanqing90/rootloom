# 安装、更新与回滚

安装插件会提供 Skills 和需审查的生命周期 Hooks。全局工程基线需要一次单独的显式应用，避免插件升级静默替换个人策略。

## 安装插件

```bash
codex plugin marketplace add liyanqing90/rootloom
codex plugin add rootloom@rootloom
```

新建任务后打开 `/hooks`，检查两条插件命令：

- `SessionStart` 运行本地项目指导扫描器。
- `SubagentStart` 记录累计子代理数量，并审计命名角色与模型路由。

只有信任当前 Hook 定义后，插件 Hooks 才会运行。

组件策略缺失时，两个内置 Hooks 都关闭。应先选择并应用能力预设，再信任 Hook 定义。Setup 写入 `components.json` 后，每个 Hook 严格遵循独立布尔开关；策略损坏或被符号链接替换时同样会关闭并告警。

## 先选择能力层级

安装器暴露的是稳定能力层，而不是要求用户理解每个底层文件：

| 预设 | 能力 | 子代理控制 |
| --- | --- | --- |
| `skills-only` | 只有插件 Skills；不写全局资产；关闭生命周期 Hooks | 无 |
| `guidance` | 全局策略 + 自动项目上下文 | 无 |
| `engineering` | 指导层 + 命令安全 | 无；普通开发推荐 |
| `delegated` | 工程层 + 四角色配置与建议式审计 | 已配置；原生路由未获证明 |
| `full` | 委派层 + 严格连续 Runner profile | 已配置；Runner 提供可证明路由 |

`delegation-control` 被刻意设计为一个整体：四个角色 TOML、并发/深度限制和审计 Hook。只装一个角色或只装计数器都会形成“看似受控、实际残缺”的半套系统，因此安装器不把这些文件作为用户层面的独立等级。

查看能力目录：

```bash
python3 <skill-dir>/scripts/setup_rootloom.py list-components
```

用户明确要求“安装完整系统”时默认使用 `full`；普通开发推荐 `engineering`，它不会安装子代理控制。

## 无需手改文件地安装某一层级

显式调用：

```text
$setup-rootloom
先展示能力层级，再规划并应用 engineering 预设。
```

Skill 会自行解析脚本路径。诊断时可使用等价命令：

```bash
python3 <skill-dir>/scripts/setup_rootloom.py plan --preset engineering
python3 <skill-dir>/scripts/setup_rootloom.py apply --preset engineering
python3 <skill-dir>/scripts/setup_rootloom.py status
```

完整系统把 `engineering` 换成 `full`。也可以精确组合能力维度：

```bash
python3 <skill-dir>/scripts/setup_rootloom.py plan \
  --capabilities global-policy,project-context,command-safety
```

可选维度为 `global-policy`、`project-context`、`command-safety`、`delegation-control` 和 `high-assurance`；选择 `high-assurance` 会自动补齐它依赖的 `delegation-control`。

安装事务只写入：

| 目标 | 所有权 |
| --- | --- |
| `~/.codex/AGENTS.md` | 完整托管的全局工作协议 |
| `~/.codex/config.toml` | 只管理三个 `[agents]` 限制键，其余内容全部保留 |
| `~/.codex/high-assurance.config.toml` | 托管的质量优先 profile |
| `~/.codex/agents/*.toml` | 四个托管自定义 Agent 角色 |
| `~/.codex/rules/rootloom.rules` | 托管命令策略 |
| `~/.codex/.rootloom/components.json` | 选择的能力记录与两个 Hook 的独立开关 |
| `~/.codex/.rootloom/` | 私有状态和回滚备份 |

它不会改变默认模型、推理等级、审批策略、sandbox、模型供应商、MCP、插件或 Apps。

Setup 与 rollback 会在 `~/.codex/.rootloom/` 下获取非阻塞跨进程锁；竞争操作会在不触碰受管目标的前提下失败。Apply 在第一次修改目标前准备全部备份与事务清单。Apply 目标写入、rollback 目标写入及各自的最终状态提交都位于补偿边界，因此失败会恢复旧文件与旧状态。清单记录原始权限模式，回滚会恢复这些模式，而不是继承临时文件的默认权限。

## 冲突处理

默认 apply 是原子的，并拒绝：

- 没有系统托管标记的用户自有文件；
- 上次 apply 后被修改的托管文件；
- 符号链接目标；
- 无效的 `config.toml`；
- 含任一未解决冲突的计划。

如果无标记文件与模板完全一致，安装器会安全地补上所有权标记。`--replace-conflicts` 只用于用户明确审查并同意的替换；Skill 使用前必须展示受影响路径。

## 命令策略

选择 `command-safety` 后，安装的 Rules 会严格区分本地历史和对外发布：

- `git commit` → `allow`；
- `git push`、Release 和包发布 → `prompt`；
- 破坏性 reset、强制 clean、批量丢弃 → 按可恢复性设为 `forbidden` 或 `prompt`。

Rules 采用所有匹配项中最严格的决策。因此另一条宽泛的 `git` prompt 规则会覆盖更窄的 allow。若提交仍要求审批，应检查所有生效的 `.rules` 文件。在 `approval_policy = "never"` 的非交互执行中，`prompt` 无法获批，只会失败；安全本地操作应使用 allow，真正需要审批的操作应切换到可交互 profile。

Rules 匹配命令 argv 前缀，不会解析嵌套 shell 字符串。例如 `bash -c 'git push'` 首先按 `bash` 而不是直接 `git push` 治理，可能落入更宽泛策略。应把 Rules 当作纵深防御，不是 shell 安全边界；危险外部效果仍需 sandbox、凭据、分支保护、CI 与人工授权共同约束。

验证策略：

```bash
codex execpolicy check --pretty --rules ~/.codex/rules/rootloom.rules -- git commit -m test
codex execpolicy check --pretty --rules ~/.codex/rules/rootloom.rules -- git push origin main
codex execpolicy check --pretty --rules ~/.codex/rules/rootloom.rules -- git reset --hard
```

## 子代理限制

选择 `delegation-control` 后，`agents.max_threads = 4` 是“同时打开的 Agent 线程”硬上限，不是整个任务的累计数量。一个任务可以关闭四个子代理后再创建更多。

只有选择 `delegation-control` 后，`SubagentStart` Hook 才会按父会话记录累计数量；超过四个唯一子代理后，它会注入停止并汇报的指令。但当前 Hook API 不能取消刚启动的子代理。全局工作协议和受控 Skills 提供行为层面的累计上限；当阶段顺序和数量必须由代码强制时，使用确定性高保障执行器。

严格高保障 Runner 支持 Linux、macOS 与 WSL，不支持原生 Windows。Setup 与项目播种拥有独立 Windows 代码路径，但当前公开 CI 只验证 Linux。

## 更新

```bash
codex plugin marketplace upgrade rootloom
codex plugin add rootloom@rootloom
```

重新审查改变后的 Hook 定义，新建任务，再次运行 `$setup-rootloom`。计划只会列出发生变化的托管资产。

改变已安装的能力组合刻意分为两步：先运行 `rollback --all`，再规划和应用新预设。普通 rollback 只恢复最近一次更新；`--all` 会沿安全事务链回到真正的安装前基线，不会猜测被取消选择的文件应该删除还是保留。

## 回滚

```bash
python3 <skill-dir>/scripts/setup_rootloom.py rollback
```

移除全局 setup 或改变能力层级时使用 `rollback --all`。随后应用 `skills-only`，可以保留工作流 Skills，同时写入关闭两个 Hook 的策略。若连 Skills 与 Hook 定义也要移除，再执行：

```bash
codex plugin remove rootloom@rootloom
```

完整托管文件只有在仍匹配 apply 后哈希时才会回滚。`config.toml` 采用语义回滚：安装器确认三个受管 `[agents]` 值未变，只恢复它们的旧值，并保留后来新增的其他设置——包括 Codex 写入的项目信任记录。恢复的文件会取回 apply 前记录的权限模式。若受管文件或受管配置值发生变化，回滚会停止，不会删除这些新工作。
