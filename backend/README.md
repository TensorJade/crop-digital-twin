# 后端（Python / FastAPI）

0.3.0 实现农田与账户两个模块。api/v1 校验 HTTP、会话和 CSRF；application 编排用例；domain/farm、domain/identity 保持业务规则；infrastructure 实现 SQL 和 Argon2id。服务只依赖真实存储/密码 Protocol，不依赖 FastAPI/SQLAlchemy。

组织是农田查询边界；管理员、农田管理成员、只读成员权限在后端检查，不能只依赖页面隐藏按钮。跨组织 ID 返回 404。成员与审计列表仅管理员可读。详见 docs/modules/identity.md 与真实 OpenAPI。

默认 SQLite，可配置 PostgreSQL/Psycopg。先运行 scripts/init-db.ps1，再交互执行 create-admin.ps1；不自动建表或建立默认账号。每请求一个事务，提交后返回成功，失败回滚；SQLite BEGIN IMMEDIATE，PostgreSQL 用户/农田父对象行锁。登录失败计数独立完成事务后再返回 401/429。

Cookie 会话固定 8 小时，SQL 保存摘要；退出、停用和改密码撤销会话。业务与审计同事务。422 错误移除原始输入，防止密码回显。密码和会话不进日志。

tests/integration 使用临时 SQLite 或 UUID PostgreSQL schema，验证权限、真实持久化、并发、旧版本升级与审计失败回滚；服务器测试通过 CROP_TWIN_TEST_POSTGRES_URL 显式启用。worker、模型未实现；production 启动保留到 M7 部署验收。
