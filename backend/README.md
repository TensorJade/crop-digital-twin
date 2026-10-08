# 后端（Python / FastAPI）

`main.py` 为应用入口；`api/v1` 负责 HTTP 契约；`application` 编排业务用例与事务；`domain` 保持业务规则独立；`infrastructure` 实现数据库、天气、对象存储与消息适配；`workers` 承载未来的重计算任务。

目前只实现 `GET /api/v1/health`（无请求体、无需认证、200 JSON、仅进程存活）。开发连接采用本机 HTTP；正式部署需 HTTPS。自动接口文档在 `/docs`，实际契约在根目录 `contracts/openapi.*`。

尚无 ORM、数据库连接、迁移、登录、业务接口、任务 worker 或生产部署。保留的 `.gitkeep` 目录仅表示模块位置。
