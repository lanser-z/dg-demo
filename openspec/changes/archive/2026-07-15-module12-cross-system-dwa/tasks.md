## 1. 依赖与基础设施

- [ ] 1.1 现有 `pyproject.toml` 依赖足够（duckdb / deltalake），无新增

## 2. 跨系统 DWA 宽表

- [ ] 2.1 创建 `scripts/build_dwa_sales_production.py`：
  - DuckDB in-memory
  - 4 个 `CREATE VIEW` 读 subject-分区 Parquet
  - 1 个 `CREATE TABLE dwa_sales_production AS SELECT ... 4-table LEFT JOIN ...`
  - `write_deltalake` 写 Delta Lake
  - 4 个分析场景 SQL 模板常量（产销对比 / 煤质定价 / 安全趋势 / 订单履约）
  - 6.9 `LineageEmitter` 包装
- [ ] 2.2 跑脚本生成 `data/lakehouse/dwa/dwa_sales_production/`
- [ ] 2.3 DuckDB CLI 验证 4 个 SQL 场景

## 3. 旧 DWA 切上游

- [ ] 3.1 改 `scripts/build_dwa_models.py` 中 3 个 DWA 函数的 read_parquet：
  - `build_dwa_sales_daily()`: `dwd/sap_erp/dwd_vbak` → `dwd/sales/dwd_vbak`
  - `build_dwa_tag_alarm()`: `dwd/pi_system/dwd_tags` → `dwd/production/dwd_tags`
  - `build_dwa_coal_quality()`: `dwd/lims/dwd_samples` → `dwd/coal_quality/dwd_samples`
- [ ] 3.2 跑 `build_dwa_models.py --layer dwa` 验证 3 张旧宽表仍生成（行数与 6.11 一致）

## 4. 教学 notebook

- [ ] 4.1 创建 `notebook/module12.ipynb` 3 cells：
  - cell 1: import + 调 `build_dwa_sales_production.py` 或 inline DuckDB JOIN
  - cell 2: 4 个 SQL 场景示例输出（产销 / 煤质 / 安全 / 订单）
  - cell 3: matplotlib 渲染 4 表 JOIN 关键指标图 → `step_images/module12_4table_join.png`
- [ ] 4.2 跑 notebook 验证 3 cells 都成功

## 5. 文档

- [ ] 5.1 创建 `docs/Module12.md`（4 sections：概述 / 4 表 JOIN 设计 / 旧 DWA 切上游 / 演进路径）
- [ ] 5.2 更新 `docs/Background.md §6.12` 标"已上线" + 简化决策表（duckdb 替代 clickhouse）
- [ ] 5.3 更新 `README.md` 路径 B notebook 列表：加 `module12.ipynb`（**影响学习路径 B**）

## 6. 验证与归档

- [ ] 6.1 跑 `verify_auto_lineage.py` 验证 dwa_sales_production job lineage（inputs=4, outputs=1）
- [ ] 6.2 `openspec validate module12-cross-system-dwa` 通过
- [ ] 6.3 `openspec archive module12-cross-system-dwa --yes` 归档
