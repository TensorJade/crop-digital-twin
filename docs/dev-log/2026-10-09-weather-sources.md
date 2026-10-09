# 2026-10-09 M3.3 历史天气和站点目录

| 项目 | 内容 |
|---|---|
| 记录人 | Codex |
| 分支 | `codex/feature_weather_20261009` |
| 基线 | 2629b8e4eb3dd4feca447e7d241ac51d5682351b |
| 软件 / 算法包 | 0.6.0 / 0.3.1 |
| PCSE / 模型适配器 | 6.0.13 / 1.0.1 |
| NASA 转换 / 输入及结果契约 | 1.0.0 / 1.0.0 |
| 时区 | Asia/Shanghai |

## 修改内容

按地块坐标获取 NASA POWER UTC 小时资料，转换为完整北京时间日值，支持预览、重试、CSV 下载和保存。天气资料随输入快照进入 PCSE 计算。附近 NOAA 站点单独显示位置、距离和历史覆盖日期，`observations_connected=false`。

| 部分 | 改动 |
|---|---|
| api/v1/weather.py、input_schemas.py | 两个新 GET 和来源校验 |
| infrastructure/weather | HTTP、小时转换、来源和站点目录 |
| domain/simulation/weather.py | 天气规则 |
| WeatherSourcePanel.vue、weatherApi.ts | 天气预览、下载和保存 |
| SimulationInputsPanel | 天气功能入口 |
| 算法结果 weather_method | 保存天气来源和哈希 |

沿用 input_assets、快照、权限、审计、任务和 worker，没有新表、迁移或外部包。授权 SQL 事务在上游请求前结束；HTTP 固定两个 HTTPS 目的地，禁止重定向，socket 超时 15 秒，上游并发限制为 2。每次获取 1–366 个已结束历史日，按不超过 120 天的区间分段；每日要求完整 24 小时，检查单位、填充值和体积，缺测时拒绝保存。A/B 系数仍由资料提供者声明。

接口、数据流和限制见 [模块设计](../modules/weather-sources.md)及 [ADR 0006](../adr/0006-weather-sources.md)。

## 联网检查

核对 NASA 小时 API、数据 FAQ、NOAA ISD 目录、FAO 露点公式和数据使用政策。AG 单位分别为 C、C、m/s、mm/hour、MJ/hr，请求使用 `time-standard=UTC`，再按 UTC+8 分日。POWER 数据有数日延迟，暂不支持当天更新。

WeatherSources 和响应模型请求广州示例点 23.1°N、113.2°E，日期为 2024-03-02 至 03，返回两日资料，API 版本 v2.10.2。

| 首日指标 | 结果 |
|---|---|
| 小时派生最低 / 最高温 | 6.4 / 19.12 ℃ |
| 降水 | 0.54 mm |
| 辐射 | 7.64 MJ/m² |
| 风速 | 3.534583 m/s |
| 蒸汽压 | 0.870197 kPa |

原始响应规范哈希为 `e54142ebb240b2211619182835a59d25a9cc551f80129cf97fef99fff304c099`。

NOAA 目录响应约 2.91 MB，筛选出 5 个候选；最近的 BAIYUN INTL（592870-99999）距示例点约 34.01 km，历史覆盖 1945-11-30 至 2025-08-24。目录只用于寻找站点，观测数据尚未接入。检查响应存放在忽略的 runtime，未写入运行数据库。

## 检查结果

| 检查 | 本地结果 | 实现提交 CI |
|---|---|---|
| 依赖同步 | 65 项，无新增外部包 | 通过 |
| 后端 / 算法测试 | 165 项通过，83 项 PostgreSQL 跳过 | 248 项通过，无跳过，89.17 秒 |
| 合并行覆盖率 | 95.40% | 95.48% |
| Ruff / mypy | 通过；格式 88 文件，双平台 mypy 69 文件 | 通过 |
| 前端单元 | 24 项通过 | 24 项通过 |
| 前端检查 / 构建 | 通过 | 通过 |
| 浏览器 | 14 条 Edge 流程，36.2 秒 | 14 条 Chromium 流程，35.1 秒 |
| 契约 / 目录 | 24 条路径、31 个操作；34 个文件 | 通过 |

桌面和 390px 手机截图已查看，修复后无横向溢出。测试覆盖日期边界、24 小时完整性、单位、来源一致性、上游请求前 SQL 释放、组织和角色、失败回滚、缓存和传输限制。PCSE 子进程通过独立执行和浏览器流程检查，其代码不计入父进程行覆盖率。当地农艺精度仍待实测验证。

`power-hourly.json` 和 `weather-stations.csv` 为自行构造的软件测试资料，站点名含 SOFTWARE TEST。e2e_api 仅在已检查的 test / OS 临时库中注入天气客户端，页面也标记为软件验收资料；生长计算使用 worker 和 PCSE。

## 问题处理

| 问题 | 处理 |
|---|---|
| 单元测试 Plot 字段构造不匹配 | 修正关键字字段 |
| Vue 多条内联事件格式化后解析失败 | 改为命名函数，重新构建 |
| 预览区域缺可访问名称 | 使用语义 section |
| CSV 中 20 与 20.0 文本比较失败 | 改为数值比较 |
| 手机嵌套网格横向溢出 | 调整 min-width、网格列、padding 和按钮间距 |
| 首次 Edge 全量旧农田流程超时 | 等待地块加载结束后再判断表单入口 |
| 新 e2e_weather.py 未纳入类型检查 | 显式加入，双平台 69 个文件通过 |

首次 Edge 全量运行 13 条通过、1 条超时。原因是空列表加载结束后表单自动展开，原按钮消失；修正辅助函数后，14 条全部通过，未增加固定等待或重试次数。

检查时运行 SQLite 为 `0004_simulation_runs`，11 张业务表均为空。OpenAPI、Markdown 本地链接、锁文件和 `git diff --check` 通过。联网响应、截图及下载仅保存在忽略的 runtime / test-results。

## 提交和 CI

| 编号 | 说明 |
|---|---|
| 5ce2e6cb4669496fd2c0ca8a3159d7259460e6cb | 按地块获取历史天气并保存来源 |
| 87e56276978b1dd7abadc0c49264e06d53ac9f87 | 补充天气接口和浏览器测试记录 |

两个提交已推送到 weather 分支。[实现提交 CI 37874015923](https://github.com/TensorJade/crop-digital-twin/actions/runs/37874015923)全部成功，结果见上表。[文档提交 CI 37874304086](https://github.com/TensorJade/crop-digital-twin/actions/runs/37874304086)也成功：后端 248 项通过，覆盖率 95.48%（124.09 秒）；前端 24 项单元、14 条 Chromium 流程通过（30.9 秒）。

CI 使用 PostgreSQL 17、临时 schema / SQLite 和合成天气。本机未配置 PostgreSQL 测试 URL，83 项用例由 CI 执行。远程默认分支仍为 scaffold，最新功能位于 weather 分支，公开部署和发布评审尚未开始。

## 待办

接入授权站点观测，支持 120 天以上分段合并，确认具体品种来源并开展当地验证。移栽水田和灌排、施肥效应仍需适配，卫星地图、无人机反射率、LAI 反演及校准按 M4–M6 开发。

参考：[NASA POWER 小时 API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/)、[数据与延迟](https://power.larc.nasa.gov/docs/faqs/data/)、[NOAA ISD](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database)、[FAO 气象数据](https://www.fao.org/4/x0490e/x0490e07.htm)。
