# ADR 0005：PCSE 潜在模式与后台计算

日期：2026-10-08。模块：M3.2。

使用 M3.1 输入快照，固定 PCSE 6.0.13 的 Wofost72_PP。首个模式计算直播出苗后的潜在生长，假定水肥充足，使用已发生的北京时间逐日天气，提交前需确认模式条件。移栽、水田灌排和施肥响应另行适配。

任务和结果使用一张 SQL 表，HTTP 校验后入队，独立 worker 领取租约并在限时子进程计算。计算时释放 SQL 写锁；请求 key 去重，新计算保留版本，过期任务可以重新领取，租约令牌防止迟到写回。当前无需 Redis、Celery 或通用队列框架。

PCSE 用户配置、日志和演示库在临时目录初始化，进程不继承应用凭据。空演示库标记用于隔离默认初始化，业务存储使用本项目 SQL 模型。输入为限定结构 JSON，不执行用户 Python/YAML，不读取任意 URL。Angstrom 系数由资料提供者填写。

参考：[PCSE 模型与天气](https://pcse.readthedocs.io/en/stable/code.html)、[PCSE 6.0.13](https://pypi.org/project/pcse/6.0.13/)。
