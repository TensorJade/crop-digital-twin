# 数据字典与实际迁移

当前有 11 张业务表，字段和约束以 Alembic 0001–0004 及 ORM 为准。原方案的 [20 张规划表](design-baseline/数据字典设计.json)和 [ER 图](diagrams/er_global.svg)用于后续设计。

| 表 | 用途 | 迁移 |
|---|---|---|
| plots | 地块 | 0001 |
| seasons | 种植季 | 0001 |
| management_events | 农事及修订 | 0001 |
| organizations | 组织 | 0002 |
| users | 账户和角色 | 0002 |
| user_sessions | 可撤销会话 | 0002 |
| login_limits | 登录失败限制 | 0002 |
| audit_events | 操作审计 | 0002 |
| input_assets | 输入资料 | 0003 |
| simulation_inputs | 输入快照 | 0003 |
| simulation_runs | 计算任务和结果 | 0004 |

## 字段与约束

### plots

主键及关系：id UUID、organization_id UUID。

字段：name、area_mu Numeric(16,6)、latitude/longitude Float、created_at。

约束及索引：面积/坐标范围；组织索引、创建时间分页；旧数据组织字段暂可空。

### seasons

主键及关系：id UUID、plot_id UUID。

字段：start_date/end_date、establishment_method、variety_name、created_at。

约束及索引：日期/方式检查；地块/日期；每地块一开放季。

### management_events

主键及关系：id UUID、season_id、replaces_event_id UUID。

字段：类型/日期、原始/标准数量单位、肥料名称、备注、创建时间、修订号/原因。

约束及索引：数量/版本检查；季节/日期；替代指针唯一。

### organizations

主键及关系：id UUID。

字段：name String(100)、created_at。

约束及索引：组织 ID 确定隔离范围，名称不作为身份。

### users

主键及关系：id UUID、organization_id UUID。

字段：username String(64)、display_name String(80)、role String(16)、is_active Boolean、password_hash String(255)、created_at。

约束及索引：小写规范用户名全局唯一；角色 owner/operator/viewer；组织/时间/ID 分页索引。

### user_sessions

主键及关系：id UUID、user_id UUID。

字段：token_digest String(64)、csrf_token String(64)、created_at、expires_at。

约束及索引：令牌摘要唯一；用户/过期索引；到期晚于创建；固定 8 小时。

### login_limits

主键及关系：id UUID。

字段：source_key String(64)、failures Integer、window_start。

约束及索引：直接来源摘要唯一；0–5 次失败；15 分钟窗口。

### audit_events

主键及关系：id UUID、organization_id、actor_user_id、entity_id UUID。

字段：action String(64)、entity_type String(32)、created_at。

约束及索引：组织/时间/ID 分页索引；与业务同事务追加。

### input_assets

主键及关系：id UUID、organization_id、plot_id 可空、actor_user_id。

字段：kind、name String(100)、source String(1000)、source_license String(300)、payload JSON、content_hash String(64)、created_at。

约束及索引：三种类型检查；品种不指定地块、其余必填；组织/类型/地块/时间/ID 索引。

### simulation_inputs

主键及关系：id UUID、organization_id、season_id、actor_user_id。

字段：version Integer、payload JSON、content_hash String(64)、created_at。

约束及索引：version >= 1；季节/版本唯一；组织/季节/时间/ID 索引。

数据库关系使用应用维护的逻辑外键。组织范围沿 plot → season → management_event 检查；新地块必须由服务端赋当前组织，客户端不能指定归属。0002 保留旧地块内容，通过显式初始化接收后补组织并记录审计。账号停用/密码修改会删除相应会话。审计展示的 actor_display_name 由本组织用户查询关联得到，不复制入审计表。

密码只存 Argon2id 哈希，随机会话令牌只在 HttpOnly Cookie 中携带，SQL 保存 SHA-256 摘要。CSRF 值绑定会话，用于校验请求，不作为登录凭证。登录限制不存原始 IP/用户名/密码。审计不存密码、会话凭证、请求体或备注正文。

保存原始亩数，响应派生公顷。标准施用水量为 mm，肥料产品质量为 kg/ha，有效入渗水和纯氮量需额外参数。Decimal 响应为字符串，日期为 ISO。时间写入 UTC，SQLite 读回补 UTC。

事务与锁见 [ADR 0002](adr/0002-farm-module.md)、[ADR 0003](adr/0003-identity.md)、[ADR0004](adr/0004-simulation-inputs.md)和 [ADR0005](adr/0005-potential-simulation.md)。无业务物理删除接口；绕过应用的 SQL 仍可能破坏关系，需限制运维写权限。农事 is_current 由后继关系派生，原始农事不更新；crop_code=rice 为模块常量。双数据库集成测试执行 Alembic check 检查迁移与 ORM 一致。

输入 payload 有明确土壤/品种/天气结构，天气原始 CSV 和解析日值同时保存；资料最多 512 KiB、CSV 256 KiB/366天、快照 1 MiB。快照持久化地块/季节/三份资料/截止前最新农事/标准天气/报告，原版本不更新。SHA-256 覆盖规范 payload，整数值浮点统一为整数；它不代替数字签名或模型验证。详见 [输入模块](modules/simulation-inputs.md)。

## 0004 计算任务/结果

simulation_runs：UUID id、organization_id、season_id、input_id、request_key、actor_user_id；model_code/engine_version String(32)、input_hash String(64)、status String(16)、attempts Integer；created_at/started_at/finished_at/lease_expires_at UTC、lease_token UUID；error_code String(64)、result JSON(nullable)、result_hash String(64)(nullable)。

组织/request_key唯一，组织/季节/时间/ID分页及状态/租约/时间索引；status限queued/running/succeeded/failed、attempts为0–3，running必须有且仅有租约字段，成功必须有结果/哈希且无错误码。所有关系是应用维护逻辑外键；私有租约字段不出API。结果最多512KiB，摘要列表不返回逐日结果。

任务状态随执行更新，完成结果无修改/删除接口。新UUID表示新计算版本，引用不可变输入ID/哈希；结果规范JSON哈希规则同输入。结果包含实际模型/PCSE/适配/软件版本、日值、天气、条件和标记，不修改旧输入报告。

## M3.3 天气来源字段（无迁移）

weather.payload新增可空provider：code固定nasa_power_hourly，adapter_version固定1.0.0，start_date/end_date ISO日期，requested_latitude/longitude有限数值，retrieved_at获取UTC时间，raw_response解析的原始小时JSON，raw_hash 64字符规范JSON SHA-256。旧资料和快照保留，不设置默认天气值。保存时核对日值、单位/日界、坐标/海拔与原始响应派生结果，再沿用资料/快照体积限制与同事务审计。

完整原始响应保留所有字段，不保留HTTP空白/键顺序；哈希仅证明内容一致，不能认证NASA身份。资料和输入保存来源，新 PCSE 结果的 weather_method 增加 source_kind、raw_hash。source_kind=gridded时station_id=null，不能把NOAA候选站点绑定为NASA来源。目录缓存24小时在内存，可丢弃；不新增业务表，迁移仍0004、11表。字段与方法见[天气模块](modules/weather-sources.md)。
