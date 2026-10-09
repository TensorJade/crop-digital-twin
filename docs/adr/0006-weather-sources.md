# ADR0006：天气预览与资料保存分开

2026-10-09，M3.3。复用已有input_assets和冻结快照，不增加天气任务表/Redis/通用数据平台。管理员按地块坐标点击获取NASA POWER历史网格天气；先预览，再复用现有POST/input-assets保存。原始小时响应、请求、获取时间、内容哈希和逐日转换方法随资料封存。预览不写运行数据库。

NASA固定Hourly/AG/UTC接口，取起始日之前一日，按UTC+8日期标记汇总；每一天必须有24小时的五个变量，缺测/非法单位/填充值拒绝，不补零。逐小时温度的最小/最大不是站点日极值；2m风速平均、降水和辐射累加、露点转换的蒸汽压平均。每次最多120日，适配结果继续遵守512KiB资料与1MiB快照上限，超过明确拒绝。Angstrom A/B仍由资料提供者声明，不生成当地默认值。

NOAA ISD公开目录用于地块附近站点位置/距离候选搜索，不拉取或补造站点观测，不把候选站点标作NASA数据来源。目录含历史覆盖起止，不证明当前站点活跃或所需变量完整。目录仅在明确查询时获取，进程内缓存24小时。

两个GET操作在短SQL事务中完成认证、角色、组织地块校验，随后关闭SQL再联网；没有HTTP期间的数据库写锁。只读成员可查看已保存天气，不触发外部请求。网络目的地固定HTTPS，禁止重定向、限制响应大小与并发、超时后返回安全错误，接口不接受URL。数据获取不定时后台运行。

用官方网络响应做开发烟雾验证，自动测试以独立合成响应隔离网络；浏览器只在已经验证的test临时数据库注入测试天气客户端，运行服务没有测试数据开关。实际气象站授权观测、连续长季分段合并、当日更新/预测与水田验证继续实施。

依据：[NASA POWER小时API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/)、[数据源/单位/延迟](https://power.larc.nasa.gov/docs/faqs/data/)、[NOAA ISD](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database)、[FAO气象数据](https://www.fao.org/4/x0490e/x0490e07.htm)。
