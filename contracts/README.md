# 接口与数据契约

openapi.json / openapi.yaml 从真实 FastAPI 应用导出，版本 0.4.0：9 个 M1、9 个 M2、7 个 M3.1 操作及存活接口，共 20 条路径、26 个 GET/POST 操作。

使用 uv run --locked python scripts/export_openapi.py 更新，附加 --check 验证一致。具体必填字段、类型和响应以导出文件为准。schemas/ 预留未来观测/模型结果，不表示已有预测契约。

登录设置 crop_twin_session Cookie，返回用户、组织、CSRF 与到期时间，不返回原始会话令牌。业务接口需要 Cookie；POST 除登录外检查 JSON、Origin、X-CSRF-Token 与角色。Cookie 为 HttpOnly、SameSite=Lax、Path=/api，HTTPS 和生产发布须经 M7。

输入资料请求按 kind 区分 soil/crop/weather，extra 字段拒绝；天气 CSV 必须包含明确单位和来源元数据。输入快照请求引用本组织三份资料、种植季、实际出苗日和截止日。列表返回摘要 items/total/limit/offset，详情返回 payload/hash。输入检查不写数据；保存允许不完整，但携带报告且 simulation_executed=false。

snapshot payload schema_version=1.0.0，与软件版本分别记录。SHA-256 只覆盖 payload 的规范 JSON，外层创建时间等元数据不在该校验范围；资料子项保留原内容和来源。规范数值规则及离线核验见 packages/crop_engine/README.md、docs/modules/simulation-inputs.md。

结构错误 422 去除原始 input/ctx；401 会话无效、403 角色/CSRF/Origin、404 不存在/跨组织、409 冲突、429 登录限制、503 存储不可用。业务错误有稳定 code 与中文 message。农事 Decimal 为字符串，日期为 ISO；只读成员不能写入。没有模型精度或预测可用性的声明。
