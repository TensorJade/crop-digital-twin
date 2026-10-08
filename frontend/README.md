# 前端（TypeScript / Vue SFC / CSS）

登录后进入华南水稻页面：选地块 → 选种植季 → 记农事。管理员可切换“成员与记录”，创建农田管理/只读账号并启停成员，查看操作审计。所有成员可修改自己的密码，修改后重新登录。

features/farm 集中农田组件；features/identity 集中会话与密码；features/simulation 集中土壤/品种/天气导入、资料分页选择、输入检查、版本历史与 JSON 下载。App 组合登录/工作区，退出或会话失效时清空身份并卸载旧工作区。共享 HTTP 仅内存保存 CSRF，Cookie 由浏览器同源携带，不存 localStorage 或返回登录令牌。

本季“农事记录”和“模拟资料”切换操作；输入要求明确来源/许可、日期和单位，不提供默认试点参数或虚构天气。详细缺参数清单折叠供参数提供者查看，默认向农户显示补充提示。

切换地块/季节按请求代次丢弃过期响应。数量展示原始单位及换算量，默认隐藏旧版，修正保留原因。只读账号隐藏写操作；权限仍由后端强制校验。桌面与手机均有真实浏览器验收。

尚未加入 Router/Pinia；地图 SDK 按模块引入。类型目前手写，真实接口以 contracts/openapi.* 为准。

```text
npm run typecheck / lint / format:check / test / build
npx playwright install chromium
npm run test:e2e
```

Playwright 自动启动 8019 API、5179 Vite 和已迁移临时 SQLite；仅该临时库建立测试账号。Windows 可运行根目录 scripts/check-e2e.ps1 -BrowserChannel msedge。单元与浏览器测试分别发现文件。验收说明见 tests/e2e/README.md（仓库根目录）。

Vite 代理供联调，dist 的 API 请求需正式代理。手工输入/快照已实现，自动天气与实际生长模拟/地图尚未实现，生产部署需后续验收。
