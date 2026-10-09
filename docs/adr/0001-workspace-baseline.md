# ADR 0001：开发环境与仓库

日期：2026-10-08。状态：已用于项目初始化。

## 决定

- 建立独立 crop-digital-twin 仓库，与已有 wofost_lai_edge 分开维护，统一管理前后端、算法、契约和文档。
- 后端及算法使用 Python 3.12 和 uv workspace；前端使用 Vue、TypeScript、Vite，Node 版本为 24.19.0。锁文件纳入 Git。
- Python、SQL 使用 snake_case，TypeScript 使用 camelCase，类和组件使用 PascalCase。
- API 使用 GET/POST；新增其他方法时补充设计记录。
- 首个提交在功能分支建立，再创建本地 master、develop、test、release_20261008 指针，后续从 release 建立功能分支。

## 待确认

远程分支保护、评审人、生产环境和外部服务授权在后续安排。原方案使用物理外键，与逻辑外键约定不同，建表前需确定关系检查和完整性措施。

作物、地区、品种参数、地图和天气供应商、影像格式、校准方法及验收阈值尚待确认。本次只建立开发环境和入口，尚未发布。
