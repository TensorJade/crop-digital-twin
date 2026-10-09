# 作物数字孪生系统 · 华南水稻

本地开发路径：D:/Dev/软著/crop-digital-twin。Vue + TypeScript 前端、Python + FastAPI 后端，独立 Python 算法包复用 PCSE/WOFOST。

当前版本 **0.6.0** 支持账户登录、农田和农事管理、模拟资料导入、后台生长计算及逐日结果查看。天气可按地块坐标获取 NASA POWER 历史网格资料，也可通过 CSV 导入；原始响应、请求和哈希随资料保存。附近站点查询使用 NOAA 公开目录，观测数据尚未接入。

生长计算使用 PCSE 6.0.13 的 Wofost72_PP，支持直播出苗后的潜在生长，假定水肥充足。灌排和施肥效应、移栽水田及当地农艺验证仍需完成。卫星地图、无人机校准和发布运维按模块继续开发。

## 实施原则

- 一个模块化后端、一套前端，按农田、账户、输入/计算组织业务；接口、用例、领域、SQL 与算法分层。
- 默认本地 SQLite，服务器支持 PostgreSQL；一个 SQL 任务/结果表与独立 worker，无需 Redis/Celery。
- 组织内共享农田；管理员管理成员，农田管理成员可写，只读成员可查看与下载，后端强制组织/角色/CSRF 校验。
- 农事修正、输入和结果保留版本，业务与审计同事务；计算不占用 HTTP 或数据库写事务。
- 不提供猜测的华南品种参数或天气；合成资料仅供隔离的软件验收。

开发安排见 [模块计划](docs/module-roadmap.md)，当前状态见 [开发进度](docs/progress.md)和 [需求追踪](docs/requirements.md)。数据流和接口见 [输入模块](docs/modules/simulation-inputs.md)、[计算模块](docs/modules/potential-simulation.md)及 [天气模块](docs/modules/weather-sources.md)。原始方案保存在 docs/design-baseline。

## 安装与启动

| 项目 | 开发环境 |
|---|---|
| 操作系统 | Windows；CI 同时检查 Linux |
| 后端与算法 | Python 3.12、FastAPI、PCSE 6.0.13 |
| 前端 | Node.js 24.19.0、Vue、TypeScript、Vite |
| 数据库 | 本地 SQLite；服务器 PostgreSQL 17 |
| 脚本与版本管理 | PowerShell 5.1/7、Git |
| 网络 | 安装访问 PyPI/npm；天气获取访问 NASA/NOAA |

在仓库根目录执行以下命令：

~~~powershell
Set-Location 'D:/Dev/软著/crop-digital-twin'
./scripts/bootstrap.ps1
./scripts/init-db.ps1
./scripts/create-admin.ps1 -Username 'farm_admin' -DisplayName '管理员' -Organization '我的水稻农场'
~~~

初始化执行 Alembic 增量迁移，默认数据库为 runtime/crop_twin.db，不重置原数据。API/worker 启动不自动建表。管理员脚本交互输入两次 12–128 字符密码，不显示或写入命令行；已有组织/账号无需重复初始化。

**从 0.4.0 升级**：重新 bootstrap 安装锁定 PCSE 依赖，然后 init-db 至 0004。旧资料/快照保持不变；需由资料提供者补充天气 Angstrom A/B 系数，重新导入天气并保存新快照，才能运行计算。

**从 0.5.0 升级**：运行 bootstrap 同步版本，迁移仍为 0004，无新增外部依赖。天气在点击获取时联网，已有资料和快照保留。

**从 0.3.0 升级**：同样执行 bootstrap、init-db；导入有来源与许可的土壤/品种/天气，不创建默认模型参数。

**从 0.2.0 升级**：迁移保留旧地块。确需将全部未归属地块接收到新组织时，创建管理员命令显式增加 -AdoptLegacy；接收有审计，已有归属不转移。

若 Node 不在 PATH，npm 脚本可传 -NodeBinDirectory 'C:/path/to/node/bin'，路径保存在忽略的 .tools/local-settings.json，不修改全局配置。

分别在三个终端运行：

~~~powershell
./scripts/start-api.ps1
./scripts/start-frontend.ps1
./scripts/start-worker.ps1
~~~

