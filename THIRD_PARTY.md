# 第三方组件与数据源

依赖的完整精确版本以 uv.lock 和 frontend/package-lock.json 为准。本清单记录关键科学组件的来源与用途，不代表全部第三方发布义务已完成。

| 组件 | 锁定版本 | 用途 | 官方来源 / 许可 |
|---|---|---|---|
| PCSE | 6.0.13 | Wofost72_PP 潜在生产、天气容器、参考蒸散量 | [官方包](https://pypi.org/project/pcse/6.0.13/)、[代码](https://github.com/ajwdewit/pcse)；EUPL1.1 或欧盟批准的后续版本，原版权/许可声明见 [PCSE-LICENSE](docs/licenses/PCSE-LICENSE.txt) |

本仓库不修改 PCSE 源码，通过依赖管理安装官方包。PCSE-LICENSE.txt 保留官方 wheel 的版权/许可声明，声明含官方许可获取链接；它并非完整许可证正文。源码和许可使用条件以官方发行包为准，公开发布前在 M7 完成完整第三方许可、通知与分发义务审查。

PCSE 使用固定的 Wofost72_PP，调用 ParameterProvider、WeatherDataProvider、WeatherDataContainer 和 reference_ET；配置由适配器固定，不接受用户脚本/模型路径。临时配置和空演示库标记隔离导入副作用，不把官方 demo 数据库或 DAO 用于业务，不下载外部天气或参数。

数值测试资料是本项目自行构造的合成参数/天气，仅验证软件接口。没有复制官方水稻品种参数为产品默认值，没有包含受限制气象站、卫星底图、原始影像或训练权重。来源/使用许可仍由每份输入资料明确记录；真实农艺参数与数据授权需在试点确认。

其他基础组件包括 FastAPI/SQLAlchemy/Alembic/Psycopg/argon2-cffi、Vue/Vite/TypeScript、Playwright；科学包的传递依赖由 uv.lock 固定。后续发布须按各实际发行包整理完整清单。

## M3.3 外部数据与公式

| 来源 | 用途 | 官方资料 |
|---|---|---|
| NASA POWER Hourly/Point（AG、UTC） | 历史网格天气 | [小时 API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/)、[数据说明](https://power.larc.nasa.gov/docs/faqs/data/)、[数据许可政策](https://science.data.nasa.gov/about/license) |
| NOAA NCEI ISD 历史目录 | 附近站点候选 | [ISD 说明](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database)、[目录](https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv)、[数据使用说明](https://www.noaa.gov/office-education/outreach-communication/faq) |
| FAO56 气象公式 | 露点转蒸汽压 | [气象章节](https://www.fao.org/4/x0490e/x0490e07.htm) |

NASA 资料保存响应 header/API 版本、请求、获取时间、原始 JSON 和哈希，转换适配器为 1.0.0。保留 POWER 和实际数据源说明，按数据政策及访问条款使用；天气数据许可需独立于客户端软件许可核对。

NOAA 目录记录原始字节 SHA-256 和获取时间，缓存 24 小时，显示 200km 内候选及历史覆盖。站点观测和 CMA 接口尚未接入。

FAO 露点公式在代码中重新实现，并注明出处，未复制全文或图表。

天气获取使用 Python 标准库 urllib。公网检查响应保存在忽略的 runtime，提交的小时和目录 fixture 为自行构造的测试资料。POWER 提供历史网格资料，有数日延迟，田间误差需另外评估。试点站点授权、地图许可和发布分发事项在对应模块及 M7 确认。
