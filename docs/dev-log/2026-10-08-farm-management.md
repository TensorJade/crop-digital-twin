# 2026-10-08 · farm-management

- 记录人：Codex
- 日期与时区：2026-10-08，Asia/Shanghai；本地完整检查于 14:32 完成，配置调整后类型与单元复核于 14:39 完成。
- 分支：codex/feature_farm_management_20261008
- 关联任务：M1；F02/F05/F12 的农田记录部分
- 状态：业务代码、本地验收和文档完成；提交后验证远程 PostgreSQL/Chromium CI。
- 用户补充：首版华南水稻；具体县市和品种参数尚未确定。

## 目标与实际交付

按奥卡姆剃刀与高内聚低耦合实现第一个可操作模块：地块 → 水稻种植季 → 农事 → 追加修正与查询 → 结束季节。没有重写作物模型，也没有引入尚未使用的 Redis/GIS/全局状态库。

1. 后端 domain/farm 集中对象、日期和水肥单位规则；application 的一个 FarmService 编排用例，一个存储 Protocol 隔离 SQL；api/v1 仅做 HTTP 适配。
2. SQLAlchemy 适配 SQLite/PostgreSQL，Alembic 0001 迁移建立 plots/seasons/management_events。保存原始亩数与原始操作量，读取派生公顷、保留标准量及修订关系。
3. 同一请求内检查引用并提交事务。SQLite BEGIN IMMEDIATE，PostgreSQL 父对象行锁；开放季与修订后继唯一索引提供附加约束。
4. Vue features/farm 内聚三类表单与局部状态。亩等常用单位、失败重试、历史开关、手机布局；请求代次避免旧响应污染新选择。
5. 9 个业务操作与存活接口导出到 contracts/openapi.*。分页有上限，安全错误为中文消息；无授权时拒绝 production 启动。
6. scripts 增加初始化和浏览器验收入口；CI 增加 PostgreSQL 17 临时服务及 Chromium。根目录、模块、需求、数据字典、运行手册和进度与实际代码同步。

环境：Windows，Python 3.12.6，Node 24.19.0，npm 11.17.0，uv 0.12.23。新增依赖锁定 SQLAlchemy 2.1.4、Alembic 1.20.0、Psycopg 3.3.6；Playwright 1.64.0、Node 类型由 npm 锁文件固定。科学包仍只有边界。

## 验证证据

| 检查 | 实际结果 | 范围/限制 |
|---|---|---|
| scripts/init-db.ps1 | 默认 SQLite 已增量建表 | API 启动不隐式迁移；无重置 |
| Ruff、mypy | 通过；mypy 26 个源文件 | Python 后端和工具静态检查 |
| pytest --cov=crop_twin --cov-fail-under=80 | 26 passed / 22 skipped，97.90% | SQLite 集成及单元；PostgreSQL 本机无服务而跳过 |
| Alembic check | 通过，无新增迁移差异 | 迁移与 ORM 类型/索引一致性 |
| Vue 类型、ESLint、Prettier、Vitest | 通过；9 个单元测试 | API 客户端与前端代码 |
| Vite build | 成功 | 页面可构建，不代表生产部署完成 |
| scripts/check-e2e.ps1 -BrowserChannel msedge | 4 passed | 真实 UI→代理→API→临时 SQLite，含重试与延迟响应 |
| 桌面/390px 手机截图 | 已查看，布局正常、无横向溢出 | 测试记录；runtime/farm-desktop.png、farm-mobile.png 不入 Git |
| OpenAPI 导出检查 | 7 条路径、10 个操作一致 | 仅真实已实现 API |
| PostgreSQL/Chromium GitHub CI | 待本模块推送后核对 | CI 结果在后续同步记录补充 |

集成测试实际检查输入拒绝及回滚、季节含边界冲突、水肥换算、修订不覆盖、过时修订冲突、并发创建/修订、结束日期和重启后读取。测试 PostgreSQL 只使用独立 UUID schema；浏览器使用临时数据库，不写运行数据库。

## 问题与处理

- ORM 的 float 自动类型与迁移 Float 不一致，被 Alembic check 检出；已显式声明 Float。
- 内联 Vue 多语句点击处理被格式化后产生构建错误；改为命名函数，重新构建成功。
- 浏览器测试的 select 标签定位和多 status 匹配出现失败；改用精确控件角色与提示筛选，最终四条通过。
- 重试种植季时地块选择不变未重新请求；已修复，并增加独立浏览器回归验证。
- 测试配置缺少 Node 类型与导入扩展名提示；增加匹配的类型及 tsconfig 设置，类型/单元复核通过。

## 限制与下一步

本机 Docker daemon 未运行，未启动 PostgreSQL/PostGIS。CI 验证关系型读写；空间功能与部署容量不在 M1。当前无账户授权、地图、天气、PCSE、无人机处理、模型校准或备份恢复。SQL 逻辑引用方案见 ADR 0002；绕过应用写入可能破坏关系，后续运维需限制写权限。

水量换算是施用水量，肥料换算是产品质量，不能直接称作土壤入渗水或纯氮。华南水稻模型还需品种参数、天气/土壤来源和独立实测验证。

下一模块 M2 账户与地块授权，之后 M3 模拟输入与模型适配；各模块分别交付与验证。

## Git

从本地 release_20261008 创建本功能分支，快进引入已推送骨架的同步文档。仅提交本模块及日志，推送同名功能分支；不合并保护基线或部署。实际提交哈希与 CI 链接在后续同步记录补充。
