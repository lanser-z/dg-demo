## 1. 脚本开发

- [x] 1.1 创建 `scripts/build_dimension_tables.py`，实现 `build_dim_mine()` 函数：从 `data/lakehouse/dwd/pi_system/dwd_tags/` 和 `data/lakehouse/dwd/lims/dwd_samples/` 提取矿井编码和名称，DISTINCT 去重后写入 `data/lakehouse/dwd/_dimensions/dim_mine/`（Delta Lake），字段：mine_code, mine_name, mine_type, sap_mine_field, pi_mine_field, lims_mine_field

- [x] 1.2 创建 `scripts/build_dimension_tables.py`，实现 `build_dim_customer()` 函数：从 `data/lakehouse/dwd/sap_erp/kna1/` 提取 KUNNR、NAME1、ORT01（作为 region），去重后写入 `data/lakehouse/dwd/_dimensions/dim_customer/`（Delta Lake），字段：kunnr, customer_name, region, credit_level（credit_level 暂设为 `UNKNOWN`）

- [x] 1.3 创建 `scripts/build_dimension_tables.py`，实现 `build_dim_material()` 函数：从 `data/lakehouse/dwd/sap_erp/dwd_vbak/` 提取 MATNR、MATNR 描述（从 VBAK/VBAP 推断），去重后写入 `data/lakehouse/dwd/_dimensions/dim_material/`（Delta Lake），字段：matnr, mat_desc, mat_type（备注：待 MARA 接入后重建）

- [x] 1.4 在 `scripts/build_dimension_tables.py` 添加 `if __name__ == "__main__"` 入口，支持 `--dimension mine|customer|material|all` 参数运行

## 2. 教学 Notebook 开发

- [x] 2.1 创建 `notebook/module7.ipynb`，包含痛点故事 markdown cell（说明异构字段名问题，如 `mine` vs `MINE_CODE` vs `WERKS`）

- [x] 2.2 在 `notebook/module7.ipynb` 添加构建维表演示 cell，调用 `scripts/build_dimension_tables.py` 分别构建 3 张维表并展示 row count

- [x] 2.3 在 `notebook/module7.ipynb` 添加 JOIN 对比 SQL cell：展示无维表时的复杂 WHERE 映射 SQL vs 有维表后的简洁 JOIN SQL

- [x] 2.4 在 `notebook/module7.ipynb` 末尾添加免责声明 cell（诚实声明本 notebook 为教学演示，数据不代表生产环境）

## 3. 验证

- [x] 3.1 运行 `python scripts/build_dimension_tables.py --dimension all`，验证 3 张维表 Delta Lake 目录创建成功且行数 > 0

- [x] 3.2 打开 `notebook/module7.ipynb`，按顺序运行所有 cell，验证无报错
