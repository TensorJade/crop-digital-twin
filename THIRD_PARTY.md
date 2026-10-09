# 第三方组件与本轮科学依赖

依赖的完整精确版本以 uv.lock 和 frontend/package-lock.json 为准。本清单记录关键科学组件的来源与用途，不代表全部第三方发布义务已完成。

| 组件 | 锁定版本 | 用途 | 官方来源 / 许可 |
|---|---|---|---|
| PCSE | 6.0.13 | Wofost72_PP 潜在生产、天气容器、参考蒸散量 | [官方包](https://pypi.org/project/pcse/6.0.13/)、[代码](https://github.com/ajwdewit/pcse)；EUPL1.1 或欧盟批准的后续版本，原版权/许可声明见 [PCSE-LICENSE](docs/licenses/PCSE-LICENSE.txt) |

本仓库不修改 PCSE 源码，通过依赖管理安装官方包。PCSE-LICENSE.txt 保留官方 wheel 的版权/许可声明，声明含官方许可获取链接；它并非完整许可证正文。源码和许可使用条件以官方发行包为准，公开发布前在 M7 完成完整第三方许可、通知与分发义务审查。

PCSE 可执行边界仅为固定 Wofost72_PP，调用 ParameterProvider、WeatherDataProvider、WeatherDataContainer 和 reference_ET；配置由适配器固定，不接受用户脚本/模型路径。临时配置和空演示库标记隔离导入副作用，不把官方 demo 数据库或 DAO 用于业务，不下载外部天气或参数。

数值测试资料是本项目自行构造的合成参数/天气，仅验证软件接口。没有复制官方水稻品种参数为产品默认值，没有包含受限制气象站、卫星底图、原始影像或训练权重。来源/使用许可仍由每份输入资料明确记录；真实农艺参数与数据授权需在试点确认。

其他基础组件包括 FastAPI/SQLAlchemy/Alembic/Psycopg/argon2-cffi、Vue/Vite/TypeScript、Playwright；本轮新增科学包的传递依赖也在 uv.lock 锁定。后续发布须按各实际发行包整理完整清单。

## M3.3 外部数据与公式

| 来源 | 用途与版本记录 | 官方使用信息 |
|---|---|---|
| NASA POWER Hourly/Point（AG、UTC） | 地块历史网格；实际响应header/API版本、请求/获取时间和原始JSON/hash随资料封存，转换适配1.0.0 | [小时API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/)、[数据/单位/延迟](https://power.larc.nasa.gov/docs/faqs/data/)、[NASA公开数据许可政策](https://science.data.nasa.gov/about/license)；保留POWER及实际数据来源，按适用政策/访问条款使用，不把第三方客户端的软件许可当成天气数据许可 |
| NOAA NCEI ISD历史站点目录 | 200km内候选位置/距离/历史覆盖；目录原始字节SHA-256/获取时间，内存缓存24h | [ISD说明](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database)、[实际目录](https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv)、[NOAA数据使用说明](https://www.noaa.gov/office-education/outreach-communication/faq)；保留来源，不声称取得CMA授权或站点实时观测 |
| FAO56气象公式 | 由小时露点计算蒸汽压后平均，公式重新实现 | [官方章节](https://www.fao.org/4/x0490e/x0490e07.htm)，采用公式并注明出处，未复制全文或图表 |

本轮使用Python标准库urllib，不增加第三方天气SDK。实际外部响应只在忽略runtime/做烟雾验证，不进入Git；提交的小时/目录fixture均为项目自行构造的合成测试资料。POWER为历史网格、存在数日延迟，派生日值和网格海拔不等于农田实测。具体试点授权站点、公开地图许可和生产分发义务继续在相应模块/M7核对。
