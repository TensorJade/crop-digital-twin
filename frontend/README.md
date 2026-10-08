# 前端（TypeScript / Vue 单文件组件 / CSS）

`src/app` 放启动、路由与状态；`pages` 放完整页面；`components` 放通用组件；`features` 放地块、农事、影像、长势模块；`maps` 隔离底图服务和矢量样式；`api` 放 HTTP 客户端与契约类型；`types` 放共享业务类型；`styles` 放样式。

当前仅有开发首页和手写的健康检查客户端，尚未引入 Router、Pinia 或地图 SDK。`api/generated` 预留契约生成位置；不能把当前手写客户端称为自动生成代码。未来按功能需要添加依赖及对应测试。

Vite 开发代理仅供本地联调；`dist` 构建后的 API 路由需通过正式代理配置提供。`preview` 不提供生产部署保证。
