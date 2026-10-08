# 本地开发运行手册

在仓库根目录执行 bootstrap → init-db → 分别启动 API 与前端。用 Ctrl+C 停止自己的进程。默认 SQLite 无需 Docker，迁移完成后可直接录入。

## 存储配置

不使用 .env 时默认 runtime/crop_twin.db。需要自定义时复制 .env.example 为 .env；不要覆盖已有 .env。初始化脚本和 API 启动脚本读取其中的 CROP_TWIN_DATABASE_URL。

PostgreSQL URL 格式：postgresql+psycopg://用户:URL编码后的密码@127.0.0.1:5432/数据库。密码中的特殊字符需 URL 编码。先创建可用数据库/用户，或按 infra/README 启动开发 postgres 服务；之后设置 URL 并运行 init-db。修改 URL 不会自动搬迁 SQLite 数据；跨库迁移需单独设计、验证。

本机 Docker daemon 未运行，尚未在本机启动 PostgreSQL/PostGIS。CI 对 PostgreSQL 17 进行集成测试；空间扩展留待地图模块。Redis 不参与 M1。

## 验证与隔离

check.ps1 执行静态检查、覆盖率、实际 SQLite 集成、契约一致性、前端测试/构建。PostgreSQL 测试显式读取 CROP_TWIN_TEST_POSTGRES_URL，创建独立 UUID schema，完成后只删除该 schema；建议仅使用测试数据库及允许建 schema 的测试账号。

check-e2e.ps1 自动迁移临时数据库，并占用 8019/5179 测试端口；拒绝复用已有服务，不接触 .env 或运行数据库。默认使用安装的 Playwright Chromium，Windows 可指定 -BrowserChannel msedge。无浏览器时在 frontend 运行 npx playwright install chromium（Linux 需 --with-deps）。失败 trace/screenshot 位于忽略的 test-results/。

## 故障处理

1. Node 版本不符：使用 24.19.0 或 -NodeBinDirectory，不修改其他项目的全局配置。
2. 端口占用：确认进程归属，停止自己的测试/开发服务，不直接结束其他进程。
3. 503 存储不可用：确认 init-db 成功、URL/数据库权限正确；修复后点击重新读取。
4. 409 季节或修订冲突：刷新列表，核对季节日期或选择最新农事版本。
5. 依赖变化：更新锁文件并执行相关检查；接口变化导出 OpenAPI。
6. production 启动失败：当前账户与地块授权未完成，仅支持本地试用。

迁移为增量更新，不重置用户数据；不要随意降级迁移或 docker down -v。备份恢复和公开部署尚未实现，存在 backups/ 目录不代表备份完成。
