# 2026-10-08 M3.1 模拟输入

| 项目 | 内容 |
|---|---|
| 记录人 | Codex |
| 分支 | `codex/feature_simulation_inputs_20261008` |
| 基线 | 119236abd14a57b893121d11959cf321023472c5 |
| 软件 / 算法包 | 0.4.0 / 0.2.0 |
| 快照契约 | 1.0.0 |

## 修改内容

实现土壤登记、品种 JSON 和天气 CSV 导入，经静态检查和单位转换后保存种植季输入快照，支持查看、下载和离线核验。沿用 M2 的组织权限和审计，增加两张表、一个应用服务和存储接口。

快照保存地块、种植季、截止日前最新农事修订、三份资料、来源和许可、规范天气、版本及检查报告。版本在种植季锁内分配，后续修改不覆盖旧快照。审计失败时，资料或快照写入一起回滚。

| 主要文件 | 改动 |
|---|---|
| api/v1/inputs.py、input_schemas.py | 新增 7 个操作和三类资料校验 |
| application/input_service.py、input_repository.py | 资料和快照用例、存储接口 |
| domain/simulation/models.py | 资料与快照对象 |
| infrastructure/database/input_models.py、input_repository.py | SQL 实现 |
| migrations/versions/0003* | 新增资料和快照表，共 10 张业务表 |
| packages/crop_engine/inputs.py | 参数、CSV、单位、序列化及哈希检查 |
| frontend/src/features/simulation | 资料组件、类型、请求和文件下载 |
| scripts/verify_input.py | 输入文件哈希核验 |

前端增加农事和模拟资料分页签页；切换种植季时清理旧状态，忽略迟到响应。同步版本、锁文件、OpenAPI、检查脚本和文档，新增两条浏览器流程。

## 参数与模型准备

从 PCSE 6.0.13 官方 wheel 的 ParameterTemplate 提取 WOFOST72 参数清单，尚未安装或执行 PCSE。检查 WeatherDataContainer 范围，包括蒸汽压 0.06–199.3 hPa、海拔 -300–6000 m。天气原值保留，超范围时阻止后续运行。E0、ES0、ET0 尚未计算，天气提供器留到 M3.2 实现。

PCSE 使用 EUPL 1.1 或以后版本，导入时会建立用户配置和演示库，适配时需要隔离。官方参数仓库 wofost72 分支当时为 `f0a6491f23685998fa2172b397ff959a3b5ea738`；未找到统一许可文件，因此未复制为默认参数。相邻 wofost_lai_edge 仅有演示和适配入口，本次未借用。

天气资料分别标记 station、gridded，要求声明位置、海拔和日界。播种、出苗、移栽日期分别保存。该版本移栽输入不能运行，灌溉和肥料尚未映射到模型；`input_ready` 表示资料完整，`simulation_available`、`simulation_executed` 均为 false。离线脚本检查文件内容一致性，来源许可及模型精度仍需另外核实。

## 检查结果

| 检查 | 本地结果 | CI 结果 |
|---|---|---|
| 依赖同步 | 49 项，无新增外部运行依赖 | 通过 |
| Ruff / mypy | 通过；mypy 50 个源文件 | 通过 |
| 后端 / 算法测试 | 102 项通过，62 项 PostgreSQL 跳过 | 164 项通过，无跳过 |
| 合并行覆盖率 | 98.17%；输入包 100% | 98.30% |
| 契约 / 目录 | 20 条路径、26 个操作；25 个文件 | 通过 |
| 前端检查 / 构建 | 通过，20 项单元 | 通过，20 项单元 |
| 浏览器 | 11 条 Edge 流程，22.1 秒 | 11 条 Chromium 流程，18.4 秒 |
| 桌面 / 390px 截图 | 无横向溢出 | — |
| JSON 下载与离线核验 | 通过；修改后的副本返回非零 | — |

本机未配置 PostgreSQL 测试服务，CI 使用 PostgreSQL 17 / SQLite。集成测试覆盖非法资料、日期和单位、天气缺失、品种缺项、组织与地块权限、只读角色、分页、旧快照、并发版本及审计回滚。两名不同成员并发保存快照，用于检查种植季锁。

CSV 的 BOM、CRLF 和末尾空白原样保留，品种 JSON 支持 BOM。篡改下载文件后的核验返回非零，错误输出未包含原文或堆栈。截图和导出文件放在忽略的 runtime。

运行库从 0002 升级到 0003，检查的原有五张表和新增资料、快照表均为空，未创建运行账号或测试记录。

## 问题处理

| 问题 | 处理 |
|---|---|
| 单元测试复用已读取的 Response | 每次请求建立新对象 |
| 登录限制测试影响其他浏览器流程 | 改用 127.0.0.2 来源，继续检查代理头绕过 |
| 浏览器改变 JSON 的 1.0 和 -0 表示 | 规范化后计算哈希 |
| 缺参数提示过于技术化 | 折叠参数清单，默认提示联系提供者 |
| 误用不存在的 npm test:unit | 使用仓库定义的 npm test，检查通过 |

## 提交与待办

| 编号 | 说明 |
|---|---|
| efc95d04e79907499720cee4f52fc15a61e35597 | 增加模拟资料导入和种植季输入快照 |
| 50ba3c0cfe4c856c701b1e85744de57203a329d0 | 补充输入模块测试记录 |

提交已推送到功能分支。[CI 运行 37768936266](https://github.com/TensorJade/crop-digital-twin/actions/runs/37768936266)于 19:19（Asia/Shanghai）检查，两项任务成功。

M3.1 完成，M3 继续开发。下一步实现隔离的 PCSE 执行和天气提供器，补充试点县市、品种来源、许可及实测资料，明确移栽和水田管理条件。自动天气、地图、无人机和发布运维仍在计划中。

参考：[PCSE 文档](https://pcse.readthedocs.io/en/stable/)、[参数仓库](https://github.com/ajwdewit/WOFOST_crop_parameters)。接口与数据流见 [模块设计](../modules/simulation-inputs.md)和 [ADR 0004](../adr/0004-simulation-inputs.md)。
