# 开发与 Git 工作流

1. 阅读需求编号、架构和当前进度；在 `docs/dev-log/` 创建当日真实日志。
2. 从目标 `release_YYYYMMDD` 创建 `<开发者>/feature_<功能>_<日期>` 分支。
3. 编码、运行相关检查、更新接口契约及文档；复核 `git diff`、`git diff --cached`、未跟踪文件和忽略规则。
4. 提交只表达一个逻辑变化，例如 `feat(plots): add plot boundary validation`、`fix(engine): correct radiation unit conversion`、`docs: record calibration validation`。
5. 配置远程后拉取目标 release 分支、处理冲突、推送功能分支、发起评审。至少一名负责人审查通过后再合并。

```powershell
git status --short
git switch -c yourname/feature_plots_20261009 release_20261008
git add backend/src/crop_twin/domain/plots docs/dev-log
git diff --cached
git commit -m "feat(plots): add plot domain model"
```

初始化特例：空仓库没有 master/release 历史，因此首个骨架提交在 `codex/feature_scaffold_20261008` 上建立，再建立本地 master、develop、test、release_20261008 基线指针。该基线是开发骨架，不是产品发布。见 [ADR 0001](docs/adr/0001-workspace-baseline.md)。

本地分支名不会产生平台保护权限。尚未配置远程地址、分支保护、实际评审或远程 CI。首次接入远程时，由负责人设置 master、develop、test、release_* 的保护规则和检查要求。

不要提交 `.env`、数据集、影像、运行日志、备份、依赖或构建输出。仅存储非敏感小型示例与来源清单；已跟踪文件不会自动受后续 `.gitignore` 规则保护。
