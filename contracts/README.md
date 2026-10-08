# 接口与数据契约

openapi.json / openapi.yaml 从真实 FastAPI 应用导出，包含 9 个 M1 业务操作与存活操作，共 7 条路径、10 个 GET/POST 操作。

使用 uv run --locked python scripts/export_openapi.py 更新，附加 --check 验证一致性。

输入包含 UUID、日期、原始数量和单位；业务/存储错误提供 code 与中文 message，结构错误为标准 422。分页有上限，Decimal 输出为字符串。农事默认仅当前版，include_history 查询修订历史。

当前无账户契约，仅供本地单用户使用。schemas/ 仍为模型输入/观测/结果快照预留，不含可用科学契约。
