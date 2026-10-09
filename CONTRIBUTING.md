# 开发与 Git 工作流

1. 阅读需求、架构和当前进度，在 `docs/dev-log/` 创建开发日志。
2. 从目标 `release_YYYYMMDD` 建立 `<开发者>/feature_<功能>_<日期>` 分支。
3. 完成修改和相关检查，更新接口契约及文档，检查未跟踪文件和暂存区。
4. 按一项逻辑改动提交，推送功能分支。
5. 发布分支准备就绪后，处理目标分支冲突并发起评审，经负责人审查后合并。

## 提交说明

标题保留 `类型(模块): 改动` 格式，说明具体做了什么。正文按需要补充原因和检查结果，避免重复标题或写成工作汇报。

| 类型 | 用途 | 示例 |
|---|---|---|
| feat | 新增功能 | `feat(weather): 按地块获取历史天气` |
| fix | 修复问题 | `fix(farm): 修复空列表下的登记表单` |
| docs | 修改文档 | `docs: 整理模块说明和测试记录` |
| chore | 调整工具或配置 | `chore: 更新开发环境脚本` |

~~~powershell
git status --short
git switch -c yourname/feature_farm_20261009 release_20261008
git add backend/src/crop_twin/domain/farm docs/dev-log
git diff --cached
git commit -m "feat(farm): 增加农事记录"
~~~

历史提交的中文索引见 [提交记录](docs/dev-log/commits.md)。已推送的提交保留原编号和说明，后续提交采用上述写法。

## 分支现状

远程仓库为 [TensorJade/crop-digital-twin](https://github.com/TensorJade/crop-digital-twin)。scaffold、farm_management、identity、simulation_inputs、pcse 和 weather 功能分支已推送。当前分支为 `codex/feature_weather_20261009`，基于 PCSE 提交 `2629b8e`。

远程默认分支仍为 scaffold；最新功能请查看 weather 分支。本地 `release_20261008` 已推进到 `2629b8e`，远程尚未建立发布分支。`master`、`develop`、`test` 也仅在本地。首个提交及分支建立方式见 [ADR 0001](docs/adr/0001-workspace-baseline.md)。

功能分支已有 CI 检查，正式评审、默认分支调整和分支保护由负责人在发布前安排。

## 文件范围

提交代码、契约、文档和小型非敏感示例。`.env`、密钥、数据集、影像、运行日志、备份、依赖和构建输出放在忽略目录中。新增忽略规则前检查文件是否已被 Git 跟踪。
