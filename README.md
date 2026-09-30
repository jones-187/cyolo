# cyolo

`cyolo` 启动长期共享的 `pi_yolo_env` 容器。裸命令和 `cyolo pi` 等价。

容器长期运行，多个终端共享同一个 Pi 环境；退出一个终端不会停止容器。入口只支持终端交互执行。

入口只允许从宿主 `$HOST_HOME/projects`、`/tmp` 或本仓库目录启动。任意深度子目录都会把同一个物理路径作为容器 cwd；其他目录会立即报错。

普通启动不会联网构建镜像。首次使用或宿主 Pi 版本变化时运行：

```sh
cyolo pi --build
```

版本不一致时，默认停止并提示更新命令。明确的应急启动方式是：

```sh
cyolo pi --allow-version-mismatch
```

`--` 后的参数原样传给 Pi。`--build` 会在构建前检查容器内是否还有 Pi 进程；发现进程或检查失败都会拒绝构建，避免打断任务。普通启动不会自动构建，也不会因 Compose 配置变化替换正在运行的容器。

环境变量按名称自动传给本次 `docker exec`，不把值写入命令行或日志。身份、PATH、HOME、SHLVL、IPC、Pi 会话目录等运行时变量会过滤；多行值保持安全传递。宿主 Git 身份只通过项目配置生效，不修改全局 Git 或 SSH 配置。

镜像构建时准备 Node 24、宿主准确 Pi 版本、PyYAML、sqlglot、PyMySQL、uv/uvx 和 Grafana MCP；Grafana uv 缓存使用持久 Docker volume。当前五个 MCP 配置保持现状，不新增 MCP。测试和验证不执行生产 SQL。

挂载关系固定如下：

| 宿主路径 | 容器路径 | 权限 |
| --- | --- | --- |
| `$HOME/projects` | `$HOME/projects` | 读写 |
| `/tmp` | `/tmp` | 读写 |
| cyolo 项目根目录 | 相同绝对路径 | 读写 |
| `$HOME/.pi`、`$HOME/.codex`、`$HOME/.m2` | 相同绝对路径 | 读写 |
| `$HOME/.agents`、OpenCode 配置、禅道部署目录 | 相同绝对路径 | 只读 |
| 宿主 `.agents/skills/modsearch` 软链解析出的包目录、`$HOME/.modsearch` | 相同绝对路径 | 只读 |
| `$HOME/.ssh`、`$HOME/.gitconfig`、Java、Maven | 相同绝对路径或 `/opt` | 只读 |

宿主 shell 包装函数只调用仓库中的 `bin/cyolo`，不复制入口逻辑；安装包装函数后，裸 `cyolo` 和 `cyolo pi` 都启动 Pi。裸 `cyolo` 的默认行为已经从旧入口改为 Pi，旧 Claude/Codex 入口使用 `cc`、`claude`、`cx` 或 `codex`。

modsearch 使用宿主已有包和配置。构建或首次创建容器时，入口解析 `$HOME/.agents/skills/modsearch` 软链，读取包目录路径并把它以只读方式挂载；容器内的 `/usr/local/bin/modsearch` 指向该包的 `dist/main.js`。`$HOME/.modsearch` 也只读挂载，配置内容和 secret 不写入镜像、命令行或日志。

共享 `.pi` 配置和会话目录会让多个终端看到同一状态；同时修改同一会话或配置时没有隔离保证。生产 MySQL 查询仍保留 MCP 的人工文字确认，这是无人值守流程中的明确例外。

版本不一致时，更新命令是 `cyolo pi --build`；必要时可用 `cyolo pi --allow-version-mismatch` 应急启动。缺少镜像时也必须先显式构建。`cc`、`claude`、`cx`、`codex` 保留旧入口，并显示停止维护警告。

测试使用标准库和 Docker 边界替身：

```sh
python3 -m unittest discover -s tests
bash -n bin/cyolo
```

真实 Docker、Pi 启动和 MCP 加载检查由交付验证脚本执行；测试不会执行生产 SQL。
