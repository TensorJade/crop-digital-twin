# 开发日志：M3.2 潜在生长计算与离线天气适配

- 日期：2026-10-08；开发/记录：Codex，结果由实际工具执行核验。
- 路径：D:/Dev/软著/crop-digital-twin。
- 分支：codex/feature_pcse_20261008，基于 release_20261008 并快进 M3.1 50ba3c0cfe4c856c701b1e85744de57203a329d0。
- 软件/API/Web0.5.0，算法包0.3.0，输入/结果契约1.0.0，PCSE6.0.13，适配器1.0.0。
- 用户授权继续按模块开发并同步仓库；首版华南水稻，具体县市/品种未指定，没有猜测填入真实参数。

## 范围和设计

复用封存输入，实现快照 → 持久排队 → 独立 worker → 真实 PCSE 潜在生产 → 日值/曲线/版本/下载。选 Wofost72_PP，假定水肥充足、无病虫害胁迫；仅直播、明确出苗、已发生的连续北京时间天气。不把通用水量平衡当作已验证水田管理，不以贮藏器官干物质作为实收稻谷产量。

一个 SQL 表和独立 CLI worker 足以满足本轮需要，无 Redis/Celery/微服务/通用任务框架。API 用请求UUID去重，只做预检/排队；独立 worker 短事务领取120s租约，算法子进程最多60s，计算期间不占写事务。过期租约最多三次领取，私有令牌阻止迟到写回；确定失败保留安全错误码，重新计算用新任务。操作者启用/角色、输入哈希、组织和引擎版本在领取时复核；已运行任务的即时取消尚未实现。

任务、状态与审计同事务，失败一起回滚。完成审计故障留原运行租约，到期可恢复。API 摘要不返回结果/私有租约，详情仅本组织可见；只读成员可查看和下载，无提交计算权限。

## 文件和数据流

- backend/domain/simulation/runs.py、application/run_service.py/run_repository.py：计算对象、幂等用例与存储边界。
- api/v1/runs.py/run_schemas.py、database/run_models.py/run_repository.py、迁移0004：三个操作、新表、组织范围及冻结DDL。
- backend/workers/simulation.py、scripts/simulation_worker.py/start-worker.ps1：短事务领取/完成、租约恢复、独立启动。
- packages/crop_engine/potential.py/pcse_runner.py：重复校验封存输入、限时隔离子进程、真实模型和日值。
- 输入schema/service及天气表单：来源提供 Angstrom A/B，两者同时提供且符合PCSE范围；旧资料仍能保存，缺系数不能运行。
- frontend/features/simulation：任务API/类型、历史/轮询/下载、SVG曲线/日期滑块/数值，FarmPage增加“生长计算”。
- tests/fixtures/potential-input.json：自有合成软件验收品种与15日天气，不是农艺参数模板。
- backend/engine测试、growth.spec.ts、runs.test.ts、e2e_api.py实际worker、版本/锁文件/OpenAPI、模块设计/ADR/工程文档。

详细状态、接口、数据流和科学条件见 [模块设计](../modules/potential-simulation.md)、[ADR0005](../adr/0005-potential-simulation.md)。

## 科学依赖和单位核对

查阅 PCSE 官方模型/天气文档、PyPI6.0.13 与安装包源码。固定 Wofost72_PP、ParameterProvider、实际 WeatherDataProvider/Container；reference_ET(PM)输出mm/day，除10传入E0/ES0/ET0的cm/day。雨量mm→cm，辐射MJ/m²→J/m²，蒸汽压kPa→hPa；2m风速、来源坐标/海拔与北京时间日界明确。A=0.1–0.4、B=0.3–0.7、和=0.6–0.9，由资料提供者声明，没有当地默认值。

只在临时子进程导入PCSE，白名单环境不携带应用数据库/账号秘密，-I隔离Python用户配置，临时.pcse用户配置/空演示库标记避免改写实际用户目录和创建默认demo数据；不查询该标记、不联网取参数或天气。父进程未导入PCSE，实际用户.pcse前后文件状态未改变。官方版权/许可声明和边界见 [第三方清单](../../THIRD_PARTY.md)。

模型运行至已发生的截止日，成熟可能提前终止作物输出，单列last_crop_date。结果包含日值、规范天气、模型/适配/软件版本、输入哈希和假设；simulation_executed=true，agronomically_validated=false，management_effects_applied=false。输入快照仍simulation_executed=false；新report.simulation_available表示潜在输入满足，旧快照不重写。农事只封存，修正后需保存新快照。

