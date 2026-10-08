# 作物算法包（Python）

包版本 0.2.0，当前交付 inputs.py：天气 CSV 解析、原始单位到 PCSE 字段的转换、WOFOST72 参数结构和静态完整性检查、规范 JSON 与 SHA-256。纯函数不依赖 API、数据库、网络或 PCSE 运行环境。

天气日期不重复、不超未来、不补缺测；雨量 mm→cm、辐射 MJ/m²→J/m²、蒸汽压 kPa→hPa，风速必须为 2m 观测。保留原值，超出 PCSE 标准范围时在预检阻塞。E0/ES0/ET0 尚未计算，输出并非已可运行的 WeatherDataProvider。

完整性清单核对 PCSE6.0.13 的 WOFOST72 组件 ParameterTemplate，不构成全部生理校验。input_ready 只表示本阶段资料静态完整，simulation_available 恒为 false。测试参数为软件检查合成数据，不是可用于华南水稻的参数集。

M3.2 再加入真实 pcse_adapter、管理和天气适配，确定水田与移栽过程、来源许可和实测验证。PCSE 尚未作为依赖安装；不得用旧项目演示曲线替代模型。遥感反演、有界校准以后独立交付，不添加假运行接口。

规范 JSON 按键排序、UTF-8、禁止 NaN，将整数值浮点数归一为整数（包括负零归一为零），使浏览器导出再读取的哈希一致。离线核验入口 scripts/verify_input.py；校验和只检测内容一致性，不是签名或农艺验证。
