# 开发日志：M3.1 模拟输入资料与不可变快照

- 日期：2026-10-08；开发与记录：Codex，实际操作结果由本地工具和远程 CI 核验。
- 路径：D:\Dev\软著\crop-digital-twin。
- 分支：codex/feature_simulation_inputs_20261008，基于 release_20261008 并快进已有 M2 成果 119236abd14a57b893121d11959cf321023472c5。
- 版本：软件/API/Web 0.4.0，独立输入算法包 0.2.0，快照契约 1.0.0。
- 用户已确认华南水稻，授权按模块开发并同步此 GitHub 仓库。具体县市与品种未补充，未填写猜测参数。

## 范围与设计

M3 拆为 M3.1 输入链路、M3.2 科学引擎。此次建立土壤、品种参数 JSON、天气 CSV → 静态检查/单位转换 → SQL 版本快照 → 前端查看/下载/离线核验的闭环。保持模块化后端，复用 M2 授权和审计，不新增 Redis、任务框架、通用 CRUD 或外部数据 SDK。

输入模块共两张表、一个应用服务、一个存储边界，三种确定资料用判别结构校验。组织隔离、地块/资料关系、种植季日期与角色在后端校验；审计失败回滚资料/快照。版本在种植季锁内分配，历史只追加。前端农事和模拟资料分页签页，切换季节卸载旧输入状态，迟到响应不能覆盖当前选择。

快照记录当时的地块、季节、截止日前最新农事修订、三份资料及来源/许可、规范天气、软件/契约版本和检查报告。农事后续更正不改变旧快照。JSON 下载保留校验和，scripts/verify_input.py 只核验 payload 内容一致性，不证明来源真实、签名有效或模型精度。

## 实际文件

- api/v1/input_schemas.py、inputs.py：7 个新增操作，土壤/品种/天气结构、摘要/详情、错误与角色。
- application/input_service.py、input_repository.py 与 domain/simulation/models.py：业务、快照与存储契约。
- infrastructure/database/input_models.py、input_repository.py，迁移 0003：十张业务表的最新 schema。
- packages/crop_engine/inputs.py：纯参数/CSV/单位检查、规范序列化与哈希。
- frontend/src/features/simulation：两份组件、types/api/files，FarmPage 季节签页与已有响应式 CSS。
- contracts/openapi.*、版本/锁文件、覆盖率/工作区检查脚本和 GitHub Actions。
- 单元、双数据库集成及两条新增浏览器流程，相关架构、目录、需求、ADR 和运行文档。

## 科学与依赖核对

查阅官方 PCSE 文档和 PyPI6.0.13；从官方 wheel 的组件 ParameterTemplate 静态提取 WOFOST72 关键参数，未执行包。核对 PCSE WeatherDataContainer 标准范围，包括蒸汽压 0.06–199.3 hPa、海拔 -300–6000m；原始天气保留，超标准范围在预检阻塞。输出仍缺引擎端 E0/ES0/ET0，不是可直接执行的完整天气提供器。

PCSE 为 EUPL1.1 或以后版本；导入默认建立用户配置/演示库，实际适配须隔离这些副作用。未安装 PCSE、未打包远程水稻数值参数。官方 WOFOST 参数分支 wofost72 核对 SHA f0a6491f23685998fa2172b397ff959a3b5ea738，但未找到统一许可文件，未复制为产品默认值。相邻 wofost_lai_edge 仅有演示/适配入口，未借用为真实水稻模拟。

station/gridded 明确区分；天气日界及真实位置/海拔必须声明，不自动把网格称为气象站。出苗、播种、移栽日期分别保留。移栽初始状态仍阻塞；灌溉和肥料记录尚未映射成水田管理信号。input_ready 不等于引擎可用，simulation_available 与 simulation_executed 均为 false。

## 本地验证

| 检查 | 真实结果 |
|---|---|
| uv sync --locked --all-packages --group dev | 成功，49 个依赖；未增加外部运行依赖 |
| Ruff 检查/格式；mypy | 通过，50 个源文件严格类型检查 |
| pytest 合并 crop_twin/crop_engine 覆盖率 | 164 项中 102 通过、62 PG 用例跳过；98.17%，纯输入包 100% |
| OpenAPI --check；check_workspace.py | 一致；25 个必要文件；20 条路径/26 操作 |
| npm typecheck/lint/format:check/test/build | 全部通过，20 项单元 |
| check-e2e.ps1 -BrowserChannel msedge | 11 条真实浏览器流程通过（22.1s，最终本地复核） |
| 页面与导出 | 桌面/390px 手机截图已查看，无横向溢出；浏览器下载 JSON 后实际运行 Python 核验通过 |
| 本地增量迁移 | 0002→0003；原五张表数量保持零，新资料/快照数量零；未创建运行账号或测试数据 |

集成覆盖非法数据、单位与时间边界、缺天气、参数缺项、跨组织/跨地块访问、只读写拒绝、分页、旧快照修订不变、并发版本和审计失败回滚。新增蒸汽压上下界、海拔边界用例防止单位/PCSE 范围错误。

最终复核还验证天气 CSV 的 BOM、CRLF 和末尾空白原样保留；品种 JSON 可识别 BOM。并发快照改由两名不同成员同时保存，避免用户锁掩盖季节锁问题。实际浏览器导出文件被修改后的副本运行核验返回非零，且无原文或堆栈泄露；仅写入忽略的 runtime。

开发中发现并修正：单元测试重复使用已经读取的 Response 对象，改为每请求新建；浏览器登录限制测试改用真实 127.0.0.2 来源，仍检查伪造代理头不能绕过限流，但不会锁住其他流程的 127.0.0.1。JSON 中 1.0→1 和 -0 的浏览器变化通过规范化解决。页面缺参数技术清单折叠，默认展示“联系参数提供者补充”。曾误调用不存在的 npm test:unit，改用仓库定义的 npm test 后通过。

## Git 与远程验证

代码提交与推送待完成；本机无 PostgreSQL 测试 URL、Docker daemon 未运行，因此不将跳过计作成功。远程 CI 使用真实 PostgreSQL17/SQLite 和 Chromium，结果将在核验后记录。未合并保护分支，未部署公开服务。

## 下一步和限制

M3.1 完成输入子模块，M3 整体仍进行中。M3.2 需确定试点县市、品种参数来源/许可和实测资料，交付隔离副作用的真实 PCSE 运行、天气提供器、移栽/水田管理适用条件和可复现输出。自动站点搜索/联网天气需数据源适配；不把本阶段手工导入称为已接入。地图、无人机反演/校准和发布运维依路线后续实施。软件用例与覆盖率不能作为农艺有效性结论。

依据：[PCSE 官方文档](https://pcse.readthedocs.io/en/stable/)、[官方参数仓库](https://github.com/ajwdewit/WOFOST_crop_parameters)。数据流与接口见 [模块设计](../modules/simulation-inputs.md)、[ADR0004](../adr/0004-simulation-inputs.md)。
