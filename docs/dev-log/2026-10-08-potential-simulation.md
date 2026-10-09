# 2026-10-08 M3.2 潜在生长计算

| 项目 | 内容 |
|---|---|
| 记录人 | Codex |
| 分支 | `codex/feature_pcse_20261008` |
| 基线 | 50ba3c0cfe4c856c701b1e85744de57203a329d0 |
| 软件 / 算法包 | 0.5.0 / 0.3.0 |
| 输入 / 结果契约 | 1.0.0 |
| PCSE / 适配器 | 6.0.13 / 1.0.0 |

## 修改内容

接入 Wofost72_PP，使用保存的输入快照排队计算，由独立 worker 执行，返回日值、曲线、历史版本和下载文件。当前支持直播出苗后的潜在生长，假定水肥充足、无病虫害胁迫，使用已发生的连续北京时间天气。水田灌排和施肥响应尚未接入，贮藏器官干物质尚不能换算为实收产量。

| 主要文件 | 改动 |
|---|---|
| domain/simulation/runs.py、application/run_service.py、run_repository.py | 任务对象、请求去重、存储接口 |
| api/v1/runs.py、run_schemas.py | 新增三个操作 |
| database/run_models.py、run_repository.py、迁移 0004 | 任务和结果表，共 11 张业务表 |
| workers/simulation.py、scripts/simulation_worker.py、start-worker.ps1 | 任务领取、租约、恢复和启动 |
| crop_engine/potential.py、pcse_runner.py | 输入复查、隔离进程和 PCSE 日值 |
| frontend/features/simulation | 历史、轮询、SVG 曲线、日期滑块和下载 |
| tests/fixtures/potential-input.json | 合成品种和 15 日天气，用于软件测试 |

一张 SQL 表保存任务和结果。API 按组织和请求 UUID 去重，检查后入队；worker 用短事务领取 120 秒租约，子进程最多运行 60 秒，计算时释放写事务。过期租约最多领取三次，私有令牌防止迟到结果覆盖新任务状态。领取时复查操作者、角色、输入哈希、组织和版本。确定失败后保留安全错误码，重算建立新任务；运行中即时取消尚未实现。

任务状态与审计同事务提交，完成审计故障时保留原租约，过期后可恢复。只读成员可以查看和下载，不能提交计算。详细接口和数据流见 [模块设计](../modules/potential-simulation.md)和 [ADR 0005](../adr/0005-potential-simulation.md)。

## 模型与单位

使用 PCSE 6.0.13 的 ParameterProvider、WeatherDataProvider、WeatherDataContainer 和 reference_ET(PM)。蒸散量由 mm/day 除以 10 转为 cm/day；雨量 mm 转 cm，辐射 MJ/m² 转 J/m²，蒸汽压 kPa 转 hPa。要求 2m 风速、来源坐标、海拔和北京时间日界。

Angstrom 系数由资料提供者填写：A 为 0.1–0.4，B 为 0.3–0.7，两者之和为 0.6–0.9。旧天气资料仍可保存，缺系数时不能运行。

PCSE 仅在临时子进程导入，使用环境白名单和 Python `-I`。临时 .pcse 配置和空演示库标记用于隔离默认初始化，运行不读取演示数据，不联网获取参数或天气，也不携带应用数据库和账户凭据。父进程未导入 PCSE，检查前后用户 .pcse 文件未改变。许可见 [第三方清单](../../THIRD_PARTY.md)。

结果记录日值、天气、版本、输入哈希和假设；成熟时可能提前结束作物输出，记录 `last_crop_date`。`simulation_executed=true`，`agronomically_validated=false`，`management_effects_applied=false`。输入快照仍为未执行状态，新的 `report.simulation_available` 表示满足潜在计算条件。农事修正后需另存快照。

## 本地检查结果

