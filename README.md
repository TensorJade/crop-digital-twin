# 作物数字孪生系统 · 华南水稻

本地开发路径：D:/Dev/软著/crop-digital-twin。Vue + TypeScript 前端、Python + FastAPI 后端，独立 Python 算法包复用 PCSE/WOFOST。

当前版本 **0.6.0** 可完成登录 → 农田/种植季/农事 → 导入土壤/品种、按位置获取历史网格天气或导入CSV → 保存输入快照 → 排队计算 → 查看逐日长势、历史和下载。天气保留原始小时响应、请求与哈希，支持附近真实站点目录候选。真实 PCSE6.0.13 Wofost72_PP 已接入，支持直播出苗后的潜在生产计算，假定水肥充足；灌排、施肥效应、移栽水田适配和当地精度尚未验证。授权站点观测、卫星地图、无人机校准与公开发布按模块继续实施。

## 实施原则

- 一个模块化后端、一套前端，按农田、账户、输入/计算组织业务；接口、用例、领域、SQL 与算法分层。
- 默认本地 SQLite，服务器支持 PostgreSQL；一个 SQL 任务/结果表与独立 worker，无需 Redis/Celery。
- 组织内共享农田；管理员管理成员，农田管理成员可写，只读成员可查看与下载，后端强制组织/角色/CSRF 校验。
- 农事修正、输入和结果保留版本，业务与审计同事务；计算不占用 HTTP 或数据库写事务。
- 不提供猜测的华南品种参数或天气；合成资料仅供隔离的软件验收。

见 [模块路线](docs/module-roadmap.md)、[实际进度](docs/progress.md)、[需求追踪](docs/requirements.md)、[输入数据流](docs/modules/simulation-inputs.md)、[计算数据流](docs/modules/potential-simulation.md)和[天气数据流](docs/modules/weather-sources.md)。docs/design-baseline 中的完整目标不代表已实现能力。

## 安装与启动

使用 Python 3.12、Node.js 24.19.0、Git。脚本支持 Windows PowerShell 5.1/7，安装需访问 PyPI/npm。

~~~powershell
Set-Location 'D:/Dev/软著/crop-digital-twin'
./scripts/bootstrap.ps1
./scripts/init-db.ps1
./scripts/create-admin.ps1 -Username 'farm_admin' -DisplayName '管理员' -Organization '我的水稻农场'
~~~

初始化执行 Alembic 增量迁移，默认数据库为 runtime/crop_twin.db，不重置原数据。API/worker 启动不自动建表。管理员脚本交互输入两次 12–128 字符密码，不显示或写入命令行；已有组织/账号无需重复初始化。

**从 0.4.0 升级**：重新 bootstrap 安装锁定 PCSE 依赖，然后 init-db 至 0004。旧资料/快照保持不变；需由资料提供者补充天气 Angstrom A/B 系数，重新导入天气并保存新快照，才能运行计算。

**从 0.5.0 升级**：bootstrap同步工作区版本即可，迁移仍为0004，无新增外部依赖。天气获取仅在页面点击时联网；旧资料/快照不改写。

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

联网天气每次1–120个已结束历史日，资料通常延迟数日，缺小时不补零；温度极值由小时值派生。附近站点仅为NOAA历史目录中的位置候选，显示距离/覆盖日期，观测尚未接入。A/B仍需来源提供者填写。源不可用时可重试或导入已有CSV，完整边界见[天气模块](docs/modules/weather-sources.md)。

## 检查与维护

~~~powershell
./scripts/check.ps1
./scripts/check-e2e.ps1 -BrowserChannel msedge
./scripts/new-dev-log.ps1 -Slug '模块主题' -Author '开发者姓名'
~~~

浏览器验收使用独立服务、临时数据库、测试账号和真实 worker；天气响应为明确标记的合成验收资料，不使用运行数据库或公网源。无 Edge 可在 frontend 安装 Playwright Chromium 后 npm run test:e2e。GitHub Actions 验证 PostgreSQL17/SQLite 和 Chromium。检查结果见 [M3.3 日志](docs/dev-log/2026-10-09-weather-sources.md)，软件测试不作为模型精度证据。

运行升级、参数、排队故障与离线校验见 [运行手册](docs/runbooks/local-development.md)。脚本绑定回环地址，production 保护保留到 M7；备份恢复、公开部署与账号找回仍待交付。

## 目录与 Git

~~~text
crop-digital-twin/
├─ frontend/src/features/       # farm、identity、simulation：组件/类型/API/曲线
├─ backend/src/crop_twin/       # API、领域、应用、SQL、天气源与独立 worker
├─ backend/migrations/          # 0001 农田、0002 账户、0003 输入、0004 计算
├─ packages/crop_engine/        # 纯输入检查 + 隔离 PCSE 潜在模型
├─ contracts/                  # 31 个真实 GET/POST 操作的 OpenAPI
├─ docs/                       # 需求、架构、ADR、数据流和实际开发日志
├─ scripts/                    # 安装、迁移、账户、启动、worker 和检查
├─ infra/                      # 开发数据库与后续运维配置
├─ tests/fixtures/             # 自有合成资料，仅软件验收
├─ frontend/tests/             # 单元与 Playwright
└─ backend/tests/              # API、迁移、故障、双数据库与并发
~~~

详细语言与目录见 [目录说明](docs/directory-structure.md)，PCSE/天气数据源与许可见 [第三方清单](THIRD_PARTY.md)。数据库、.env、影像、依赖、输出和备份不进入 Git。当前功能分支 codex/feature_weather_20261009，代码与日志同步至 [TensorJade/crop-digital-twin](https://github.com/TensorJade/crop-digital-twin)；协作见 [CONTRIBUTING](CONTRIBUTING.md)。

下一步补充授权站点观测、长季天气、移栽水田条件与当地实测验证，并按模块接入卫星地图。相邻 wofost_lai_edge 保持独立，复用前核对来源、许可和真实能力。
