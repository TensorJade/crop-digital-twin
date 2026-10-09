# 产品与实现架构

系统由 FastAPI 后端、Vue 前端、独立算法包和 SQL worker 组成。API 处理授权和任务提交，worker 在独立进程中计算。业务数据保存在 SQLite 或 PostgreSQL，当前任务量由 SQL 队列处理。

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

目前已实现农田、账户、输入、潜在生长计算，以及历史天气和站点目录。主要流程为：天气预览与保存 → 输入快照 → SQL 排队 → worker 计算 → 日值、曲线和导出。

API 不导入 PCSE，算法不访问 HTTP 或应用数据库。天气获取前完成 SQL 授权检查并关闭事务，站点目录在进程内缓存 24 小时。授权站点观测、当天更新、预测、卫星地图、影像存储和遥感校准待开发。初始目标图保存在 docs/diagrams。

| 层 / 组件 | 职责 |
|---|---|
| 前端功能模块 | 组件、类型、请求及页面状态 |
| 后端 API | 请求校验、授权、响应 |
| 应用服务 | 用例、事务和请求去重 |
| 领域层 | 对象和业务规则，无框架依赖 |
| 存储适配 | SQL、组织范围和锁 |
| 天气适配 | 固定源请求、日值转换和目录缓存 |
| worker / 算法包 | 任务领取、进程隔离和模型执行 |

共用 HTTP 和分页模块独立于业务模块。各模块数据流见 [农田](modules/farm-management.md)、[账户](modules/identity.md)、[输入](modules/simulation-inputs.md)、[计算](modules/potential-simulation.md)和 [天气](modules/weather-sources.md)。

账户使用 Argon2id、可撤销 SQL 会话、HttpOnly Cookie 和内存 CSRF，无 JWT/Redis。组织内共享地块，跨组织资源返回404。写操作与审计同事务；停用/改密码撤销会话。旧地块接收须显式初始化，不自动归属首次登录者。见 [ADR0003](adr/0003-identity.md)。

资料、输入快照和历史结果只追加，农事修正保留原版本。一张 simulation_runs 同时保存有界任务与结果，组织/request_key 去重；领取用短事务和租约令牌，计算期间无 SQL 写锁，迟到 worker 不能覆盖新租约。过期任务最多领取三次，确定失败须新建计算；任务/结果状态与审计一致。无 worker 时持久排队，重启后可恢复。见 [ADR0004](adr/0004-simulation-inputs.md)、[ADR0005](adr/0005-potential-simulation.md)。

PCSE 固定版本，仅在隔离临时目录/环境中导入，阻止默认用户配置/演示数据库参与业务。不携带应用数据库或账户秘密，不下载外部参数/天气，不执行用户脚本。模型只支持直播已出苗的潜在生产条件；冻结的农事供追踪，尚无灌排/施肥响应。模型执行和农艺适用性分别检查。

后续影像拟使用对象存储，SQL 保存来源、版本和校验和；遥感观测、原始预测和校准结果分别留存。根据容量和协调需求再评估 Redis。production 启动保护保留到 M7，部署、备份恢复、容量及 SLA 在试点阶段验收。