| 检查 | 结果 | 备注 |
|---|---|---|
| 依赖同步 | 65 项 | 新增 PCSE 及其依赖 |
| Ruff / mypy | 通过 | mypy 检查 61 个源文件 |
| 后端 / 算法测试 | 137 项通过，79 项 PostgreSQL 跳过 | 共 216 项，覆盖率 94.92% |
| OpenAPI / 目录 | 通过 | 22 条路径、29 个操作、30 个文件 |
| 前端检查 / 构建 | 通过 | 22 项单元 |
| Edge 浏览器 | 13 条通过，32.1 秒 | 布局修正后两条重测，14.3 秒 |
| 桌面 / 390px 截图 | 无横向溢出 | 结果下载和离线核验通过 |
| 运行库迁移 | 0003 → 0004 | 原有数据和新增任务均为空 |
| worker -Once | 正常退出 | 空队列输出 No claimable task |

官方内核用合成输入执行两次，15 日结果一致；LAI 首日 0.224、末日约 12.3249，仅作为软件测试值。单日运行、缺系数、非法天气、模式和参数均检查。pcse_runner 在父进程覆盖率中显示为 0，通过独立执行和浏览器检查。

双数据库用例覆盖请求去重、权限、CSRF、导出、超时、非法结果、体积限制、过期令牌、重试耗尽、双 worker、成员停用、输入损坏、版本不符和审计恢复。本机 PostgreSQL 未运行，相关用例由 CI 执行。

## 问题处理

| 问题 | 处理 |
|---|---|
| Ruff 长行和 SQL 约束排版 | 调整后检查通过 |
| 官方许可读取编码问题 | 显式使用 UTF-8 |
| 通用 label 样式影响确认框 | 调整局部选择器优先级 |
| 手机曲线文字偏小 | 调整并复查截图 |
| 失败任务刷新后未重新读取 | 刷新时重取详情 |
| Linux mypy 不识别 CREATE_NO_WINDOW | 改为显式 sys.platform 分支 |
| 本机未安装 Chromium，重测未指定 Edge | 使用已安装 Edge，两条流程通过，12.3 秒 |

## 提交和 CI

| 提交 | 说明 | CI |
|---|---|---|
| 7631c73c2d50af0718791f72044279509f836b37 | 接入 PCSE 和后台任务 | Python 类型检查失败；前端通过 |
| 2a1ca91bb08c9ab326448350fe8d8bc4642ba348 | 修复跨平台进程参数检查 | 全部通过 |
| 2629b8e4eb3dd4feca447e7d241ac51d5682351b | 补充计算和数据库检查记录 | 全部通过 |

首次 [CI 37782416824](https://github.com/TensorJade/crop-digital-twin/actions/runs/37782416824)中，前端 22 项单元、13 条 Chromium 流程通过（29.3 秒），Python 在 Linux mypy 处失败，后端测试未执行。问题来自条件表达式中的 Windows 专用参数。修正后本地 Windows/Linux 类型检查均通过，CI 增加 Windows 检查，本地脚本增加 Linux 检查。

修正提交的 [CI 37782900218](https://github.com/TensorJade/crop-digital-twin/actions/runs/37782900218)于 21:19（Asia/Shanghai）检查，两个任务成功。PostgreSQL 17 / SQLite 共 216 项全部通过、无跳过（128.71 秒），覆盖率 95.01%；双平台 mypy 61 个文件、Ruff、契约和目录检查通过。前端 22 项单元、13 条 Chromium 流程通过（29.0 秒）。补记文档的 [CI 37783666060](https://github.com/TensorJade/crop-digital-twin/actions/runs/37783666060)也通过。

提交已推送到功能分支，尚未合并或公开部署，远程发布分支和人工评审待安排。

## 待办

继续开发天气源和站点适配，确认品种来源、许可和当地实测资料，补充移栽水田及灌排、施肥规则。地图、无人机反射率、LAI 和参数校准按后续模块开发，生产部署和备份恢复安排在 M7。

参考：[PCSE 文档](https://pcse.readthedocs.io/en/stable/code.html)、[PCSE 6.0.13](https://pypi.org/project/pcse/6.0.13/)。
