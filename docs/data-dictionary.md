# 数据字典与实际迁移

总体目标包含 [20 张规划表](design-baseline/数据字典设计.json)与 [ER 图](diagrams/er_global.svg)。M1 仅建立三张业务表。

| 表 | 主键与关系 | 主要事实 | 约束/索引 |
|---|---|---|---|
| plots | id UUID | name、area_mu Numeric(16,6)、latitude/longitude Float、created_at | 面积/坐标范围；创建时间分页 |
| seasons | id UUID、plot_id 逻辑引用 | start_date/end_date、establishment_method、variety_name、created_at | 日期/方式检查；地块/日期；每地块一开放季 |
| management_events | id UUID、season_id、replaces_event_id 逻辑引用 | 类型/日期、原始/标准数量单位、肥料名称、备注、时间、修订号/原因 | 数量/版本检查；季节/日期；替代指针唯一 |

保存原始亩数，响应派生公顷。标准水量为 mm、肥料产品质量为 kg/ha；不是入渗水或纯氮量。Decimal 响应为字符串，日期为 ISO。时间写入 UTC，SQLite 读回统一补充 UTC。

应用逻辑外键、事务与锁见 [ADR 0002](adr/0002-farm-module.md)。不提供物理删除；绕过应用的 SQL 仍可能破坏关系，需限制运维写权限。其他规划表尚未实施。

is_current 由后继修订关系查询，原始农事不更新；crop_code=rice 是模块常量，不重复存表。完整类型、空值、精度和索引以迁移 0001_farm_records.py 与 ORM 为准；集成测试执行 Alembic check 验证一致性。
