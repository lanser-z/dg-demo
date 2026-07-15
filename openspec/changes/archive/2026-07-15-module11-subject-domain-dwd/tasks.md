## 1. 依赖与基础设施

- [ ] 1.1 现有 `pyproject.toml` 依赖足够（pandas / deltalake / duckdb），无新增

## 2. ETL 脚本

- [ ] 2.1 创建 `scripts/restructure_dwd.py`：dual-write 模式读 `dwd/{system}/` 写 `dwd/{subject}/`
- [ ] 2.2 表-主题映射常量：`SUBJECT_MAP = {"sap_erp/dwd_vbak": "sales/dwd_vbak", "sap_erp/dwd_vbap": "sales/dwd_vbap", "sap_erp/dwd_kna1": "sales/dwd_kna1", "pi_system/dwd_tags": "production/dwd_tags", "lims/dwd_samples": "coal_quality/dwd_samples", "oa/dwd_doc_flow": "finance/dwd_doc_flow"}`
- [ ] 2.3 实现 `--dry-run` CLI 模式
- [ ] 2.4 实现 `--mode={dual,replace}` 模式（演示阶段用 dual）
- [ ] 2.5 跑脚本生成 4 主题目录 6 张表，验证 dual-write

## 3. DataHub 集成

- [ ] 3.1 创建 `scripts/register_subject_dwd.py`：注册 `dwd` 自定义 platform + 6 张新表的 datasetKey
- [ ] 3.2 用 `acryl-datahub` SDK 的 `DatahubRestEmitter.emit()` 写 `DataPlatformInfoClass` + `DatasetPropertiesClass`
- [ ] 3.3 跑 `scripts/emit_lineage.py` 重新 emit 新主题表的 lineage（如需）

## 4. 教学 notebook

- [ ] 4.1 创建 `notebook/module11.ipynb` 3 cells：
  - cell 1: 列出新旧 DWD 目录结构
  - cell 2: DuckDB 验证行数一致
  - cell 3: Playwright 截图 DataHub UI
- [ ] 4.2 跑 notebook 验证 3 cells 都成功

## 5. 文档

- [ ] 5.1 创建 `docs/Module11.md`
- [ ] 5.2 更新 `docs/Background.md §6.11` 标"已上线"
- [ ] 5.3 更新 `README.md` 路径 B notebook 列表：加 `module11.ipynb`（**影响学习路径 B**）

## 6. 验证与归档

- [ ] 6.1 验证 `data/lakehouse/dwd/sales/` 等 4 主题目录有数据
- [ ] 6.2 验证 DataHub OpenSearch `datasetindex_v2` 含 6 张新主题表
- [ ] 6.3 `openspec validate module11-subject-domain-dwd` 通过
- [ ] 6.4 `openspec archive module11-subject-domain-dwd --yes` 归档
