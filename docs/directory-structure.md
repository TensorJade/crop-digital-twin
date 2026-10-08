# 目录与模块语言

根目录：`D:\Dev\软著\crop-digital-twin`。同仓库统一追踪前后端、契约、工程文档和算法版本。

```text
backend/src/crop_twin/
├─ api/v1/                 # farm.py、farm_schemas.py、health.py
├─ application/            # farm_service.py、farm_repository.py
├─ domain/farm/            # models.py、rules.py
├─ infrastructure/database/# models.py、session.py、farm_repository.py
├─ core/                   # settings.py
└─ workers/                # 待接入
backend/migrations/versions/ # 0001_farm_records.py
backend/tests/{unit,integration}/
frontend/src/
├─ app/                    # App.vue、main.ts
├─ pages/                  # FarmPage.vue
├─ components/             # PageNavigation.vue
├─ features/farm/          # PlotPanel、SeasonPanel、ManagementPanel
│                          # api.ts、types.ts、useFarmWorkspace.ts
├─ api/                    # HTTP 与健康检查
├─ maps/                   # 待接入
└─ styles/                 # main.css
frontend/tests/            # *.test.ts、e2e/*.spec.ts
```

| 模块 | 路径 | 语言/格式 | 状态 |
|---|---|---|---|
| 农田页面与交互 | frontend/src/pages、features/farm | TypeScript、Vue SFC | M1 已实现 |
| 分页与 HTTP | frontend/src/components、api | TypeScript、Vue SFC | 已实现 |
| 响应式布局 | frontend/src/styles | CSS | 已实现 |
| API 与输入验证 | backend/src/crop_twin/api/v1 | Python | M1 和存活接口 |
| 用例与存储契约 | backend/src/crop_twin/application | Python | 已实现 |
| 领域对象与规则 | backend/src/crop_twin/domain/farm | Python | 已实现，无 HTTP/ORM 依赖 |
| SQL 与配置 | backend/src/crop_twin/infrastructure/database、core | Python | SQLite/PostgreSQL 共用 |
| 数据迁移 | backend/migrations、alembic.ini | Python、SQL、INI | 首个迁移 |
| 科学计算 | packages/crop_engine | Python | 仅包边界 |
| 地图与外部适配 | maps、weather、object_store、messaging、workers | TypeScript / Python | 预留 |
| 接口契约 | contracts | JSON、YAML | 10 个真实操作 |
| 后端测试 | backend/tests | Python | 单元/双数据库集成 |
| 前端测试 | frontend/tests | TypeScript | 单元/浏览器 |
| 工具脚本 | scripts | PowerShell、Python | 安装、迁移、启动、检查、导出 |
| CI/服务配置 | .github/workflows、infra | YAML | 开发检查/数据库编排 |
| 工程文档 | docs | Markdown、SVG、JSON | 需求、架构、ADR、日志 |

保留空目录表示待实施位置，不代表实现。完整版本化文件以 git ls-files 为准；依赖、数据库、影像和输出不在其中。
