# 前端（TypeScript / Vue SFC / CSS）

华南水稻页面：选地块 → 选种植季 → 记农事。features/farm 集中业务组件、API 类型与局部状态；pages/FarmPage.vue 组合页面，components 仅放通用分页。

切换地块/季节按请求代次丢弃过期响应。数量展示原始单位及换算量，默认隐藏旧版，修正保留原因。支持桌面与手机布局。

尚无跨页状态需求，未加入 Router/Pinia；地图 SDK 等按模块引入。类型目前手写，真实接口以 contracts/openapi.* 为准。

```text
npm run typecheck / lint / format:check / test / build
npx playwright install chromium
npm run test:e2e
```

Playwright 自动启动 8019 API、5179 Vite 和已迁移临时 SQLite。Windows 可运行根目录 scripts/check-e2e.ps1 -BrowserChannel msedge。*.test.ts 为单元，tests/e2e/*.spec.ts 为浏览器测试，各运行器分别发现文件。

Vite 代理仅供联调；dist 的 API 请求需正式代理。当前无生产发布、账户、地图或科学模拟。
