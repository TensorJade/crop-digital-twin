# ADR 0006：天气预览与保存

日期：2026-10-09。模块：M3.3。

天气获取先返回预览，再通过现有 POST /api/v1/input-assets 保存版本，沿用输入表、快照和审计。保存原始小时响应、请求、获取时间、哈希和日值转换方法，预览不写业务数据。

NASA 使用固定 Hourly/AG/UTC 接口，取起始日前一日，按 UTC+8 汇总。每天要求五个变量各有 24 小时，缺测、非法单位和填充值拒绝保存。风速和露点派生蒸汽压取平均，降水和辐射累加，温度取小时最小及最大值。每次最多 120 日，资料上限 512KiB、快照上限 1MiB。Angstrom A/B 由资料提供者填写。

NOAA ISD 目录用于查找附近站点位置、距离和历史覆盖日期，暂未接入观测。NASA 网格资料保持自己的来源标记，目录在明确查询时获取并缓存 24 小时。

两个 GET 先在短 SQL 事务中完成会话、角色和组织地块检查，关闭连接后请求固定 HTTPS 数据源。禁止重定向，限制响应大小、并发和超时，接口不接受 URL。只读成员可以查看已有资料，不能触发外部获取；目前没有定时后台获取任务。

公网检查和自动测试分别记录。自动测试使用合成响应，仅在 test 临时库注入，运行服务不提供测试天气开关。后续接入授权站点观测、长季分段合并、当天更新及水田验证。

参考：[NASA POWER 小时 API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/)、[数据、单位和延迟](https://power.larc.nasa.gov/docs/faqs/data/)、[NOAA ISD](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database)、[FAO 气象数据](https://www.fao.org/4/x0490e/x0490e07.htm)。
