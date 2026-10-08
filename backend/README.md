# 后端（Python / FastAPI）

0.2.0 实现本地农田管理。api/v1 校验 HTTP，application 编排用例，domain/farm 保存纯规则，infrastructure/database 实现 SQL。FarmService 仅依赖一个存储 Protocol，不依赖 FastAPI/SQLAlchemy。

已实现地块、种植季和农事的查询/创建，以及结束季节和追加农事修订。接口见 docs/modules/farm-management.md、/docs 和 contracts。存活接口不表示数据库就绪。

默认 SQLite，可配置 PostgreSQL/Psycopg。先运行 scripts/init-db.ps1 显式迁移，再启动；API 不自行建表。每请求一个事务，提交后返回成功，失败回滚；SQLite BEGIN IMMEDIATE，PostgreSQL 父对象行锁。

tests/integration 使用临时 SQLite 或 UUID 命名的 PostgreSQL schema，验证实际存储、并发、日期、单位和历史；服务器测试通过 CROP_TWIN_TEST_POSTGRES_URL 显式启用。

账户、worker、模型未实现；production 模式拒绝启动。公开服务前完成 M2 与 HTTPS。