前端 http://127.0.0.1:5173，API 文档 http://127.0.0.1:8000/docs；Vite 代理 /api。worker 与 API 使用相同数据库配置，缺少 worker 的任务会保持排队。一次性处理可用 start-worker.ps1 -Once。

## 计算需要什么

1. 本组织地块与水稻直播种植季，明确实际出苗日、已发生的截止日。
2. 农艺人员提供的完整 rice/WOFOST72 品种参数 JSON，声明来源、许可、品种和适用区域。
3. 土壤体积含水率与深度；连续逐日天气，可在“模拟资料→按农田位置获取天气”预览NASA POWER历史网格资料，或导入注明来源/位置/海拔/北京时间日界/2m风速的CSV。
4. 天气资料提供者填写 Angstrom A/B 系数（同时提供，不猜测默认值）。
5. “模拟资料”检查并保存快照；进入“生长计算”，选可运行快照，确认潜在模式后开始。

页面显示 LAI、发育进度、地上部/贮藏器官干物质，支持曲线、日期滑块、历史、逐日表和 JSON 下载。贮藏器官干物质不能直接当作实收稻谷产量。输入的 simulation_executed 始终为 false；真正完成计算的结果为 true，agronomically_validated 为 false。

联网天气每次获取 1–120 个已结束历史日，通常有数日发布延迟；缺少小时数据时拒绝保存。温度极值由小时值派生。附近站点显示距离和历史覆盖日期，暂不获取观测。数据源不可用时，可重试或导入已有 CSV，详细限制见 [天气模块](docs/modules/weather-sources.md)。

## 检查与维护

~~~powershell
./scripts/check.ps1
./scripts/check-e2e.ps1 -BrowserChannel msedge
./scripts/new-dev-log.ps1 -Slug 'farm-management' -Author '开发者姓名'
~~~

浏览器检查使用独立服务、临时数据库、测试账号和 worker，天气响应为合成测试资料。没有 Edge 时，可在 frontend 安装 Playwright Chromium 后运行 npm run test:e2e。GitHub Actions 使用 PostgreSQL 17、SQLite 和 Chromium。检查结果见 [M3.3 日志](docs/dev-log/2026-10-09-weather-sources.md)，农艺验证另见 [验证计划](docs/model-validation.md)。

运行升级、参数、排队故障与离线校验见 [运行手册](docs/runbooks/local-development.md)。脚本绑定回环地址，production 保护保留到 M7；备份恢复、公开部署与账号找回仍待交付。

## 目录与 Git

~~~text
crop-digital-twin/
├─ frontend/src/features/       # farm、identity、simulation：组件/类型/API/曲线
├─ backend/src/crop_twin/       # API、领域、应用、SQL、天气源与独立 worker
├─ backend/migrations/          # 0001 农田、0002 账户、0003 输入、0004 计算
├─ packages/crop_engine/        # 纯输入检查 + 隔离 PCSE 潜在模型
├─ contracts/                  # 31 个 GET/POST 操作的 OpenAPI
├─ docs/                       # 需求、架构、ADR、数据流和开发日志
├─ scripts/                    # 安装、迁移、账户、启动、worker 和检查
├─ infra/                      # 开发数据库与后续运维配置
├─ tests/fixtures/             # 自有合成资料，仅软件验收
├─ frontend/tests/             # 单元与 Playwright
└─ backend/tests/              # API、迁移、故障、双数据库与并发
~~~

详细语言与目录见 [目录说明](docs/directory-structure.md)，PCSE/天气数据源与许可见 [第三方清单](THIRD_PARTY.md)。数据库、.env、影像、依赖、输出和备份不进入 Git。当前功能分支 codex/feature_weather_20261009，代码与日志同步至 [TensorJade/crop-digital-twin](https://github.com/TensorJade/crop-digital-twin)；协作见 [CONTRIBUTING](CONTRIBUTING.md)。

后续工作包括授权站点观测、长季天气、移栽水田适配和当地实测验证，再接入卫星地图。相邻 wofost_lai_edge 独立维护，复用前检查实现和许可。历史提交说明见 [提交记录](docs/dev-log/commits.md)。
