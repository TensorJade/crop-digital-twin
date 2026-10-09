# 本地开发运行手册

在仓库根目录执行 bootstrap → init-db → create-admin（交互设置密码）→ 分别启动API、前端与worker。用 Ctrl+C 停止自己的进程。默认 SQLite 无需 Docker，没有默认运行账号；完整命令见根 README。

## 存储与升级

不使用 .env 时默认 runtime/crop_twin.db。需要自定义时复制 .env.example 为 .env，不覆盖已有 .env。迁移、管理员初始化和 API及worker脚本读取同一CROP_TWIN_DATABASE_URL。

从 M1 升级先运行 init-db。旧地块保持保存，organization_id 为空时不会向用户开放。若确需把全部未归属旧地块归入此次新组织，在 create-admin 命令增加 -AdoptLegacy；没有该标记会拒绝创建且回滚，不自动给第一个用户授权。已有归属不会转移。迁移不要降级或重置真实数据。

PostgreSQL URL 格式：postgresql+psycopg://用户:URL编码后的密码@127.0.0.1:5432/数据库。先创建数据库/用户，或按 infra/README 启动开发 postgres；设置 URL 后 init-db。修改 URL 不搬迁 SQLite 数据，跨库迁移需另行设计验证。

本机 Docker daemon 未运行。CI 使用 PostgreSQL 17；空间扩展留待地图模块。Redis不参与当前模块，计算使用SQL任务表。

从 0.3.0 升级执行 init-db 至 0003，只增加两张输入表，不需重建账号。不得降级运行库来清理输入历史。

## 输入资料与导出

选择本组织地块和种植季，切换“模拟资料”。登记土壤体积含水率和深度，导入农艺提供者准备的 JSON 参数，再导入列名为 date,tmin_c,tmax_c,rain_mm,radiation_mj_m2,wind_m_s,vapor_kpa 的 UTF-8 天气 CSV。页面可下载只有表头的 CSV，不提供虚构天气。所有资料填写来源/使用许可，天气另填真实来源坐标、海拔、站点/网格、日界；风速为 2m，蒸汽压不是相对湿度。

明确实际出苗日和截止日，检查后可保存输入快照；未补齐时仍保存明确的待补齐报告。新增资料不覆盖旧版本，管理更正后需另存快照。只读成员可查看/下载。下载 JSON 后在本地核验：

```powershell
& .tools\uv\Scripts\uv.exe run --locked python scripts/verify_input.py 'C:\path\to\rice-input.json'
```

PASS仅表示payload校验和一致，不表示模型运行、来源认证或精度验证。资料上限512KiB，天气CSV256KiB/366天，快照1MiB，核验文件上限2MiB。M3.3已支持历史网格获取/附近站点目录，站点观测尚未接入。可下载实际PCSE结果并用同一verify_input.py核验，PASS仍不证明农艺精度。

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
3. 503：STORAGE_UNAVAILABLE检查init-db、数据库连接和权限；WEATHER_NETWORK_FAILED等天气错误检查外部网络/源状态，或缩短历史日期/改用已有CSV，不重置数据库。
4. 401：重新登录。403：核对角色，刷新会话；自定义页面核对 Origin/CSRF。
5. 409：刷新季节/农事或成员列表，检查日期、修订版本或重复账号。
6. 429：等待登录失败窗口结束，核对账号密码，避免持续重试。
7. production 启动失败：当前 M7 部署与发布验收未完成。

备份恢复和公开部署未实现；backups/ 目录不代表备份完成。不要随意 docker down -v 或降级真实数据库。

## 0.5.0升级与生长计算

先bootstrap安装锁定科学依赖，再init-db到0004；已有组织/账号继续使用，不修改原输入。第三个终端运行start-worker.ps1，与API同数据库；-Once最多处理一个可领取任务。计算之前在“模拟资料”重新导入补齐系数的天气并保存新快照，历史0.4快照不补写。

天气表单折叠的“模型计算资料”由来源提供者填写Angstrom A/B，两者同时提供，A=0.1–0.4、B=0.3–0.7、和=0.6–0.9。仅直播已出苗、连续北京时间已发生天气与完整品种参数可计算，最多366日。进入“生长计算”选可运行快照、明确确认潜在模式后排队。日期滑块、指标曲线、历史及JSON导出供所有本组织成员查看。

排队未变化：检查worker终端是否运行、同库、已迁移。运行中断：启动worker，120s租约到期后可重新领取，最多三次。确定失败：核对页面安全提示，必要时修改资料保存新快照，重新计算保留旧记录。不要直接改SQL状态/哈希/租约。输入simulation_available只表示输入条件，不是worker存活检查。

计算假定水肥充足，真实农事灌排/施肥尚无效应；移栽暂拒绝。不用合成验收品种生产决策，贮藏器官干物质不当作实收产量。模型精度与软件通过分别验收。

## 0.6.0 天气获取

从0.5.0升级运行bootstrap同步版本，迁移仍0004，无新增包/表。API机器需HTTPS访问NASA POWER/NOAA，启动不会自动获取。登录后选地块/季节，在“模拟资料→按农田位置获取天气”填写历史起止日（最早2001-01-02、1–120已结束日），点击预览再保存，或先下载CSV检查；POWER近期资料常延迟数日，不将昨天一定可用作为保证。

保存保留原始小时JSON/请求/日值/hash，若CSV或来源内容不同则拒绝并提示重新获取；不要直接修改SQL。A/B留空可保存，计算前由资料提供者补齐并另存天气版本/输入。超过响应/资料/快照体积上限需缩短日期，当前没有自动拼接超过120天的长季。

“查找附近气象站”获取NOAA目录，缓存24h，显示200km内最多5个候选及历史覆盖。覆盖截止可能早于今天，目录候选不保证当日活跃/所需观测完整；不把候选ID填成NASA来源。已获得的实际站点CSV仍可从原入口导入并声明站点ID/来源。

WEATHER_DATA_INVALID可能为小时缺测、单位改变或源位置不符，整段拒绝、不补零；WEATHER_BUSY等待后手工重试。网络失败不会保存部分天气，自动测试合成响应不用于运行服务。真实源示例、日界/单位与错误码见[天气模块](../modules/weather-sources.md)。
