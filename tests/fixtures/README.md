# 软件测试资料

以下资料由本项目自行构造，不含农户数据或官方品种参数。

| 文件 | 内容 | 检查用途 |
|---|---|---|
| potential-input.json | 未校准合成品种及天气 | PCSE 执行、单位、确定性、隔离和模块交互 |
| power-hourly.json | 72 小时、五个变量、UTC 单位及 crop_twin_test 标签 | 日值转换、日期边界和保存 |
| weather-stations.csv | 两个附近和一个远处的示例候选 | 距离筛选和目录处理 |

合成小时资料包含夜间辐射值，站点名称带 SOFTWARE TEST、编号为软件样例。它们不对应实际 POWER 响应或 NOAA 站点。potential-input.json 中的品种明确标为“软件验收合成品种（未校准）”，仅供软件测试。

运行库、页面默认模板和管理员初始化不加载这些资料。e2e_api.py 检查 test 环境及临时 SQLite 路径后才注入 scripts/e2e_weather.py 客户端，页面来源标为“软件验收合成响应”。公网检查资料保存在忽略的 runtime，结果另记在开发日志中。农艺评价和生产决策使用实测及经验证的资料。
