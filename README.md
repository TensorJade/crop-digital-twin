# 作物数字孪生系统 · 华南水稻

本地开发路径：`D:\Dev\软著\crop-digital-twin`。前端使用 Vue + TypeScript，后端使用 Python + FastAPI，科学计算保留独立的 PCSE/WOFOST 适配包。

当前版本 **0.3.0** 已完成 M1 农田管理与 M2 账户授权：登录后按“选地块 → 选种植季 → 记农事”操作，支持成员管理、组织隔离、角色权限和操作审计。页面支持桌面与手机。生长模拟、天气、卫星地图和无人机校准仍在后续模块中；公开发布还需 M7 验收。

## 实施原则

- 一个模块化后端、一套前端。农田与账户各自集中业务，HTTP、业务规则和 SQL 分层。
- 默认本地 SQLite，服务器目标 PostgreSQL；Redis 等异步计算需要时再接入。
- 组织内共享地块。管理员管理成员，农田管理成员可写，只读成员仅查看；跨组织资源不可访问。
- 修正农事新增版本；操作与审计同事务，失败一起回滚。
- 已确认首版为华南水稻，尚无具体试点县市、模型品种参数或农艺精度结论。

见 [模块路线](docs/module-roadmap.md)、[实际进度](docs/progress.md)、[需求追踪](docs/requirements.md)、[M1 数据流](docs/modules/farm-management.md)和 [M2 数据流](docs/modules/identity.md)。`docs/design-baseline/` 中的完整目标不代表已实现能力。

## 安装与启动

使用 Python 3.12、Node.js 24.19.0、Git。脚本支持 Windows PowerShell 5.1 和 PowerShell 7，安装访问 PyPI/npm。

```powershell
Set-Location 'D:\Dev\软著\crop-digital-twin'
.\scripts\bootstrap.ps1
.\scripts\init-db.ps1
.\scripts\create-admin.ps1 -Username 'farm_admin' -DisplayName '管理员' -Organization '我的水稻农场'
```

初始化运行 Alembic 增量迁移，默认数据库为 `runtime/crop_twin.db`，无需 Docker/Redis。API 启动不自动建表。管理员脚本交互输入两次 12–128 字符的密码，不显示密码；没有默认账号或密码，不把密码写入命令行。

**从 0.2.0 升级**：先执行 init-db。旧地块原样保存但不会自动授权；确需将全部未归属旧地块接收到新组织时，创建管理员命令显式增加 `-AdoptLegacy`。脚本会记录接收审计，已有归属不转移。已有组织的管理员不需要重复创建。

若合适的 Node 不在 PATH，可向 npm 相关脚本传入 `-NodeBinDirectory 'C:\path\to\node\bin'`。本机路径存于忽略的 `.tools/local-settings.json`，不修改全局配置。

分别在两个终端运行：

```powershell
.\scripts\start-api.ps1
.\scripts\start-frontend.ps1
```

前端：`http://127.0.0.1:5173`；API 文档：`http://127.0.0.1:8000/docs`。Vite 将 /api 代理到本机 API。登录后录入；管理员可在“成员与记录”创建农田管理或只读账号。所有成员可改自己的密码，修改后须重新登录。

启动脚本绑定回环地址；production 模式在 M7 部署验收前继续拒绝启动。账户功能不代表完整生产发布完成。

## 检查与维护

```powershell
.\scripts\check.ps1
# 本机 Edge：独立服务、临时数据库和测试账号，均不使用运行数据库
.\scripts\check-e2e.ps1 -BrowserChannel msedge
.\scripts\new-dev-log.ps1 -Slug '模块主题' -Author '开发者姓名'
```

无 Edge 的机器可在 frontend 安装 Playwright Chromium 后执行 `npm run test:e2e`。GitHub Actions 使用真实 PostgreSQL 17 与 Chromium；验证结果见 [M1 日志](docs/dev-log/2026-10-08-farm-management.md)和 [M2 日志](docs/dev-log/2026-10-08-identity.md)。软件测试不作为模型准确性证据。

PostgreSQL 配置、测试隔离与账户故障处理见 [运行手册](docs/runbooks/local-development.md)。生产备份、账号找回、逐成员地块授权和公开部署尚未交付。

## 目录与 Git

```text
crop-digital-twin/
├─ frontend/src/features/       # farm、identity：组件、类型、API 与局部状态
├─ backend/src/crop_twin/        # API、领域、应用服务与存储/密码适配
├─ backend/migrations/           # 0001 农田、0002 账户与归属
├─ packages/crop_engine/         # 后续 PCSE、遥感和校准，尚无科学算法
├─ contracts/                   # 19 个真实 GET/POST 操作的 OpenAPI
├─ docs/                        # 需求、架构、ADR、数据流和开发日志
├─ scripts/                     # 安装、迁移、管理员初始化、启动与检查
├─ infra/                       # 数据库 Compose 和未来运维配置
├─ frontend/tests/              # 单元和 Playwright 验收
└─ backend/tests/               # API、迁移、故障、双数据库与并发测试
```

详细语言与目录见 [目录说明](docs/directory-structure.md)。数据库、真实 .env、影像、依赖、运行输出和备份忽略版本控制。代码与日志同步至 [TensorJade/crop-digital-twin](https://github.com/TensorJade/crop-digital-twin)，本模块分支为 `codex/feature_identity_20261008`。协作约定见 [CONTRIBUTING.md](CONTRIBUTING.md)。

下一模块为 M3 水稻模拟输入与 PCSE 适配。原有 `..\wofost_lai_edge` 保持独立；复用前核对许可、参数来源、水田过程和实测验证。
