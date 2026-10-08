# 后端（Python / FastAPI）

0.5.0提供农田、账户、模拟输入和潜在计算。api/v1负责HTTP/会话/角色/CSRF，application负责事务与用例，domain不依赖框架，infrastructure负责SQL/密码。crop_engine负责纯输入检查和独立模型；API不执行作物模型。

29个GET/POST操作见contracts/openapi。所有农田/输入/任务查询限定登录组织，跨组织404；管理员/农田管理成员可写，只读可查看导出。业务与审计同事务，SQLite写事务和PostgreSQL行锁保护并发，版本和幂等同时有唯一约束。

默认SQLite、服务器PostgreSQL，先scripts/init-db.ps1增量迁移至0004共11表。输入资料/快照只追加，JSON/CSV不执行，源引用不自动访问。新天气可声明Angstrom A/B，不猜测当地系数。input_ready和simulation_available为静态输入标记，不代表已运行或农艺验证。

POST simulation-runs仅校验/排队。独立scripts/start-worker.ps1短事务领取SQL租约，计算在限时隔离PCSE子进程；结果/错误/哈希和审计同事务保存。私有租约不出API，结果无编辑接口，旧任务不覆盖新结果。不引入Redis/Celery。

规则/数据流见docs/modules/{farm-management,identity,simulation-inputs,potential-simulation}.md。双数据库测试使用临时SQLite或UUID PostgreSQL schema；CROP_TWIN_TEST_POSTGRES_URL只供测试。潜在模式仅直播、出苗、已发生天气；水田管理、移栽/精度、联网天气和production/M7待验证。
