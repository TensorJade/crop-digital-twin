# 作物算法包（Python）

包0.3.0包含inputs.py纯天气CSV/参数结构/单位/规范JSON与哈希检查，potential.py运行条件和隔离协议，pcse_runner.py真实PCSE6.0.13 Wofost72_PP。算法不依赖HTTP/数据库，PCSE只在私有临时子进程导入，父进程不产生默认配置/演示库副作用。

天气日期不重复、不超未来、不补缺测。雨mm→cm、辐射MJ/m²→J/m²、蒸汽压kPa→hPa，风速为2m；reference_ET(PM)输出mm/day，除10传WeatherDataContainer E0/ES0/ET0。Angstrom A/B需来源提供，检查单项及总和，不猜测当地值。

静态完整性不等于全部生理/农艺校验。潜在模式仅支持直播实际出苗、完整rice/WOFOST72参数与北京时间连续已发生天气，最多366日。输入报告simulation_available是满足此模式输入，不是模型已运行。结果输出LAI、DVS、TAGP/TWSO干物质与规范天气，真实成功simulation_executed=true；agronomically_validated=false、management_effects_applied=false。

真实PCSE仅在60s限时隔离子进程运行，输入最多1MiB、输出512KiB；固定模型配置、白名单环境、临时用户配置，不下载天气/参数，不执行用户Python/YAML。版本和许可见根THIRD_PARTY.md。软件测试用自行构造的合成参数，不提供华南生产默认品种；移栽、水田管理/精度及遥感校准以后独立实施。

规范JSON排序键、UTF-8、禁止NaN，整数值浮点归一为整数（负零为零）。scripts/verify_input.py可核验输入/结果下载的payload/hash；仅证明内容一致，非签名、来源认证或农艺验证。真实PCSE子进程以黑盒执行测试验证，其行覆盖不合并到父pytest覆盖率。
