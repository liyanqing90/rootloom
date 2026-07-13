# 故障排查

## 插件已安装，但 Hook 没有运行

1. 新建 Codex 任务；插件与 Hook 在任务启动时加载。
2. 执行 `/hooks`，检查 `SessionStart` 条目。
3. 如果提示需要审查，核对精确命令后完成信任。
4. 确认插件已启用：

   ```bash
   codex plugin list --json
   ```

正常使用时不要添加 `--dangerously-bypass-hook-trust`。

## 没有创建 `AGENTS.md`

直接探查仓库：

```bash
python3 plugins/rootloom/skills/seed-project-guidance/scripts/seed_project_guidance.py \
  probe --cwd /path/to/repository
```

以下跳过原因通常是有意设计：

- `not_a_git_repository`
- `untrusted_project`
- `override_exists`
- `user_owned_guidance`
- `disabled`
- `guidance_is_symlink`
- `unsafe_path`
- `plan_mode`

## 仓库已信任，但仍报告 `untrusted_project`

使用 `/debug-config` 确认当前生效的 Codex 配置层，以及仓库或父级根目录是否包含 `trust_level = "trusted"`。不要仅为了让 Hook 通过而信任一个过大的目录；应先审查仓库。

## 已有 `AGENTS.md` 没有更新

没有播种器标记的文件归用户所有，插件不会接管或改写。如果希望获得托管基线，可以先备份原内容，运行一次播种器，再把自定义规则放到托管区块之后。

## 校验报告 `managed_block_drift`

托管区块被手动编辑，或已不再匹配仓库证据。把自定义内容保留在标记之外，然后重新运行 `seed`。

## 校验报告疑似密钥

从指导中移除凭据、Token、私钥或看起来像密钥的示例。秘密应存放在仓库批准的 Secret Manager 或环境中，不能写入 `AGENTS.md`。

## 普通模式有效，但 Plan 模式不运行

这是设计行为。Plan 模式下自动播种只读不写；回到可写模式后再运行 Skill。

## 没有生成嵌套指导

嵌套播种是懒执行的。目标必须位于 Git 根目录内部、深度不超过三层，并包含独立的受支持 Manifest。普通目录不会获得自己的 `AGENTS.md`。

## Setup 报告用户自有冲突

让 `$setup-rootloom` 先展示计划并检查具体路径。安装器拒绝无托管标记的文件，也拒绝上次 apply 后被修改的托管文件。优先通过经过审查的变更把有价值的个人策略合并到模板中。只有明确授权这些路径后才使用 `--replace-conflicts`；安装器会备份，但仍会替换文件内容。

## 我不需要子代理

安装 `--preset engineering`，不要选 `delegated` 或 `full`。它保留全局/项目指导和命令安全，但不会写入 `[agents]` 限制、自定义 Agent TOML、质量 profile，也不会启用子代理审计。`skills-only` 和 `guidance` 还可以更小；使用 `list-components` 查看精确映射。

若已经安装其他预设，先运行 `rollback --all`，再应用更小层级。安装器拒绝原地切换能力，避免未选择的旧资产变成含义不明的残留。

## `approval_policy = "never"` 时 `git commit` 被拒绝

检查所有生效的 Rules，而不只是本系统文件。Rules 采用最严格匹配，因此宽泛的 `git → prompt` 会覆盖 `git commit → allow`。非交互的 `never` 无法回答 prompt，命令只会失败。

```bash
codex execpolicy check --pretty \
  --rules ~/.codex/rules/rootloom.rules \
  -- git commit -m test
```

本系统自身应返回 `allow`。若组合策略仍为 prompt，应先理解来源，再删除或收窄冲突规则。不要为了修复本地 commit 而把 `git push` 改成 allow。

## 已设置 `max_threads = 4`，任务里却出现十个 Agent

`max_threads` 限制同时打开的线程，不限制累计总数。已完成或关闭的子代理会释放槽位。审计 Hook 会统计父会话的唯一子代理并在超过四个时告警，但 `SubagentStart` 无法取消子代理。必须硬限制阶段数量时，使用确定性 Runner。

## 自定义 Agent 看起来用了错误模型

