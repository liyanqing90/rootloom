# Setup、更新与回滚

安装插件只会暴露 Skills 和经过审查的 `SessionStart` Hook 定义。应用全局 Personal Core 资产是独立的显式操作。

## 安装

```bash
codex plugin marketplace add liyanqing90/rootloom
codex plugin add rootloom@rootloom
```

新建任务并检查 `/hooks`。唯一 Hook 是本地项目指导播种；只有有效的托管组件策略启用后才会执行。

## Preset

| Preset | 能力 |
| --- | --- |
| `skills-only` | 仅 Skills；关闭 Hook |
| `guidance` | `global-policy`、`project-context` |
| `personal` | Guidance + `command-safety`；默认 |
| `engineering` | `personal` 的兼容别名 |

`skills-only` 使用的空 capability 集合会作为明确的已安装状态保存。后续没有显式新选择的 `status`、`plan` 与 `apply` 都会保持它。

检查并应用：

```bash
python3 <setup-skill>/scripts/setup_rootloom.py list-components
python3 <setup-skill>/scripts/setup_rootloom.py plan --preset personal
python3 <setup-skill>/scripts/setup_rootloom.py apply --preset personal
python3 <setup-skill>/scripts/setup_rootloom.py status
```

也可以精确选择能力：

```bash
python3 <setup-skill>/scripts/setup_rootloom.py plan \
  --capabilities global-policy,project-context,command-safety
```

## 托管目标

| 路径 | 用途 |
| --- | --- |
| `~/.codex/AGENTS.md` | 个人工程工作协议 |
| `~/.codex/rules/rootloom.rules` | 命令安全策略 |
| `~/.codex/.rootloom/components.json` | Hook 开关 |
| `~/.codex/.rootloom/state.json` | 已安装选择与目标哈希 |
| `~/.codex/.rootloom/backups/` | 修改前文件副本与清单 |

Rootloom 不会修改普通模型、推理、沙箱、审批、Provider、MCP、插件或 App 配置。

## 安全契约

Setup：

- Skill 应用前先展示 plan；
- 使用普通 create-exclusive 本地锁；
- 拒绝符号链接目标和无标记的用户文件冲突；
- 使用 `--replace-conflicts` 前需要精确授权；
- 第一个托管目标写入前复制所有被替换文件；
- 逐目标原子写入；
- 记录 apply 后哈希以检测漂移；
- 回滚时恢复原内容和 POSIX mode。

个人契约不承诺跨整个事务的崩溃补偿。如果进程在多个文件替换之间停止，请运行 `status`、检查 `.rootloom/backups/` 并显式处理可见不一致。它也不防御敌对同用户进程并发替换锁或目标路径。

## 检查命令 Rules

```bash
codex execpolicy check --pretty --rules ~/.codex/rules/rootloom.rules -- git commit -m test
codex execpolicy check --pretty --rules ~/.codex/rules/rootloom.rules -- git push origin main
codex execpolicy check --pretty --rules ~/.codex/rules/rootloom.rules -- git reset --hard
```

预期分别为 `allow`、`prompt` 和 `forbidden`。Rules 是 argv 前缀策略，不是完整 shell 安全边界。

## 修改 preset 或回滚

修改能力选择前必须先回滚：

```bash
python3 <setup-skill>/scripts/setup_rootloom.py rollback
python3 <setup-skill>/scripts/setup_rootloom.py plan --preset guidance
python3 <setup-skill>/scripts/setup_rootloom.py apply --preset guidance
```

回滚会预检每个托管文件。目标在 setup 后被修改时会停止，不覆盖该修改。普通 rollback 返回上一个简单备份；`rollback --all` 沿备份链回到安装前状态。

完成全局回滚后移除插件 Skills：

```bash
codex plugin remove rootloom@rootloom
```

## 更新

```bash
codex plugin marketplace upgrade rootloom
codex plugin add rootloom@rootloom
```

新建任务，再次检查 Hook 定义，规划同一 preset 后应用。

## 从 Enterprise Assurance 1.2.19 迁移

两个 setup 契约有意不兼容。安装 Personal Core 前，请使用 `codex/enterprise-assurance` 上的 1.2.19 代码回滚旧 setup。不要让 Personal Core 猜测或删除自定义 Agents、高保障 profile、配置限制、Human Review 状态或恢复日志。
