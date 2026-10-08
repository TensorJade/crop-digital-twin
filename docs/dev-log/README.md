# 开发日志

文件名为 `YYYY-MM-DD-主题.md`。一份日志对应真实的一次开发工作；同一天可有多个主题。记录人员、时间、需求/任务、实际文件变更、检查命令与结果、限制、Git 分支/提交和下一步。不回填虚构的开发活动。

```powershell
.\scripts\new-dev-log.ps1 -Slug 'farm-management' -Author '开发者姓名'
```

模板在 `docs/templates/dev-log.md`。同名文件存在时脚本会拒绝覆盖。实际进度维护在 `docs/progress.md`；版本变化维护在 CHANGELOG.md。运行日志放忽略的 runtime/，两者用途不同。

当前模块记录：[M1 农田管理](2026-10-08-farm-management.md)、[M2 账户与组织授权](2026-10-08-identity.md)、[M3.1 输入与快照](2026-10-08-simulation-inputs.md)、[M3.2 潜在计算](2026-10-08-potential-simulation.md)。初始骨架和首次远程连接日志保留当时状态，不回改为后续能力。
