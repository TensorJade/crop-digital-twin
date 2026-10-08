# 本地开发运行手册

在仓库根目录执行 bootstrap → init-db → create-admin（交互设置密码）→ 分别启动 API 与前端。用 Ctrl+C 停止自己的进程。默认 SQLite 无需 Docker，没有默认运行账号；完整命令见根 README。

## 存储与升级

不使用 .env 时默认 runtime/crop_twin.db。需要自定义时复制 .env.example 为 .env，不覆盖已有 .env。迁移、管理员初始化和 API 脚本读取 CROP_TWIN_DATABASE_URL。

从 M1 升级先运行 init-db。旧地块保持保存，organization_id 为空时不会向用户开放。若确需把全部未归属旧地块归入此次新组织，在 create-admin 命令增加 -AdoptLegacy；没有该标记会拒绝创建且回滚，不自动给第一个用户授权。已有归属不会转移。迁移不要降级或重置真实数据。

PostgreSQL URL 格式：postgresql+psycopg://用户:URL编码后的密码@127.0.0.1:5432/数据库。先创建数据库/用户，或按 infra/README 启动开发 postgres；设置 URL 后 init-db。修改 URL 不搬迁 SQLite 数据，跨库迁移需另行设计验证。

本机 Docker daemon 未运行。CI 使用 PostgreSQL 17；空间扩展留待地图模块。Redis 不参与 M1/M2。

## 账户与配置

账号为 3–64 位字母、数字、下划线或短横线，首字符为字母或数字，统一小写；密码为 12–128 字符。密码初始化仅交互输入，不放进命令行、配置或日志。组织管理员在页面建成员，只允许农田管理/只读两种角色。M2 不提供公开注册、管理员停用、角色转移或找回密码。

会话到期、退出、成员停用、改密码后需重新登录；重新启用不会恢复旧会话。直接连接来源 15 分钟内五次错误登录后暂时限制，重启不清零；等待窗口结束后再试。开发与验收入口关闭 Uvicorn 代理头解析。若未来使用代理，必须在 M7 验证可信来源配置及限流，不直接信任任意 X-Forwarded-For。

本地 HTTP 的 CROP_TWIN_COOKIE_SECURE=false；HTTPS 部署须启用 Secure。CROP_TWIN_ALLOWED_ORIGINS 是 JSON 数组，按实际页面同源地址设置，当前默认允许 localhost/127.0.0.1 的 5173、8000、5179。业务 POST 需 Cookie、JSON、X-CSRF-Token；页面自动携带。production 仍被 M7 发布保护拒绝启动。

## 验证与隔离

check.ps1 执行静态检查、覆盖率、SQLite 集成、契约一致性、前端测试/构建。PostgreSQL 显式读取 CROP_TWIN_TEST_POSTGRES_URL，在独立 UUID schema 运行，完成后只清理该 schema；仅使用测试库及允许建 schema 的测试账号。

check-e2e.ps1 占用 8019/5179 并拒绝复用已有服务。e2e_api.py 检查 test 环境及 OS 临时目录下 crop-twin-e2e-* SQLite 路径，满足条件后迁移并建立测试账号；不读运行 .env 或写运行库。默认 Chromium，Windows 可用 -BrowserChannel msedge。Linux 安装 Chromium 可附 --with-deps。失败 trace/screenshot 位于忽略的 test-results/；页面验收截图在 runtime/。

## 故障处理

1. Node 版本不符：使用 24.19.0 或 -NodeBinDirectory，不修改全局配置。
2. 端口占用：确认归属，停止自己的服务，不结束其他进程。
3. 503：检查 init-db、URL、连接和权限；修复后重新读取。
4. 401：重新登录。403：核对角色，刷新会话；自定义页面核对 Origin/CSRF。
5. 409：刷新季节/农事或成员列表，检查日期、修订版本或重复账号。
6. 429：等待登录失败窗口结束，核对账号密码，避免持续重试。
7. production 启动失败：当前 M7 部署与发布验收未完成。

备份恢复和公开部署未实现；backups/ 目录不代表备份完成。不要随意 docker down -v 或降级真实数据库。