## 本地验证

| 检查 | 实际结果 |
|---|---|
| uv sync --locked --all-packages --group dev | 65个依赖锁定/同步成功，加入官方PCSE及传递科学依赖 |
| Ruff check/format；mypy | 通过，61个源文件严格检查 |
| pytest 合并crop_twin/crop_engine | 216项中137通过、79项PG因未配置跳过；94.92%，超过80%门槛 |
| OpenAPI --check、工作区检查 | 22路径/29 GET/POST操作；30项必要文件 |
| npm typecheck/lint/format:check/test/build | 通过，22项单元 |
| Edge Playwright | 全部13流程通过（32.1s）；布局修正后两条生长流程再通过（14.3s） |
| 图像和导出 | 桌面/390px手机截图已实际查看，无溢出；真实PCSE结果下载并经Python离线校验通过 |
| 运行库升级 | 0003→0004；原有数据仍零、新任务零，没有运行账户/测试农田/默认参数 |
| start-worker.ps1 -Once | 空队列正常输出No claimable task并退出 |

实际黑盒测试两次运行官方内核，15日结果可复现；测试LAI首日0.224、末日约12.3249，属于未校准合成值，只验证软件。单日可执行；缺系数、非法天气/模式/参数被拒绝。PCSE私有子进程未计入父pytest行覆盖率（pcse_runner覆盖显示0），由真实黑盒与浏览器链路验证，未把这部分隐藏或宣称为农艺精度。

双数据库参数化测试覆盖请求幂等、输入/组织/只读/CSRF、版本导出、超时/非法结果/大小限制、安全错误、过期令牌/重试耗尽、双worker竞争、操作者停用/输入损坏/引擎版本不符、排队审计回滚和完成审计恢复。PostgreSQL部分本机未运行，必须以远程CI补验。前端验证真实异步任务、曲线日期和指标、下载校验、刷新历史、只读查看。

开发中修正Ruff长行/SQL约束排版；读取官方许可文件时改为显式UTF-8。页面截图发现确认框被通用label网格样式覆盖、手机曲线文字偏小，已提高局部选择器优先级并复核；刷新失败任务时重取当前详情，避免停止轮询后无法恢复读取。

## Git 与远程验证

实现提交7631c73c2d50af0718791f72044279509f836b37已推送。首次[CI运行37782416824](https://github.com/TensorJade/crop-digital-twin/actions/runs/37782416824)的前端22项单元/13条Chromium流程通过（29.3s），Python在Linux的mypy步骤失败，后端测试尚未执行。Linux不识别条件表达式中的Windows专用subprocess.CREATE_NO_WINDOW；Windows本地检查通过，Linux平台本地复现同一错误。改为显式sys.platform分支，本地两平台类型检查均通过；CI增加Windows、本地check增加Linux检查。修正后生长流程重测时首次未选择Edge，本机没有Chromium而无法启动浏览器，随后明确使用已安装Edge，两条流程通过（12.3s）。

修正提交2a1ca91bb08c9ab326448350fe8d8bc4642ba348已推送，[CI运行37782900218](https://github.com/TensorJade/crop-digital-twin/actions/runs/37782900218)的headSha与提交一致，整体及两个任务均success，于2026-10-08 21:19（北京时间）核验。真实PostgreSQL17/SQLite共216项全部通过、无跳过（128.71s），合并覆盖率95.01%；Windows/Linux mypy均61文件通过、Ruff/格式/契约/30项目录检查通过。前端22项单元、构建与13条Chromium流程通过（29.0s）。

远程验证涵盖真实模型日值、双数据库并发/幂等/租约和审计恢复；本机PG仍未运行，以CI补验服务器数据库。当前未合并保护分支、未公开部署，远程无release目标分支、无指定人工审查者；不把工具检查称为人工审核。本文件/progress/协作说明在后续文档提交同步，提交编号可查Git日志。

## 下一步

M3.2潜在计算子链路完成，M3整体仍进行中。继续授权天气源/站点适配、品种来源/许可与当地实测验证，确定移栽和水田灌排/施肥语义。地图、无人机反射率/LAI和有界校准按后续模块实施，production与备份恢复留至M7。

依据：[PCSE官方文档](https://pcse.readthedocs.io/en/stable/code.html)、[PCSE6.0.13官方包](https://pypi.org/project/pcse/6.0.13/)。软件测试仅证明链路、单位和存储行为，不构成华南水稻准确性结论。
