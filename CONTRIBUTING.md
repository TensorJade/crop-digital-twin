# 开发与 Git 工作流

1. 阅读需求编号、架构和当前进度；在 `docs/dev-log/` 创建当日真实日志。
2. 从目标 `release_YYYYMMDD` 创建 `<开发者>/feature_<功能>_<日期>` 分支。
3. 编码、运行相关检查、更新接口契约及文档；复核 `git diff`、`git diff --cached`、未跟踪文件和忽略规则。
4. 提交只表达一个逻辑变化，例如 `feat(plots): add plot boundary validation`、`fix(engine): correct radiation unit conversion`、`docs: record calibration validation`。
5. 配置远程后拉取目标 release 分支、处理冲突、推送功能分支、发起评审。至少一名负责人审查通过后再合并。

```powershell
git status --short
git switch -c yourname/feature_farm_20261009 release_20261008
git add backend/src/crop_twin/domain/farm docs/dev-log
git diff --cached
git commit -m "feat(farm): add farm business rules"
```

初始化特例：空仓库没有 master/release 历史，因此首个骨架提交在 `codex/feature_scaffold_20261008` 上建立，再建立本地 master、develop、test、release_20261008 基线指针。该基线是开发骨架，不是产品发布。见 [ADR 0001](docs/adr/0001-workspace-baseline.md)。

远程 `origin` 为 `https://github.com/TensorJade/crop-digital-twin.git`。scaffold、farm_management、identity、simulation_inputs 和 pcse 功能分支已按用户授权推送；当前开发/同步分支为 `codex/feature_weather_20261009`，从已验证PCSE基线2629b8e建立。本地release_20261008快进到该基线，仅用于连续开发。远程默认分支仍为scaffold，查看最新实现须选择weather功能分支。master、develop、test、release_20261008仍仅在本地，远程尚无目标release分支。后续发布基线分支、发起正式评审和设置默认分支时，由负责人同步分支保护与检查要求。

本地分支名不会产生平台保护权限。本次推送未配置分支保护或完成正式评审；GitHub Actions 已触发，其结论以具体提交的运行页面为准。日常功能继续在功能分支开发、记录日志并复核提交，再按已授权的范围推送。

不要提交 `.env`、数据集、影像、运行日志、备份、依赖或构建输出。仅存储非敏感小型示例与来源清单；已跟踪文件不会自动受后续 `.gitignore` 规则保护。
