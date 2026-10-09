# 后端（Python / FastAPI）

版本 0.6.0，提供农田、账户、模拟输入、潜在计算和天气获取。

| 目录 | 职责 |
|---|---|
| api/v1 | HTTP、会话、角色和 CSRF |
| application | 用例和事务 |
| domain | 对象和规则，无框架依赖 |
| infrastructure | SQL、密码库和天气源 |
| crop_engine | 输入检查和独立模型 |

API 负责提交任务，模型由 worker 在子进程中执行。

31个GET/POST操作见contracts/openapi。所有农田/输入/任务/天气查询限定登录组织，跨组织404；管理员/农田管理成员可写并触发获取，只读可查看已保存资料/导出。业务与审计同事务，SQLite写事务和PostgreSQL行锁保护并发，版本和幂等同时有唯一约束。

默认SQLite、服务器PostgreSQL，先scripts/init-db.ps1增量迁移至0004共11表。输入资料/快照只追加，JSON/CSV不执行，源引用不自动访问。新天气可声明Angstrom A/B，不猜测当地系数。input_ready和simulation_available为静态输入标记，不代表已运行或农艺验证。

POST simulation-runs仅校验/排队。独立scripts/start-worker.ps1短事务领取SQL租约，计算在限时隔离PCSE子进程；结果/错误/哈希和审计同事务保存。私有租约不出API，结果无编辑接口，旧任务不覆盖新结果。不引入Redis/Celery。

天气GET先短SQL认证/组织地块校验，再释放连接获取固定NASA/NOAA源，未保存候选不写业务/审计。NASA原始响应/请求/hash保留，保存API重新派生检查；目录24h缓存，无新表/迁移/依赖。实例构造不联网，测试通过 create_app 注入合成客户端，仅在临时库使用。

规则/数据流见docs/modules/{farm-management,identity,simulation-inputs,potential-simulation,weather-sources}.md。双数据库测试使用临时SQLite或UUID PostgreSQL schema；CROP_TWIN_TEST_POSTGRES_URL只供测试。潜在模式仅直播、出苗、已发生天气；水田管理、移栽/精度、授权站点观测和production/M7待验证。
