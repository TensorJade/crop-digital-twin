# 作物数字孪生系统 · 开发仓库

本地路径：`D:\Dev\软著\crop-digital-twin`。项目使用 Vue + TypeScript 前端、Python + FastAPI 后端，预留独立的 PCSE/WOFOST 适配与无人机遥感处理模块。

当前版本 `0.1.0` 是可运行的开发骨架：前端开发首页、API 存活检查、接口文档、检查脚本和 Git 基线。地块管理、作物生长模拟、天气接入、卫星底图、影像处理及数据库持久化均未实现。`docs/design-baseline/` 中的方案是设计依据，不代表已上线能力。

## 目录与职责

```text
crop-digital-twin/
├─ frontend/              # Vue、TypeScript；页面、地图、农事、影像、长势
├─ backend/               # Python、FastAPI；API、业务用例、领域、基础设施
├─ packages/crop_engine/  # Python；未来的 PCSE 适配、质控、反演和校准
├─ contracts/             # 已实现 OpenAPI 与未来数据契约
├─ model-assets/          # 小型模型配置、参数来源和授权清单
├─ docs/                  # 需求、架构、ADR、运行手册、开发日志
├─ tests/e2e/             # 未来跨前后端、数据库的业务验收测试
├─ infra/                 # Compose、容器、代理、监控、备份
├─ scripts/               # 安装、启动、检查、接口导出和日志工具
├─ .github/               # CI 配置及 PR 模板
├─ data/                  # 本地数据，忽略版本控制
├─ runtime/               # 运行日志和缓存，忽略版本控制
└─ backups/               # 本地备份，忽略版本控制
```

详细说明见 [目录与模块语言](docs/directory-structure.md)、[实际进度](docs/progress.md)、[开发日志](docs/dev-log/README.md)。

## 首次安装（Windows PowerShell）

基线环境：Python 3.12、Node.js 24.19.0、Git。脚本支持 Windows PowerShell 5.1 及 PowerShell 7。Node 环境要求记录在 `.node-version` / `.nvmrc` / `frontend/package.json`。安装时会访问 PyPI 和 npm；数据库、天气和地图服务不会自动连接。

```powershell
Set-Location 'D:\Dev\软著\crop-digital-twin'
.\scripts\bootstrap.ps1
```

若合适版本的 Node 不在 PATH，可仅对当前命令指定目录：

```powershell
.\scripts\bootstrap.ps1 -NodeBinDirectory 'C:\path\to\node\bin'
```

工具安装到忽略的 `.tools/uv/`，项目 Python 环境为 `.venv/`。`uv.lock`、`frontend/package-lock.json` 一并提交；后续安装使用锁文件，不修改系统 Python 或全局 Node 配置。

本机默认 Node 为 24.11.1。本次已在忽略的 `.tools/local-settings.json` 中记录本机可用的 Node 24.19.0 目录，所以下方脚本可直接运行。其他机器使用自己的 PATH，或传入 `-NodeBinDirectory`；本机路径不会进入 Git。

## 启动与检查

分别打开两个终端运行：

```powershell
.\scripts\start-api.ps1
.\scripts\start-frontend.ps1
```

前端：`http://127.0.0.1:5173`。后端：`http://127.0.0.1:8000/docs`。点击前端“检查后端连接”可验证 `/api/v1/health`。Vite 代理将 `/api` 转发到本地后端。该接口只证明 API 进程运行，不证明数据库、模型或外部服务可用。

```powershell
.\scripts\check.ps1
.\scripts\new-dev-log.ps1 -Slug 'plot-management' -Author '开发者姓名'
```

可向涉及 npm 的脚本传入同样的 `-NodeBinDirectory` 参数。启动脚本绑定回环地址；正式部署另行设计。若脚本被本机执行策略阻止，可在当前终端运行 `Set-ExecutionPolicy -Scope Process Bypass`，只影响该终端。

## 数据与 Git

- PostgreSQL/PostGIS 计划保存业务、空间与版本数据；Redis 计划保存缓存及任务协调状态；影像存放对象存储。当前只有开发数据库 Compose 配置，API 尚未接入。
- `.env.example` 仅为配置模板。运行数据库前复制为 `.env` 并修改本地密码；`.env`、原始影像、备份、日志和依赖目录不提交。
- 远程 `origin`：[TensorJade/crop-digital-twin](https://github.com/TensorJade/crop-digital-twin)。代码与开发日志已首次推送至 `codex/feature_scaffold_20261008`，并设置上游跟踪。工作流见 [CONTRIBUTING.md](CONTRIBUTING.md)；同步记录见 [GitHub 同步日志](docs/dev-log/2026-10-08-github-sync.md)。GitHub Actions 已触发，具体运行结论以对应提交的检查页面为准。
- 原有 `..\wofost_lai_edge` 保持独立。后续复用需检查许可证、参数来源及农艺验证结果，不能将演示曲线当成成熟作物模型。

下一步先完成地块、种植季、管理事件与持久化，再实现可复现的 PCSE 适配，最后接入地图和遥感校准。验收条件见 [requirements.md](docs/requirements.md)。
