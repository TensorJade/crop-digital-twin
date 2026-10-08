# 接口与数据契约

`openapi.json` / `openapi.yaml` 从已实现的 FastAPI 应用导出，当前只有 `GET /api/v1/health`。通过 `uv run --locked python scripts/export_openapi.py` 更新，用 `--check` 验证一致性。

未来地块、农事、影像、任务与模拟接口清单见 docs/requirements.md 和设计基线；先设计请求、单位、错误、权限和版本语义，再实现。`schemas/` 预留模型输入、观测与结果快照 JSON Schema；当前没有可用科学数据契约。
