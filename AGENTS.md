# 仓库协作约定

- 本仓库为实际开发代码；先读 README、docs/progress.md 和最近开发日志。
- 普通功能在开发者功能分支完成。不要擅自推送、合并保护分支、部署或变更全局工具设置。
- 将设计与已实现功能区分清楚。不得用演示数据证明模型精度或伪造真实遥感反射率。
- Python 使用 snake_case / PascalCase，TypeScript 使用 camelCase / PascalCase，SQL 使用 snake_case。依据见 docs/adr/0001-workspace-baseline.md。
- API 业务路由采用 GET/POST；修改接口后运行 scripts/export_openapi.py 并提交 contracts 中的变化。
- 原始影像、.env、密钥、个人数据、运行输出不得进入 Git。数据源和模型参数必须记录来源与授权。
- 作物算法置于 packages/crop_engine，API 路由不直接执行重计算。数据库、对象存储、消息队列的细节置于 infrastructure。
- 修改后运行相关检查；不要为仅目录或文档变化编写空测试。核心业务实现后以有意义的测试满足 80% 行覆盖率目标。
- 每次实际开发更新 docs/dev-log，并在 docs/progress.md 记录真实进度。失败和未验证事项也要写明。
- 同一农田业务集中于 domain/farm 和 frontend/src/features/farm；仅在实际边界引入抽象，不增加尚未使用的框架或中间件。
- M1 逻辑外键、事务锁和追加修订见 ADR 0002；M2 组织/角色、SQL 会话、同事务审计与旧数据接收见 ADR 0003，M3.1 输入只追加与校验边界见 ADR 0004，当前十张业务表已迁移。未来规划表不默认为已实现或批准。
- 所有农田查询必须限定当前组织，不能用客户端提交的组织 ID 授权；写操作同时检查角色/CSRF并追加同事务审计，跨组织资源返回 404。
- 不创建默认运行账号/密码。测试账号只允许在已验证的隔离数据库创建；旧地块不得自动归属第一个用户。
