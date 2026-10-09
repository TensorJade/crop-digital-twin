# 2026-10-08 M1 农田管理

| 项目 | 内容 |
|---|---|
| 记录人 | Codex |
| 分支 | `codex/feature_farm_management_20261008` |
| 需求 | F02、F05、F12 的农田记录部分 |
| 试点范围 | 华南水稻，县市和品种参数待定 |
| 检查时间 | 14:32 完整检查；14:39 类型和单元复查；14:44 页面修正复查 |
| 时区 | Asia/Shanghai |

## 修改内容

实现地块登记、种植季、农事记录、追加修正、历史查询和季节结束。农田规则集中在 `domain/farm`，FarmService 组织用例，存储 Protocol 连接 SQL 适配，API 处理请求和响应。

| 部分 | 改动 |
|---|---|
| 数据库 | Alembic 0001，建立 plots、seasons、management_events |
| 日期与修订 | 检查季节冲突，开放季及修订后继使用唯一索引 |
| 并发 | SQLite BEGIN IMMEDIATE；PostgreSQL 父对象行锁 |
| 单位 | 保存原始亩数和操作量，计算公顷、水量和肥料产品质量 |
| 前端 | 三类表单、失败重试、历史开关、手机布局 |
| 接口 | 9 个业务操作，加健康接口共 10 个操作 |
| 工具 | 数据库初始化、浏览器检查、PostgreSQL 17 / Chromium CI |

前端使用请求代次处理延迟响应。暂不增加 GIS、Redis 或全局状态库。该版本供本地使用，production 模式拒绝启动。

环境为 Windows、Python 3.12.6、Node 24.19.0、npm 11.17.0、uv 0.12.23。新增 SQLAlchemy 2.1.4、Alembic 1.20.0、Psycopg 3.3.6、Playwright 1.64.0，Node 类型由 npm 锁文件固定。算法包当时仅有目录和接口规划。

## 检查结果

| 检查 | 结果 | 备注 |
|---|---|---|
| init-db | 通过 | 默认 SQLite 增量建表，API 不自动迁移 |
| Ruff / mypy | 通过 | mypy 检查 26 个源文件 |
| 本地 pytest | 26 项通过，22 项跳过 | 97.90%；本机无 PostgreSQL 服务 |
| Alembic check | 通过 | ORM 类型和索引与迁移一致 |
| 前端检查 / 单元 | 通过，9 项单元测试 | 类型、ESLint、Prettier |
| Vite build | 通过 | — |
| Edge 浏览器 | 4 条流程通过 | 临时 SQLite，含重试和延迟响应 |
| 桌面 / 390px 截图 | 布局正常 | 无横向溢出 |
| OpenAPI | 一致 | 7 条路径、10 个操作 |
| GitHub Actions | 48 项通过，4 条浏览器流程通过 | 98.28%；PostgreSQL / Chromium |

集成测试覆盖日期边界、输入拒绝和回滚、水肥换算、修订冲突、并发写入、结束日期及重启读取。PostgreSQL 使用独立 UUID schema，浏览器使用临时库。截图保存在忽略的 `runtime/farm-desktop.png`、`runtime/farm-mobile.png`。

## 问题处理

| 问题 | 处理和复查 |
|---|---|
| ORM 自动浮点类型与迁移不一致 | 显式声明 Float，Alembic check 通过 |
| Vue 内联多语句格式化后构建失败 | 改为命名函数，构建通过 |
| select 和 status 定位不明确 | 使用精确控件角色和提示筛选，4 条流程通过 |
| 同一地块重试未加载种植季 | 修复请求逻辑，增加浏览器回归检查 |
| 测试配置缺 Node 类型、导入扩展名提示 | 更新类型和 tsconfig，类型与单元检查通过 |
| 空列表表单与收起按钮冲突 | 隐藏空列表切换按钮，保存中禁用切换 |

最后一项修正后，14:44 重新通过前端静态检查、9 项单元测试、构建和 4 条 Edge 流程。

## 支持范围和待办

本机 Docker daemon 未运行，PostgreSQL 由 CI 检查，PostGIS 未启动。该版本尚无账户、地图、天气、PCSE、无人机、校准和备份恢复。逻辑引用方案见 ADR 0002，后续需要限制绕过应用的数据库写入。

灌溉换算结果为施用水量，肥料换算结果为产品质量；土壤入渗水和纯氮需要额外参数。下一步开发 M2 账户与授权，再进入 M3 输入和作物模型。

## 提交

| 编号 | 说明 |
|---|---|
| f9eb5aa81d14be60b74a64190bc61ff4cba1193c | 增加地块、种植季和农事管理 |
| 402deb0a6b329cb87ffd29f613426b69f1511bb5 | 修复空列表表单并补充数据库测试结果 |

分支从本地 release_20261008 建立并接收初始化文档。[CI 运行 37739132250](https://github.com/TensorJade/crop-digital-twin/actions/runs/37739132250)对应主实现 f9eb5aa，于 14:43:50 完成，python/frontend 均成功，后端 48 项无跳过，Chromium 4 条通过。提交已推送到功能分支，尚未合并或部署。
