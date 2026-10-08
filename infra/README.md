# 基础设施

compose/compose.dev.yaml 配置开发 PostgreSQL/PostGIS 与预留 Redis，端口绑定 127.0.0.1，数据保留在命名卷。M1 可连接 PostgreSQL，但默认使用 SQLite；Redis 尚未接入。

```powershell
# 仅当 .env 不存在时复制；之后填写本地密码
Copy-Item .env.example .env
docker compose --env-file .env -f infra/compose/compose.dev.yaml config --quiet
# M1 只启动 postgres；Redis 留待任务模块
docker compose --env-file .env -f infra/compose/compose.dev.yaml up -d postgres
# 设置 .env 内 CROP_TWIN_DATABASE_URL，然后运行增量迁移
.\scripts\init-db.ps1
# 停止保留数据；不要随意使用 down -v
docker compose --env-file .env -f infra/compose/compose.dev.yaml down
```

镜像标签为开发基线，不代表补丁或生产审计；正式部署锁定 digest 并验证升级策略。本机 Docker 未运行；CI 用 PostgreSQL 17 验证 M1 SQL，不证明 PostGIS 空间功能、备份恢复或生产容量。对象存储、API 镜像、HTTPS、监控和备份尚待实施。
