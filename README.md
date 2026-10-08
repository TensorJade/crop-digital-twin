# 作物数字孪生系统 · 华南水稻

本地开发路径：`D:\Dev\软著\crop-digital-twin`。前端使用 Vue + TypeScript，后端使用 Python + FastAPI，科学计算保留独立的 PCSE/WOFOST 适配包。

当前版本 **0.2.0** 完成第一个业务模块：地块、水稻种植季、农事记录、单位换算、修订历史和 SQL 持久化。页面按“选地块 → 选种植季 → 记农事”操作，支持手机布局。当前供本地单用户试用；账户授权、生长模拟、天气、卫星地图和无人机校准仍在后续模块中。

## 实施原则

- 一个模块化后端、一套前端。地块、种植季和农事组成农田管理模块。
- HTTP、业务规则和 SQL 分层，仅在真实存储边界使用一个 FarmRepository 接口。
- 默认本地 SQLite，服务器目标 PostgreSQL；Redis 等异步任务需要时再接入。
- 修正新增版本，保留原记录和原因；原始单位与标准量都可追踪。
- 已确认首版为华南水稻，尚无具体试点县市、模型品种参数或农艺精度结论。

见 [模块路线](docs/module-roadmap.md)、[实际进度](docs/progress.md)、[需求追踪](docs/requirements.md)和 [M1 设计与数据流](docs/modules/farm-management.md)。`docs/design-baseline/` 中的完整目标不代表已实现能力。

## 安装与启动

使用 Python 3.12、Node.js 24.19.0、Git。脚本支持 Windows PowerShell 5.1 和 PowerShell 7，安装访问 PyPI/npm。

```powershell
Set-Location 'D:\Dev\软著\crop-digital-twin'
.\scripts\bootstrap.ps1
.\scripts\init-db.ps1
```

安装按锁文件建立隔离环境；初始化运行 Alembic 增量迁移。默认数据库为 `runtime/crop_twin.db`，无需 Docker/Redis。API 启动不自动建表。

若合适的 Node 不在 PATH，可向 npm 相关脚本传入 `-NodeBinDirectory 'C:\path\to\node\bin'`。本机路径存于忽略的 `.tools/local-settings.json`，不修改全局配置。

分别在两个终端运行：

```powershell
.\scripts\start-api.ps1
.\scripts\start-frontend.ps1
```

前端：`http://127.0.0.1:5173`；API 文档：`http://127.0.0.1:8000/docs`。Vite 将 /api 代理到本机 API。记录保存后刷新页面或重启服务仍可读取。启动脚本绑定回环地址；production 模式在账户授权完成前拒绝启动。

## 检查与维护

```powershell
.\scripts\check.ps1
# 本机 Edge：自动启动独立服务、迁移临时数据库并执行浏览器验收
.\scripts\check-e2e.ps1 -BrowserChannel msedge
.\scripts\new-dev-log.ps1 -Slug '模块主题' -Author '开发者姓名'
```

无 Edge 的机器可在 frontend 安装 Playwright Chromium 后执行 `npm run test:e2e`。GitHub Actions 增加真实 PostgreSQL 17 与 Chromium 验收；结果见 [M1 开发日志](docs/dev-log/2026-10-08-farm-management.md)。软件测试不作为模型准确性证据。

PostgreSQL 配置、测试隔离和故障处理见 [运行手册](docs/runbooks/local-development.md)。当前没有生产备份、公开部署或权限隔离。

## 目录与 Git

```text
crop-digital-twin/
├─ frontend/src/features/farm/   # 页面组件、API 类型和局部状态
├─ backend/src/crop_twin/        # API、farm 领域、应用服务、SQL 适配
├─ backend/migrations/           # Alembic 增量迁移
├─ packages/crop_engine/         # 后续 PCSE、遥感和校准，尚无科学算法
├─ contracts/                   # 已实现接口的 OpenAPI
├─ docs/                        # 需求、架构、ADR、数据流和开发日志
├─ scripts/                     # 安装、迁移、启动、检查与契约导出
├─ infra/                       # 数据库 Compose 和未来运维配置
├─ frontend/tests/              # 单元和 Playwright 验收
└─ backend/tests/               # API、故障、双数据库集成与并发测试
```

详细语言与目录见 [目录说明](docs/directory-structure.md)。数据库、真实 .env、影像、依赖、运行输出和备份忽略版本控制。代码与日志同步至 [TensorJade/crop-digital-twin](https://github.com/TensorJade/crop-digital-twin)，本模块分支为 `codex/feature_farm_management_20261008`。协作约定见 [CONTRIBUTING.md](CONTRIBUTING.md)。

下一模块为账户与地块授权，之后接入水稻模型输入与 PCSE。原有 `..\wofost_lai_edge` 保持独立；复用前核对许可、参数来源和实测验证。
