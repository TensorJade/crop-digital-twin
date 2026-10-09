# 作物算法包（Python）

版本 0.3.1，处理输入检查和潜在生长计算。

| 文件 | 职责 |
|---|---|
| inputs.py | CSV、参数、单位、规范 JSON 和哈希检查 |
| potential.py | 运行条件、输入复查和子进程协议 |
| pcse_runner.py | 在临时进程执行 PCSE 6.0.13 Wofost72_PP |

算法包无 HTTP 或数据库依赖，PCSE 仅在私有临时子进程导入。计算最长 60 秒，输入上限 1MiB、输出上限 512KiB。使用固定模型、环境白名单和临时配置，不执行用户 Python/YAML，也不下载参数或天气。版本和许可见根 THIRD_PARTY.md。

天气要求连续、日期不重复且已发生，最多 366 日，缺测时拒绝运行。雨量 mm 转 cm、辐射 MJ/m² 转 J/m²、蒸汽压 kPa 转 hPa，风速为 2m。reference_ET(PM) 的 mm/day 除以 10 后传入 E0/ES0/ET0。Angstrom A/B 由来源提供者声明，检查单项和总和。

潜在模式要求直播实际出苗、完整 rice/WOFOST72 参数和北京时间天气。`simulation_available` 表示满足输入条件，成功结果标记 `simulation_executed=true`，输出 LAI、DVS、TAGP、TWSO 和规范天气。`agronomically_validated=false`、`management_effects_applied=false`；移栽、水田管理和当地验证待完成。测试使用合成参数，系统不预置生产默认品种。

规范 JSON 使用排序键、UTF-8，禁止 NaN，整数值浮点转为整数，负零转为零。scripts/verify_input.py 检查下载文件的 payload/hash 一致性。来源认证和农艺验证另外处理。PCSE 子进程用独立执行测试检查，不计入父 pytest 行覆盖率。

模型适配器 1.0.1 增加 weather_method.source_kind、raw_hash 和网格使用条件。NASA 获取和 UTC+8 转换位于后端，算法读取快照中的日值与来源，不重新联网；旧结果保留。
