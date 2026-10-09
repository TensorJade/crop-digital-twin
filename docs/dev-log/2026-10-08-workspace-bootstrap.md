# 2026-10-08 项目初始化

| 项目 | 内容 |
|---|---|
| 记录人 | Codex |
| 时间 | 11:27–11:32，Asia/Shanghai |
| 分支 | `codex/feature_scaffold_20261008` |
| 任务 | S0；为 F01–F12 建立开发目录 |
| 状态 | 开发环境和入口完成，农业业务尚未实现 |

## 修改内容

在 `D:\Dev\软著\crop-digital-twin` 建立独立仓库，与原 `wofost_lai_edge` 和方案文档分开维护。

| 目录 | 本次内容 |
|---|---|
| frontend | Vue 3、TypeScript、Vite 首页，健康请求和错误提示 |
| backend | FastAPI 应用工厂、配置检查、健康接口 |
| packages/crop_engine | 独立 Python 包，预留模型适配、质控和校准位置 |
| contracts | 从应用导出的 JSON/YAML OpenAPI及一致性检查 |
| docs | 需求、架构、目录、验证计划、ADR、运行手册和日志模板 |
| infra/compose | PostgreSQL/PostGIS、Redis 开发配置 |
| scripts | 安装、启动、检查、契约导出和日志生成脚本 |

复制原方案的 6 张 SVG 图、设计 JSON 和数据字典源文件，配置编码、行尾、忽略规则、编辑器、CI 和 PR 模板。数据库容器尚未启动，业务持久化和作物算法尚未实现。

环境为 Windows、Python 3.12.6、Node 24.19.0、npm 11.17.0、Git 2.47.1.windows.1、uv 0.12.23。Python 环境位于 `.venv/`，uv 位于 `.tools/uv/`；依赖由 `uv.lock` 和 `frontend/package-lock.json` 固定。

## 检查结果

| 检查 | 结果 | 备注 |
|---|---|---|
| bootstrap | 通过 | 锁定安装和 npm ci 完成 |
| PowerShell AST | 通过 | 全部 ps1 语法检查 |
| Ruff / mypy | 通过 | 13 个 Python 文件；mypy 检查 10 个源文件 |
| pytest | 2 项通过 | 健康响应和接口清单，无警告 |
| OpenAPI / 目录检查 | 通过 | 1 条路径；14 个关键文件 |
| 前端类型 / ESLint / Prettier | 通过 | ESLint 零警告 |
| Vitest | 3 项通过 | 请求失败、契约异常和正确响应 |
| Vite build | 通过 | 输出位于忽略的 dist |
| Docker Compose config | 通过 | 仅解析模板，未启动容器 |
| docker manifest inspect | 通过 | 两个镜像标签，未拉取或运行 |
| Edge / Playwright | 4 项通过 | API 代理、390px 布局、HTTP 503 和运行错误检查 |
| 桌面 / 手机截图 | 显示正常 | 中文和按钮已查看 |
| 忽略规则 / 暂存区 | 通过 | 116 个文件，约 0.42 MB |

Compose 检查使用 `docker compose --env-file .env.example -f infra/compose/compose.dev.yaml config --quiet`。暂存区已执行 `git diff --cached --check`，未包含本机配置、依赖、数据库、日志或备份。

浏览器报告和截图保存在 `runtime/scaffold-smoke.json`、`runtime/scaffold-desktop.png`、`runtime/scaffold-mobile.png`。检查后停止服务，8000/5173 端口未留监听。

## 问题处理

| 问题 | 处理 |
|---|---|
| npm 报 EBADENGINE，默认 Node 为 24.11.1 | 显式用 Node 24.19.0 执行 npm CLI，本机路径保存在 .tools/local-settings.json |
| npm.cmd 优先使用同目录旧 Node | 安装脚本使用选定的 Node，不修改全局 PATH |
| ESLint 版本选择及格式冲突 | 核对维护状态后使用 ESLint 10，配合 eslint-config-prettier |
| Starlette 测试客户端提示 httpx 兼容层弃用 | 改用 httpx2，复测通过且无该警告 |
| uv 缓存无法硬链接 | 安装自动复制完成，保留原缓存设置 |

## 待办

物理外键与逻辑外键的取舍尚待确定，已记录在 ADR。下一步确定作物和地区，设计地块、种植季、农事接口及数据约束，再实现持久化。

本次尚未实现权限、天气、地图、PCSE、任务、遥感和模型校准，也未开展农艺、容量、备份恢复及部署检查。80% 行覆盖率作为后续核心业务的检查门槛。

## 提交

`59da0fcbfceb25bb5a84ce583fed07729a6a68a2`：建立项目目录、前后端入口和开发脚本。

该提交同时作为本地 master、develop、test、release_20261008 的初始指针，开发仍在功能分支。当时尚未配置远程仓库，发布和正式评审未开始。
