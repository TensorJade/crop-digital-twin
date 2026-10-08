# 接口与数据契约

openapi.json / openapi.yaml 从真实 FastAPI 应用导出，包含 9 个 M1 操作、9 个 M2 操作和存活操作，共 15 条路径、19 个 GET/POST 操作，版本 0.3.0。

使用 uv run --locked python scripts/export_openapi.py 更新，附加 --check 验证一致性。具体请求字段和响应以导出文件为准。

登录返回用户/组织/CSRF/到期时间并设置 crop_twin_session Cookie；原始会话令牌不进入 JSON。业务 API 使用 Cookie 会话；POST 除登录还需 X-CSRF-Token，安全方案/请求头已在 OpenAPI 标出。前端通过 GET auth/me 恢复会话状态。Cookie 为 HttpOnly、SameSite=Lax、Path=/api，HTTPS 部署需启用 Secure 并完成 M7。

输入包含 UUID、日期、原始数量和单位；业务错误提供 code 与中文 message。结构错误 422 保留位置和描述但不返回原始 input/ctx，避免密码回显。401 会话无效、403 角色/CSRF/Origin、404 无资源或跨组织、409 冲突、429 登录限制、503 存储不可用。

列表返回 items/total/limit/offset，分页有上限。Decimal 输出为字符串；农事 include_history 查询修订历史。成员角色只允许创建 operator/viewer，归属由服务端确定。schemas/ 为模型输入/观测/结果快照预留，尚无可用科学契约。
