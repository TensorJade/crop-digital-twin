# 2026-10-09 M3.3 天气源与站点目录

- 人员：Codex；日期采用客户端北京时间2026-10-09。
- 基线：2629b8e4eb3dd4feca447e7d241ac51d5682351b，已核验上一轮PCSE代码/日志；工作区初始干净。
- 本地release_20261008快进至上述基线后建立codex/feature_weather_20261009；未推送或合并远程发布分支。
- 软件/API/Web0.6.0，算法包0.3.1，PCSE6.0.13，模型适配1.0.1、NASA转换1.0.0；输入/结果契约1.0.0。
- 用户授权继续模块开发并push代码/日志。华南水稻已确认，具体品种/县市和授权站点接口未提供；可选询问后按公开网格历史天气推进，没有假定拥有中国气象局接口。

## 本轮交付与设计

地块坐标→NASA UTC小时资料→完整北京时间日值→页面预览/CSV→追加天气资料及原始响应→冻结输入→已有真实PCSE计算。附近NOAA目录单独显示位置/距离/历史覆盖，observations_connected=false，不把网格值归属目录站点。

复用input_assets、快照、组织/角色/审计、任务与worker，没有新表/迁移/Redis/外部包。两条新GET先短SQL校验再释放连接联网；标准库固定HTTPS白名单、禁止重定向、15秒socket超时、上游并发2、响应/资料体积限制。1–120已结束历史日，完整24小时、单位/填充值检查，异常不补零。A/B仍来源声明，缺少可保存资料但不可计算。

实现位置：api/v1/weather.py/input_schemas.py；infrastructure/weather/{http,power,sources,stations}.py；domain/simulation/weather.py；前端WeatherSourcePanel.vue/weatherApi.ts与SimulationInputsPanel入口；算法结果扩展weather_method来源/哈希。目录、接口、数据流、请求/响应、来源和边界见[模块设计](../modules/weather-sources.md)、[ADR0006](../adr/0006-weather-sources.md)。

## 官方核对与真实联网烟雾

查阅NASA小时API/数据FAQ、NOAA ISD/实际isd-history.csv、FAO露点公式和NASA/NOAA使用政策。AG单位为C、C、m/s、mm/hour、MJ/hr；使用time-standard=UTC，不能把UTC日值只改成北京时间标签。POWER存在数日延迟，不声称当天实时。

完成的WeatherSources和Pydantic响应模型实际请求公开示例点23.1°N、113.2°E，2024-03-02至03，成功返回2日，源API v2.10.2。首日小时派生最低6.4℃、最高19.12℃、降水0.54mm、辐射7.64MJ/m²、风速3.534583m/s、蒸汽压0.870197kPa，仅为该公开网格资料示例。原始响应规范哈希e54142ebb240b2211619182835a59d25a9cc551f80129cf97fef99fff304c099。

实际目录响应约2.91MB，筛选5个候选；最近BAIYUN INTL（592870-99999）约34.01km，目录覆盖1945-11-30至2025-08-24。历史结束日期说明目录不等于当前观测可用保证。真实响应仅留在忽略runtime/，没有提交大目录、外部气象数据或写运行数据库。

## 本地检查

| 检查 | 实际结果 |
|---|---|
| 锁定依赖 | uv同步65项；无新增外部包，工作区版本同步 |
| 后端/算法pytest覆盖率 | 248项中165通过、83项本机PG因未配置测试URL而跳过，95.40% |
| 前端单元/类型/ESLint/Prettier | 24项单元、类型/静态/格式通过 |
| 构建 | Vue/TypeScript/Vite构建通过；模板事件修正后重新验证 |
| Ruff、双平台mypy/契约/目录 | Ruff check/format通过；Windows/Linux mypy69文件通过；24路径/31操作契约一致；34项工作区文件检查通过 |
| 浏览器 | 最终全量14条Edge流程通过（36.2s），含真实PCSE；桌面/390px天气截图已查看，无横向溢出 |

PCSE私有子进程仍以真实黑盒和浏览器执行验证，不合并到父pytest行覆盖率；数值可执行不作为农艺精度证据。新增单元/API覆盖前日小时边界、完整性、单位、日期范围、来源一致性、无SQL联网、跨组织/只读、失败无写入、目录缓存及传输限制。

验收响应power-hourly.json和weather-stations.csv均自行构造，合成辐射用于软件测试，站点名含SOFTWARE TEST，不是实际NASA/NOAA记录或农户数据。e2e_api仅在已验证test/OS临时库后注入客户端，页面来源显式标记软件验收；计算仍执行真实worker/PCSE。

开发中修正单元Plot构造的关键字字段；浏览器先发现Prettier处理多条内联事件后导致Vue模板解析错误，改为命名函数；预览改为语义section以提供可访问区域；CSV验收改为数值比较，避免20与20.0的格式差异；手机截图发现嵌套网格内在宽度引起溢出，调整min-width/网格列/局部padding与按钮间距，最终复核记录在下方。失败运行没有标成通过。

首次全量Edge中天气/其余12条通过，第一条旧农田流程超时：列表尚在加载时isVisible看到按钮，空列表返回后自动展开表单并移除按钮，click等待已消失元素。修正验收辅助函数先等待“正在读取地块”状态结束再判断入口，没有固定sleep或增加重试掩盖问题；重跑全量14条通过。mypy显式纳入新的e2e_weather.py，两个平台均69源文件通过。

收尾只读核对：运行SQLite迁移0004_simulation_runs、11张业务表数量均零；没有新增运行数据。OpenAPI0.6.0/24路径/31操作，Markdown本地链接通过；uv锁文件检查/同步通过，Ruff格式88文件通过，git diff --check通过。真实烟雾/浏览器截图/下载保存在忽略runtime/test-results，没有进入提交。

## Git、CI与收尾

实现和日志按既有授权推送功能分支；提交号、远程检查和最后工作区状态在检查完成后追加。远程无release目标分支、无指定人工审查者；自查/工具验证不称正式人工审核。未公开部署，M7生产保护不变。

## 后续范围

M3整体继续进行：授权站点观测、120天以上分段合并、具体品种来源与当地实测验证、移栽水田/灌排/施肥语义尚待交付。卫星地图、无人机反射率/LAI和有界校准按M4–M6实施。当前天气日值不保证当地精度，新增来源元数据不改变潜在模型数值方法。

依据：[NASA POWER小时API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/)、[数据/延迟](https://power.larc.nasa.gov/docs/faqs/data/)、[NOAA ISD](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database)、[FAO气象数据](https://www.fao.org/4/x0490e/x0490e07.htm)。
