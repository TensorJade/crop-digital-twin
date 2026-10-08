# 基础设施

`compose/compose.dev.yaml` 仅配置本地 PostgreSQL/PostGIS 和 Redis，端口绑定 127.0.0.1，数据保留在 Docker 命名卷。API 还没有数据库驱动、迁移或连接配置。

```powershell
# 在仓库根目录运行，修改 .env 中的本地密码后启动
Copy-Item .env.example .env
docker compose --env-file .env -f infra/compose/compose.dev.yaml config --quiet
docker compose --env-file .env -f infra/compose/compose.dev.yaml up -d
# 停止保留数据；不要随意使用 down -v
docker compose --env-file .env -f infra/compose/compose.dev.yaml down
```

镜像标签是开发基线，不代表最新补丁或生产安全审计；正式部署前锁定 digest、验证版本及升级策略。当前未拉取/启动容器、未验证数据库读写、未建立备份恢复。对象存储、API 镜像、HTTPS 代理、监控与备份目录只是预留位置。
