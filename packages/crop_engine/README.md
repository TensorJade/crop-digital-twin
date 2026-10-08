# 作物算法包（Python）

此包仅建立独立模块边界，当前没有模拟器、反演模型或校准算法。

后续按需要新增 `contracts.py`、`pcse_adapter.py`、`weather_units.py`、`management_adapter.py`、`provenance.py`。`imagery/` 放影像质控、光谱指数与 LAI 反演；`calibration/` 放先验、有界更新与不确定性评估。未实现的功能不预先添加空 Python 类或假运行接口。

PCSE、NumPy、Rasterio/GDAL 等依赖在实现对应模块并验证环境时再锁定。与 API、数据库和队列保持解耦：输入版本化参数/观测快照，输出可复现结果及来源信息。RGB 图像不能直接当作定量光谱反射率；校准更新应保留原始预测、观测及修正后的新版本。

复用旧项目代码前核实许可证、科学有效性与参数可用性。优先测试单位转换、管理事件时间语义、恢复重算与参数边界。
