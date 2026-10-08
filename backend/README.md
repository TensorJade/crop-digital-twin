# 后端（Python / FastAPI）

0.4.0 包含农田、账户和模拟输入三个业务模块。api/v1 校验 HTTP、会话、角色与 CSRF；application 编排事务内用例；domain 保存无框架的数据对象和规则；infrastructure 实现 SQL、Argon2id。输入的纯数值检查和单位转换调用独立 crop_engine，不在 API 运行作物模型。

组织由登录身份确定，所有资料/地块/季节/快照查询限定当前组织，跨组织返回 404。管理员和农田管理成员可导入并保存，只读成员可查看与导出。品种资料按组织共享，土壤和天气限定地块。列表只返回摘要，详情返回 JSON 内容；全部 26 个操作见真实 OpenAPI。

默认 SQLite，服务器可配置 PostgreSQL/Psycopg。先执行 scripts/init-db.ps1，已有用户不必重复初始化账号。每请求一个事务，业务与审计一起提交/回滚；SQLite BEGIN IMMEDIATE，PostgreSQL 用户/农田父对象行锁。输入版本在种植季锁内分配，SQL 唯一约束保护并发版本。

0003 追加 input_assets、simulation_inputs，资料与快照无更新/删除接口。缺测天气不补零，输入不完整也可保存带报告的快照；结构/单位错误拒绝保存。JSON/CSV 不执行，源引用不由服务器访问。

账户会话、登录限制、密码保护见 docs/modules/identity.md；输入数据流、日期/单位、来源与科学边界见 docs/modules/simulation-inputs.md。tests/integration 在临时 SQLite 或 UUID PostgreSQL schema 验证，服务端测试需 CROP_TWIN_TEST_POSTGRES_URL。worker 与模型执行尚未实现，production 保护留至 M7。
