# 2026-10-08 · workspace-bootstrap

- 记录人：Codex
- 记录日期与时区：2026-10-08，Asia/Shanghai；关键检查在 11:27–11:32 执行
- 分支：`codex/feature_scaffold_20261008`
- 关联任务：S0 开发骨架；为 F01–F12 建立代码、文档与验收位置
- 状态：骨架和本地检查完成；农业业务尚未实现

## 本次目标

建立可用于实际开发的独立本地仓库，包含清晰模块边界、可运行入口、依赖锁文件、启动与检查脚本、Git 配置及真实开发记录。

## 实际完成与文件

1. 在 `D:\Dev\软著\crop-digital-twin` 建立单仓库。原 `wofost_lai_edge` 与原方案文档保持独立。
2. `frontend/`：Vue 3、TypeScript、Vite 开发首页；健康请求客户端及失败处理；未来页面、地图、农事、影像与长势模块位置。
3. `backend/`：FastAPI 应用工厂、配置验证、`GET /api/v1/health`；业务用例、领域、基础设施、worker 与迁移目录预留。
4. `packages/crop_engine/`：独立 Python 包边界及后续适配/质控/校准说明；未添加演示作物算法或假业务接口。
5. `contracts/`：从真实应用导出的 JSON/YAML OpenAPI，当前仅一个业务路径；接口导出一致性检查。
6. `docs/`：需求追踪、模块语言与目录表、架构、模型验证、ADR、运行手册、进度表和日志模板。复制原方案的 6 张 SVG 图、设计 JSON 和数据字典源文件。
7. `infra/compose/`：PostgreSQL/PostGIS 与 Redis 的本地配置；没有启动数据库或实现持久化。
8. `scripts/`：隔离环境安装、API/前端启动、检查、接口导出、日志生成；根目录增加编码、行尾、忽略、编辑器和协作配置。
9. Git 在功能分支初始化；依赖、真实配置、运行数据、备份和机器路径被忽略。CI 配置和 PR 模板就位，但没有远程仓库、远程执行或平台保护规则。

环境：Windows、Python 3.12.6、Node 24.19.0、npm 11.17.0、Git 2.47.1.windows.1、uv 0.12.23。项目 Python 环境位于 `.venv/`，uv 工具位于 `.tools/uv/`。版本由 `uv.lock` 和 `frontend/package-lock.json` 固定。

## 验证证据

| 命令/检查 | 结果 | 环境/限制 |
|---|---|---|
| `scripts/bootstrap.ps1` | 通过；锁定安装及 npm ci 完成 | 本地隔离环境；默认 Node 另有旧版本 |
| PowerShell AST 解析全部 `.ps1` | 通过 | 检查语法；不等同执行所有持续运行服务 |
| `scripts/check.ps1`：Ruff 检查与格式 | 通过；13 个 Python 文件已规范 | 仅当前骨架 |
| `mypy` | 通过；10 个源文件无问题 | strict 模式 |
| `pytest` | 2 项通过，无警告 | 健康响应及实际接口清单 |
| OpenAPI `--check`、workspace 检查 | 通过 | 实现契约一致；14 个关键文件 |
| Vue/TypeScript 类型、ESLint、Prettier | 通过；ESLint 零警告 | 当前开发首页及客户端 |
| `vitest run` | 3 项通过 | HTTP 失败、契约异常、正确响应 |
| `npm run build` | 通过，生成 dist | 构建输出被忽略；不是生产部署 |
| `docker compose --env-file .env.example -f infra/compose/compose.dev.yaml config --quiet` | 通过 | 仅模板解析，未启动容器 |
| 两个镜像标签的 `docker manifest inspect` | 通过 | 只验证仓库清单可访问，未拉取运行 |
| Edge/Playwright 本地浏览器冒烟 | 4 项通过 | 页面→Vite 代理→真实 API、手机无横向溢出、HTTP 503 提示、无运行错误 |
| 桌面/手机截图查看 | 已查看，中文及按钮显示正常 | 证据放忽略的 runtime/ |
| `git check-ignore` | 预期本机配置、数据、日志、备份、依赖和构建文件被忽略 | 本机路径配置未入 Git |
| 暂存区清单、`git diff --cached --check` 与关键文件复核 | 通过；116 个版本化文件约 0.42 MB | 无真实 .env、依赖目录或运行数据；清单已复核 |

浏览器检查报告：`runtime/scaffold-smoke.json`；截图：`runtime/scaffold-desktop.png`、`runtime/scaffold-mobile.png`。冒烟检查结束后已停止本次启动的服务，8000/5173 没有遗留监听。

## 问题、决策与下一步

- 首次 npm 调用遇到 `EBADENGINE`：本机默认 Node 24.11.1 不满足前端 engines，Windows npm.cmd 还会优先选择同目录旧 Node。修正为显式使用选定 Node 执行 npm CLI，并在忽略的 `.tools/local-settings.json` 保存本机 24.19.0 路径；不修改全局安装或 PATH。
- 初始 ESLint 9 已停止维护，改为经官方状态核对的 ESLint 10；使用 eslint-config-prettier 避免格式规则冲突，检查要求零警告。
- 当前 Starlette 测试客户端提示旧 httpx 兼容层弃用，改用 httpx2；后端测试重新通过且无此警告。
- uv 缓存与项目目录无法硬链接时自动复制；安装成功，未因此更改系统缓存策略。
- 原字典的物理外键与组织逻辑外键规则待决策，尚无数据库迁移；ADR 已记录。
- 地块、权限、天气、地图、PCSE、任务队列、遥感反射率/LAI 及校准均未实现；未评估农艺精度、生产性能、备份恢复或正式部署。
- 80% 核心业务行覆盖率是后续质量目标；当前没有核心农业业务代码，不以骨架测试推断已达到目标。
- 下一步：确定作物与地区，设计地块/种植季/管理事件契约，决策数据约束，完成持久化业务闭环，再接入 PCSE 和遥感流程。

## Git

初始提交信息：`chore(workspace): bootstrap crop twin development scaffold`。此日志包含在该提交中，提交 ID 可用 `git log --oneline --all` 查询；不在提交内容中循环记录自身哈希。

该提交建立本地 master、develop、test、release_20261008 基线指针，当前工作分支仍为功能分支。基线不表示产品发布、正式评审或分支已受保护。远程地址未配置。