先确认确实选择了 `delegation-control` 或 `full`，再确认角色文件存在于 `~/.codex/agents/`。新建任务，然后运行 setup status 和高保障校验器。线程标签或昵称不能证明角色 TOML 已被选择。如果当前 spawn 工具无法显式选择并证明 `agent_type`，应使用确定性 Runner，而不是依赖自然语言路由。

## 高保障校验显示原生路由未就绪

这可能是正确结果。Runner 与原生路由分别判断 readiness。若 Agent 文件和 profile 通过，但本地 spawn 工具不能证明 `agent_type`，确定性连续 Runner 仍可使用，而原生模型路由保持关闭。

## 严格 Runner 以退出码 10 和 `HUMAN_REVIEW_REQUIRED` 结束

这是显式授权 `--allow-protected-path-delete` 操作后的预期结果。授权会在 Writer 前检查，并使该任务成为 deletion-only，因此普通修改、rename、move 和 visible 文件创建必须拆到另一次任务。Protected deletion 模式还要求干净基线和 `--max-repair-cycles 0`。验证和模型 Review 已通过，但旧的 protected 内容被刻意保持为从未读取，因此 Runner 不能给出自动 PASS。请使用内置决定命令；Human Review v4 会在 supplied Run 是副本、Result 变化、任一 protected 目标重新出现（包括 ignored 文件）、父边界变化、完整 metadata-only 下限无法保持、规范化仓库承诺漂移或已审证据变化时拒绝 accept。版本 2/3 审核结果必须重跑，或通过显式外部流程处理。自动化不得把退出码 10 转成成功。

## Decision Pair 验证报告 `INVALID` 或 `STALE`

运行 `review_decision.py verify --repo ... --run-dir ...`，不要提供 reviewer 或 decision 参数。`VALID`/0 表示规范 Result、Terminal、Summary、仓库/protected deletion 承诺与 Run Directory 身份仍一致。`INVALID`/9 表示持久化 Binding/Pair Schema 格式错误、内部冲突、非规范、超预算、路径不安全，或不再是普通单链接私有文件。只有结构已确认有效、但当前仓库、已审 Artifact 或 protected deletion 状态不再匹配时才输出 `STALE`/12。stdout 仍只有一个状态词；stderr 包含一条不带 Artifact 内容的有界诊断原因。应重新运行高保障流程，不要编辑证据。验证命令完全只读，不刷新、修复或签名证据。

## 严格 Runner 拒绝 verification entrypoint 变化

Runner 会在 Writer 前为检测到的验证入口建立指纹，在每条确定性验证命令前检查对应入口，并在命令结束后立即确认仓库未变化。它也会记录常见缺失候选，因此 Writer 在基线后新建 `GNUmakefile`、`pytest.ini` 或类似 harness 会被视为验证入口变化。它会记录仓库内每个符号链接路径组件，并绑定最终目标内容。

如果 Writer 修改了 `Makefile`、`package.json`、pytest 配置、`--verify` 使用的已检测仓库相对脚本，或通过 `--bind-verification-path verify-N:path` 显式绑定的路径，任务会在执行验证前停止。显式绑定必须解析为已存在的普通文件，并作为按命令关联的稳定性依赖记录；它不能证明命令真实导入或执行了该文件。protected harness 会在内容访问前被拒绝。应使用外部可信 harness，把重要的仓库内依赖绑定到正确命令，将测试入口变更拆成单独任务，或选择不在 Writer 允许范围内的验证入口。

如果 Runner 报告的是未授权 protected 路径变化，说明它在 Writer 返回后停止了验收，sandbox 并未预防文件系统修改。应人工检查并恢复该路径；Rootloom 不会读取或备份 ignored/敏感内容用于自动回滚。

## Python 报告缺少 `tomllib`

请使用 Python 3.11 或更高版本：

```bash
python3 --version
```

## 更新插件

```bash
codex plugin marketplace upgrade rootloom
codex plugin add rootloom@rootloom
```

随后新建 Codex 任务。如果 Hook 定义发生变化，请通过 `/hooks` 重新审查并信任。

升级后再次运行 `$setup-rootloom`，让新的全局托管资产经过计划后应用。仅安装插件不会覆盖 Codex home 中的策略文件。
