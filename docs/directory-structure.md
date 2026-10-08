# 开发目录与模块语言

仓库根目录为 `D:\Dev\软著\crop-digital-twin`。使用单仓库统一追踪需求、前后端和算法版本；算法包仍保持独立依赖与接口边界。

| 路径 | 职责 | 开发语言/格式 | 当前状态 |
|---|---|---|---|
| frontend/src/app | 前端启动、未来路由与状态 | TypeScript、Vue SFC | 开发首页已运行 |
| frontend/src/pages、components | 业务页面、通用组件 | TypeScript、Vue SFC | 预留 |
| frontend/src/features/{plots,management,imagery,growth} | 地块、农事、影像、长势 | TypeScript、Vue SFC | 预留 |
| frontend/src/maps | 卫星底图和作物矢量适配 | TypeScript | 预留 |
| frontend/src/api | 请求与接口类型 | TypeScript | 健康检查已实现 |
| frontend/src/styles | 样式与设计变量 | CSS | 开发首页样式 |
| backend/src/crop_twin/api/v1 | API 边界和输入输出验证 | Python | 仅健康检查 |
| backend/src/crop_twin/application | 业务用例和事务编排 | Python | 预留 |
| backend/src/crop_twin/domain/{identity,plots,seasons,management,observations,simulation} | 领域对象与业务规则 | Python | 预留 |
| backend/src/crop_twin/infrastructure/{database,object_store,weather,messaging} | 外部适配器 | Python | 预留 |
| backend/src/crop_twin/workers | 影像、模拟、调度与恢复任务 | Python | 预留 |
| backend/src/crop_twin/core | 设置、未来日志和认证 | Python | 设置已实现 |
| backend/migrations | 未来数据库迁移 | Python、SQL | 未建表 |
| packages/crop_engine/src/crop_engine | PCSE/WOFOST 适配和来源追踪 | Python | 包边界已建立 |
| packages/crop_engine/src/crop_engine/{imagery,calibration} | 遥感质控、反演、校准 | Python | 预留 |
| contracts | OpenAPI、JSON Schema | YAML、JSON | 健康检查契约已导出 |
| model-assets | 参数与授权清单 | YAML、JSON、文本 | 未含科学模型资产 |
| tests | 单元、集成、端到端验收 | Python、TypeScript | API/客户端测试已实现 |
| infra | 服务编排、未来镜像与运维 | YAML、Dockerfile、配置 | 仅数据库 Compose |
| scripts | 安装、启动、检查、日志、导出 | PowerShell、Python | 已实现 |
| docs | 需求、架构、决策、运行手册、日志 | Markdown、SVG、JSON | 开发文档基线 |

空模块使用 `.gitkeep` 保留，不添加假实现。新增模块要有真实职责；不要把算法堆进 API 路由，也不要让 UI 直接依赖数据库或对象存储内部路径。

实际完整目录可用 `git ls-files` 查看（只列版本化文件），本机依赖与输出不在此列表中。中文资料保留中文文件名，代码路径以英文命名，便于跨平台工具处理。
