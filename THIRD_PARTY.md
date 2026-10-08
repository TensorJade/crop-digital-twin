# 第三方组件与本轮科学依赖

依赖的完整精确版本以 uv.lock 和 frontend/package-lock.json 为准。本清单记录关键科学组件的来源与用途，不代表全部第三方发布义务已完成。

| 组件 | 锁定版本 | 用途 | 官方来源 / 许可 |
|---|---|---|---|
| PCSE | 6.0.13 | Wofost72_PP 潜在生产、天气容器、参考蒸散量 | [官方包](https://pypi.org/project/pcse/6.0.13/)、[代码](https://github.com/ajwdewit/pcse)；EUPL1.1 或欧盟批准的后续版本，原版权/许可声明见 [PCSE-LICENSE](docs/licenses/PCSE-LICENSE.txt) |

本仓库不修改 PCSE 源码，通过依赖管理安装官方包。PCSE-LICENSE.txt 保留官方 wheel 的版权/许可声明，声明含官方许可获取链接；它并非完整许可证正文。源码和许可使用条件以官方发行包为准，公开发布前在 M7 完成完整第三方许可、通知与分发义务审查。

PCSE 可执行边界仅为固定 Wofost72_PP，调用 ParameterProvider、WeatherDataProvider、WeatherDataContainer 和 reference_ET；配置由适配器固定，不接受用户脚本/模型路径。临时配置和空演示库标记隔离导入副作用，不把官方 demo 数据库或 DAO 用于业务，不下载外部天气或参数。

数值测试资料是本项目自行构造的合成参数/天气，仅验证软件接口。没有复制官方水稻品种参数为产品默认值，没有包含受限制气象站、卫星底图、原始影像或训练权重。来源/使用许可仍由每份输入资料明确记录；真实农艺参数与数据授权需在试点确认。

其他基础组件包括 FastAPI/SQLAlchemy/Alembic/Psycopg/argon2-cffi、Vue/Vite/TypeScript、Playwright；本轮新增科学包的传递依赖也在 uv.lock 锁定。后续发布须按各实际发行包整理完整清单。
