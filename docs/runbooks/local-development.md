# 本地开发运行手册

在仓库根目录运行安装、启动和检查脚本。README 给出 PowerShell 命令。API 与前端需要分别运行；用 Ctrl+C 停止自己的进程。

1. Node 版本错误：使用 24.19.0，或传 `-NodeBinDirectory`；不要将不满足 engines 的系统 Node 用于安装。
2. Python 版本错误：本基线要求 3.12。修改版本前先评估科学依赖兼容性及更新锁文件。
3. 8000/5173 端口被占用：检查占用进程并确认归属，不直接杀死其他项目进程。两端端口或代理目标需一起调整。
4. 前端连接失败：确认 API 已启动，直接访问 `/api/v1/health`，检查 Vite 代理与终端日志。
5. 依赖变化：修改对应 pyproject/package.json，更新锁文件，运行相关检查，并在日志记录原因。
6. 接口变化：导出 OpenAPI、检查差异、更新消费者与测试。contracts 只记录真实接口。

Compose 可进行配置检查，见 infra/README。运行数据库不意味着业务数据已经持久化；此阶段尚无迁移/备份/恢复脚本。不要把仅存在 backups/ 目录描述为已完成备份。

官方环境参考：[Vue Quick Start](https://vuejs.org/guide/quick-start.html)、[FastAPI First Steps](https://fastapi.tiangolo.com/tutorial/first-steps/)、[Docker Compose 环境变量](https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/)。
