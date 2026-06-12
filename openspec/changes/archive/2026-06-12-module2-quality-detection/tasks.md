## 1. 源码扩展（quality.py）

- [x] 1.1 在 `src/dg_education/quality.py` 末尾追加 `analyze_vbap_invalid_links(vbap)` 函数
- [x] 1.2 追加 `analyze_pi_missing_tags(pi_df)` 函数
- [x] 1.3 追加 `analyze_pi_anomalies(pi_df)` 函数（含 3x 中位数阈值计算）
- [x] 1.4 追加 `analyze_lims_ad_outliers(lims_df)` 函数（按煤种分组）

## 2. 新增 GE 扫描封装（ge_scan.py）

- [x] 2.1 新建 `src/dg_education/ge_scan.py` 文件
- [x] 2.2 实现 `run_ge_scan(systems, output_json)` 函数（同进程 import + numpy 类型规范化）
- [x] 2.3 实现 `parse_ge_report(json_path)` 辅助函数

## 3. 源码扩展（visualization.py）

- [x] 3.1 在 `src/dg_education/visualization.py` 末尾追加 `plot_root_cause_distribution` 函数
- [x] 3.2 追加 `plot_alert_heatmap` 函数（红黄绿渐变）
- [x] 3.3 追加 `plot_system_alert_summary` 函数（双柱状对比）

## 4. API 导出更新

- [x] 4.1 更新 `src/dg_education/__init__.py`：导入 8 个新 API
- [x] 4.2 更新 `__all__` 列表
- [x] 4.3 验证：`uv run python -c "from dg_education import run_ge_scan, analyze_vbap_invalid_links, plot_root_cause_distribution"` 成功

## 5. Notebook 创建（module2.ipynb）

- [x] 5.1 创建 `notebook/module2.ipynb`，第 1 个 cell 为「痛点故事」（< 200 字符）
- [x] 5.2 第 2 cell：Setup（import + 加载 2022 年全量数据）
- [x] 5.3 第 3 cell：3 步学习节奏总览（markdown 表格）
- [x] 5.4 第 4 cell：步骤 1 GE 规则引擎全量扫描（run_ge_scan + plot_system_alert_summary）
- [x] 5.5 第 5 cell：步骤 2 根因定位（4 个子节：SAP / PI 缺失 / PI 异常 / LIMS）
- [x] 5.6 第 6 cell：步骤 3 告警聚合（plot_alert_heatmap + 系统总分排名）
- [x] 5.7 最后 1-2 cell：模块二总结 + 引用 `notebook/module1.ipynb`

## 6. 验证

- [x] 6.1 `uv run jupyter notebook notebook/module2.ipynb` 全部 cell 跑通，无 error
- [x] 6.2 检查 module2.ipynb 不含 `direct_es_bulk.py` / `emit_*.py` / `29200` 命中
- [x] 6.3 检查 module2.ipynb 数据路径全为 `year=2022`
- [x] 6.4 模块一 notebook 仍可正常运行（无破坏性变更）
