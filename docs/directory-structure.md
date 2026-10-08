# 目录与模块语言

根目录：`D:\Dev\软著\crop-digital-twin`。同仓库统一追踪前后端、契约、工程文档和算法版本。

```text
backend/src/crop_twin/
├─ api/v1/                  # farm、identity、schemas、dependencies、health
├─ application/             # farm/identity service 与 repository Protocol
├─ domain/
│  ├─ farm/                 # 农田对象与规则
│  ├─ identity/             # 用户/组织/会话/角色/审计对象与规则
│  └─ pagination.py         # 共用分页，不反向依赖业务模块
├─ infrastructure/
│  ├─ database/             # SQL 模型、连接和两种模块存储适配
│  └─ passwords.py          # Argon2id 适配
├─ core/                    # settings.py
└─ workers/                 # 待接入
backend/migrations/versions/ # 0001_farm_records、0002_identity
backend/tests/{unit,integration}/
frontend/src/
├─ app/                     # App.vue 组合登录/工作区与会话失效处理
├─ pages/                   # FarmPage
├─ components/              # PageNavigation
├─ features/
│  ├─ farm/                 # 地块、种植季、农事组件及局部状态
│  └─ identity/             # LoginPage、MembersPage、密码组件、类型、API、会话状态
├─ api/                     # 共用 HTTP、内存 CSRF、错误与分页
├─ maps/                    # 待接入
└─ styles/                  # main.css
frontend/tests/             # 单元、e2e 农田与账户流程
scripts/                    # PowerShell 入口 + Python 迁移/管理员/检查
```

| 模块 | 路径 | 语言/格式 | 状态 |
|---|---|---|---|
| 农田与账户页面 | frontend/src/pages、features | TypeScript、Vue SFC | M1/M2 已实现 |
| 分页、HTTP、会话交互 | frontend/src/components、api、app | TypeScript、Vue SFC | 已实现，无 Router/Pinia |
| 响应式布局 | frontend/src/styles | CSS | 已实现 |
| API、认证入口与输入验证 | backend/src/crop_twin/api/v1 | Python | 19 个真实操作 |
| 用例与存储契约 | backend/src/crop_twin/application | Python | farm、identity 分层 |
| 领域对象与规则 | backend/src/crop_twin/domain | Python | 无 HTTP/ORM 依赖 |
| SQL、密码与配置 | infrastructure、core | Python | SQLite/PostgreSQL、Argon2id |
| 数据迁移 | backend/migrations、alembic.ini | Python、SQL、INI | 两个增量迁移，八张业务表 |
| 科学计算 | packages/crop_engine | Python | 仅包边界 |
| 地图与外部适配 | maps、weather、object_store、messaging、workers | TypeScript / Python | 预留 |
| 接口契约 | contracts | JSON、YAML | 15 条路径、19 个 GET/POST 操作 |
| 后端测试 | backend/tests | Python | 单元/双数据库/迁移/并发 |
| 前端测试 | frontend/tests | TypeScript | 单元/浏览器 |
| 工具脚本 | scripts | PowerShell、Python | 安装、迁移、交互建管理员、启动、检查、导出 |
| CI/服务配置 | .github/workflows、infra | YAML | PostgreSQL/Chromium CI、开发编排 |
| 工程文档 | docs | Markdown、SVG、JSON | 需求、架构、数据流、ADR、日志 |

保留空目录表示待实施位置，不代表实现。完整版本化文件以 git ls-files 为准；依赖、数据库、影像和输出不在其中。
