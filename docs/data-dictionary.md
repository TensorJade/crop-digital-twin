# 数据字典与实际迁移

总体目标包含 [20 张规划表](design-baseline/数据字典设计.json)与 [ER 图](diagrams/er_global.svg)。实际版本以 Alembic 0001、0002 与 ORM 为准，M1/M2 共八张业务表；规划图中的未来表尚未实施。

| 表 | 主键与逻辑关系 | 主要事实 | 约束/索引 |
|---|---|---|---|
| plots | id UUID、organization_id UUID | name、area_mu Numeric(16,6)、latitude/longitude Float、created_at | 面积/坐标范围；组织索引、创建时间分页；旧数据组织字段暂可空 |
| seasons | id UUID、plot_id UUID | start_date/end_date、establishment_method、variety_name、created_at | 日期/方式检查；地块/日期；每地块一开放季 |
| management_events | id UUID、season_id、replaces_event_id UUID | 类型/日期、原始/标准数量单位、肥料名称、备注、创建时间、修订号/原因 | 数量/版本检查；季节/日期；替代指针唯一 |
| organizations | id UUID | name String(100)、created_at | 组织 ID 确定隔离范围，名称不作为身份 |
| users | id UUID、organization_id UUID | username String(64)、display_name String(80)、role String(16)、is_active Boolean、password_hash String(255)、created_at | 小写规范用户名全局唯一；角色 owner/operator/viewer；组织/时间/ID 分页索引 |
| user_sessions | id UUID、user_id UUID | token_digest String(64)、csrf_token String(64)、created_at、expires_at | 令牌摘要唯一；用户/过期索引；到期晚于创建；固定 8 小时 |
| login_limits | id UUID | source_key String(64)、failures Integer、window_start | 直接来源摘要唯一；0–5 次失败；15 分钟窗口 |
| audit_events | id UUID、organization_id、actor_user_id、entity_id UUID | action String(64)、entity_type String(32)、created_at | 组织/时间/ID 分页索引；与业务同事务追加 |

数据库关系使用应用维护的逻辑外键。组织范围沿 plot → season → management_event 检查；新地块必须由服务端赋当前组织，客户端不能指定归属。0002 不篡改旧地块内容；只有明确初始化接收才补组织并写审计。账号停用/密码修改会删除相应会话。审计展示的 actor_display_name 由本组织用户查询关联得到，不复制入审计表。

密码只存 Argon2id 哈希，随机会话令牌只在 HttpOnly Cookie 中携带，SQL 保存 SHA-256 摘要。CSRF 值绑定会话，用于校验请求，不作为登录凭证。登录限制不存原始 IP/用户名/密码。审计不存密码、会话凭证、请求体或备注正文。

保存原始亩数，响应派生公顷。标准水量为 mm、肥料产品质量为 kg/ha，不是入渗水或纯氮量。Decimal 响应为字符串，日期为 ISO。时间写入 UTC，SQLite 读回补 UTC。

事务与锁见 [ADR 0002](adr/0002-farm-module.md)和 [ADR 0003](adr/0003-identity.md)。无业务物理删除接口；绕过应用的 SQL 仍可能破坏关系，需限制运维写权限。农事 is_current 由后继关系派生，原始农事不更新；crop_code=rice 为模块常量。双数据库集成测试执行 Alembic check 检查迁移与 ORM 一致。
