# 产品与实现架构

当前采用模块化 FastAPI 后端、Vue Web 前端、独立算法包和 SQL worker。API 负责授权和快速提交，计算在独立进程执行；本地 SQLite、服务器 PostgreSQL 为唯一业务事实来源，无需 Redis。

~~~mermaid
flowchart LR
  U[农田管理人员] --> WEB[Vue / TypeScript]
  WEB --> API[FastAPI / 会话 / 角色 / CSRF]
  API --> APP[农田 / 账户 / 输入 / 计算用例]
  APP --> DB[(SQLite / PostgreSQL)]
  APP --> CHECK[crop_engine 静态检查]
  DB --> W[Python worker：短事务领取]
  W --> P[临时子进程：PCSE6.0.13]
  P --> W
  W --> DB
  DB --> API
  API --> WEATHER[天气适配：短SQL校验后联网]
  WEATHER --> POWER[NASA POWER历史小时网格]
  WEATHER --> NOAA[NOAA历史站点目录]
  WEATHER --> API
~~~

已实现M1/M2/M3.1/M3.2及M3.3历史网格天气/站点目录：天气预览并保存原始响应 → 输入封存 → SQL排队 → 独立worker → 真实Wofost72_PP → 版本化日值/曲线/导出。API不导入PCSE，算法不读HTTP或应用数据库。天气只在明确请求时获取，短SQL授权事务在上游HTTP之前结束；目录进程内缓存24小时，无Redis。授权站点观测、当天更新/预测、卫星底图/空间扩展、影像对象存储和遥感校准仍待实施。初始目标图保存在docs/diagrams，与当前实现分别维护。

实际数据流见 [农田](modules/farm-management.md)、[账户](modules/identity.md)、[输入](modules/simulation-inputs.md)、[计算](modules/potential-simulation.md)和[天气](modules/weather-sources.md)。前端各功能集中组件、类型和API；后端接口负责校验/授权，用例负责事务与幂等，领域无框架依赖，存储适配负责组织范围SQL，共用HTTP/分页不反向依赖业务。

账户使用 Argon2id、可撤销 SQL 会话、HttpOnly Cookie 和内存 CSRF，无 JWT/Redis。组织内共享地块，跨组织资源返回404。写操作与审计同事务；停用/改密码撤销会话。旧地块接收须显式初始化，不自动归属首次登录者。见 [ADR0003](adr/0003-identity.md)。

资料、输入快照和历史结果只追加，农事修正保留原版本。一张 simulation_runs 同时保存有界任务与结果，组织/request_key 去重；领取用短事务和租约令牌，计算期间无 SQL 写锁，迟到 worker 不能覆盖新租约。过期任务最多领取三次，确定失败须新建计算；任务/结果状态与审计一致。无 worker 时持久排队，重启后可恢复。见 [ADR0004](adr/0004-simulation-inputs.md)、[ADR0005](adr/0005-potential-simulation.md)。

PCSE 固定版本，仅在隔离临时目录/环境中导入，阻止默认用户配置/演示数据库参与业务。不携带应用数据库或账户秘密，不下载外部参数/天气，不执行用户脚本。模型只支持直播已出苗的潜在生产条件；冻结的农事供追踪，尚无灌排/施肥响应。软件可执行性与农艺适用性分别验证。

后续影像在对象存储保留原始文件，SQL 保存来源、版本和校验和；遥感观测、未更新预测、校准结果分别留存。Redis 仅在实测容量或协调需要时引入。production 启动保护保留到 M7；部署、备份恢复、容量与 SLA 需试点验收。
