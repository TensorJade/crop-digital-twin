# 目录与模块语言

根目录：`D:\Dev\软著\crop-digital-twin`。同仓库统一追踪前后端、契约、工程文档和算法版本。

```text
backend/src/crop_twin/
├─ api/v1/                  # farm、identity、inputs、runs、weather、schemas、dependencies、health
├─ application/             # farm/identity/input/run service 与 repository Protocol
├─ domain/
│  ├─ farm/                 # 农田对象与规则
│  ├─ identity/             # 用户/组织/会话/角色/审计对象与规则
│  ├─ simulation/           # 输入资料/快照/计算对象
│  └─ pagination.py         # 共用分页，不反向依赖业务模块
├─ infrastructure/
│  ├─ database/             # SQL 模型、连接和四类存储适配
│  ├─ weather/              # 固定HTTPS、NASA小时转换、站点目录/缓存、来源校验
│  └─ passwords.py          # Argon2id 适配
├─ core/                    # settings.py
└─ workers/                 # simulation：SQL领取、租约和结果
backend/migrations/versions/ # 0001_farm_records、0002_identity、0003_simulation_inputs、0004_simulation_runs
backend/tests/{unit,integration}/
frontend/src/
├─ app/                     # App.vue 组合登录/工作区与会话失效处理
├─ pages/                   # FarmPage
├─ components/              # PageNavigation
├─ features/
│  ├─ farm/                 # 地块、种植季、农事组件及局部状态
│  ├─ simulation/           # 资料/计算/天气预览、站点候选、历史/曲线、文件与API
│  └─ identity/             # LoginPage、MembersPage、密码组件、类型、API、会话状态
├─ api/                     # 共用 HTTP、内存 CSRF、错误与分页
├─ maps/                    # 待接入
└─ styles/                  # main.css
frontend/tests/             # 单元、e2e 农田/账户/输入/实际计算流程
scripts/                    # PowerShell 入口 + Python 迁移/管理员/核验/检查
```

| 模块 | 路径 | 语言/格式 | 状态 |
|---|---|---|---|
| 农田、账户、输入/计算/天气页面 | frontend/src/pages、features | TypeScript、Vue SFC | M1/M2/M3.1–M3.3已实现 |
| 分页、HTTP、会话交互 | frontend/src/components、api、app | TypeScript、Vue SFC | 已实现，无 Router/Pinia |
| 响应式布局 | frontend/src/styles | CSS | 已实现 |
| API、认证入口与输入验证 | backend/src/crop_twin/api/v1 | Python | 31 个操作 |
| 用例与存储契约 | backend/src/crop_twin/application | Python | farm、identity、input、run分层 |
| 领域对象与规则 | backend/src/crop_twin/domain | Python | 无 HTTP/ORM 依赖 |
| SQL、密码与配置 | infrastructure、core | Python | SQLite/PostgreSQL、Argon2id |
| 数据迁移 | backend/migrations、alembic.ini | Python、SQL、INI | 四个增量迁移，11张业务表 |
| 输入检查与生长计算 | packages/crop_engine | Python | 静态检查、隔离 PCSE 潜在模型 |
| 天气获取/转换/站点目录 | backend/src/crop_twin/infrastructure/weather | Python标准库 | NASA历史网格/NOAA目录，保存来源与哈希 |
| 地图与后续外部适配 | maps、object_store、messaging | TypeScript / Python | 预留 |
| 接口契约 | contracts | JSON、YAML | 24条路径、31个GET/POST操作 |
| 后端测试 | backend/tests | Python | 单元/双数据库/迁移/并发 |
| 前端测试 | frontend/tests | TypeScript | 单元/浏览器 |
| 工具脚本 | scripts | PowerShell、Python | 安装、迁移、账户、启动、检查、导出及核验 |
| CI/服务配置 | .github/workflows、infra | YAML | PostgreSQL/Chromium CI、开发编排 |
| 工程文档 | docs | Markdown、SVG、JSON | 需求、架构、数据流、ADR、日志 |

空目录为后续模块预留。跟踪文件可用 git ls-files 查看，依赖、数据库、影像和输出放在忽略目录。

任务进程位于 backend/src/crop_twin/workers/simulation.py，算法子进程位于 packages/crop_engine/src/crop_engine/pcse_runner.py，均用 Python 编写。Windows 入口为 scripts/start-worker.ps1。数据流图使用 Mermaid，随模块文档维护。
