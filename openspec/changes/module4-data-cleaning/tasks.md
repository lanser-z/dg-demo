## 1. 新建 cleaning.py 基础清洗（无依赖，先做）

- [ ] 1.1 新建 `src/dg_education/cleaning.py`,实现 `clean_basic(source, df)` —— 从 `ingest_to_deltalake.py:_clean()` 逐行搬出(去空/去重/规范化,覆盖 6 张表)
- [ ] 1.2 实现 `cleaning_stats(before_df, after_df) -> dict`(剔除行数/比例/各表统计)
- [ ] 1.3 验证:`clean_basic` 与原 `_clean` 对同一 ODS Parquet 输出完全一致(行数/列/值)

## 2. ingest_to_deltalake.py 委托 + description bug（依赖 1）

- [ ] 2.1 `scripts/ingest_to_deltalake.py` 的 `_clean()` 改为 `return cleaning.clean_basic(source, df)` 委托,删内联规则
- [ ] 2.2 修 `DWD_TABLES` 的 `oa/doc_flow` description:`DOC_TYPE/CREATE_DATE` → `FLOW_TYPE/APPLY_DATE`
- [ ] 2.3 验证:`uv run python scripts/ingest_to_deltalake.py --layer dwd` 仍可跑,输出行数与改前一致

## 3. 3 类智能修复函数（依赖 1）

- [ ] 3.1 实现 `mark_vbap_valid_link(vbap, vbak) -> vbap`:加 `IS_VALID_LINK` 布尔列(VBELN ∈ vbak.VBELN),不删行
- [ ] 3.2 实现 `repair_pi_anomalies(pi_df) -> (df, n_fixed)`:超 3x median 的 value 用 `sort_values('timestamp').groupby('tag').interpolate()` 替代,不删行
- [ ] 3.3 实现 `repair_lims_ad(lims_df) -> (df, n_fixed)`:超煤种区间 AD 夹逼到 [lo,hi],`from dg_education.quality import AD_RANGES_BY_COAL_TYPE` 复用,不删行
- [ ] 3.4 验证:3 函数返回 df 行数=输入行数(改值不删行);VBAP 孤儿行 ~60375;PI 修复数>0;LIMS AD=1200→15

## 4. Delta Lake 封装（依赖 1）

- [ ] 4.1 实现 `clean_and_write_dwd(table_key) -> dict`:基础清洗 + `write_deltalake` 落 `data/lakehouse/dwd/`,返回 before/after 行数与存储
- [ ] 4.2 实现 `show_delta_history(table_key) -> list`:读 `_delta_log` 返回版本号+操作时间
- [ ] 4.3 验证:`clean_and_write_dwd('sap_erp/vbak')` 写盘成功;`show_delta_history` 返回非空版本列表
- [ ] 4.4 确认 3 个智能修复函数无 `write_deltalake`/`to_parquet`/`to_delta` 调用(不落库)

## 5. 可视化扩展（依赖 1）

- [ ] 5.1 在 `src/dg_education/visualization.py` 追加 `plot_cleaning_stats(stats)`(清洗剔除行数/比例柱状图)
- [ ] 5.2 追加 `plot_quality_before_after(before_scores, after_scores)`(清洗前后质量分对比)
- [ ] 5.3 追加 `plot_pi_repair_before_after(df_before, df_after)`(PI 异常插值前后曲线对比)
- [ ] 5.4 验证:3 函数可调用,中文字体不乱码(沿用 `_ensure_chinese_font()`)

## 6. API 导出（依赖 1, 3, 4, 5）

- [ ] 6.1 更新 `src/dg_education/__init__.py`:导入 cleaning API(`clean_basic`/`mark_vbap_valid_link`/`repair_pi_anomalies`/`repair_lims_ad`/`clean_and_write_dwd`/`show_delta_history`)+ 新 visualization API
- [ ] 6.2 更新 `__all__`
- [ ] 6.3 验证:`uv run python -c "from dg_education import clean_basic, repair_pi_anomalies, clean_and_write_dwd, show_delta_history"` 成功

## 7. 教学 notebook（依赖 1-6）

- [ ] 7.1 创建 `notebook/module4.ipynb`,第 1 cell 痛点故事(<200 字,幕一脏数据进报表/幕二清洗后可信)
- [ ] 7.2 第 2 cell:Setup(import cleaning + 加载 ODS Parquet)
- [ ] 7.3 第 3 cell:3 步学习节奏总览(markdown 表格)
- [ ] 7.4 步骤 1:清洗前脏数据画像(调 cleaning_stats,plot_cleaning_stats)
- [ ] 7.5 步骤 2:4 类清洗演示(clean_basic + 3 智能修复 + 业务影响白话 + plot_pi_repair_before_after)
- [ ] 7.6 步骤 3:清洗前后质量分对比(调 run_ge_scan,plot_quality_before_after)
- [ ] 7.7 附加:Delta Time Travel(show_delta_history)+ ACID/Schema演进/TimeTravel markdown 讲解
- [ ] 7.8 末尾引用 module1/2/3.ipynb
- [ ] 7.9 验证:每个 code cell 清洗相关代码 ≤10 行(调函数不堆代码);无 `dropna`/`drop_duplicates`/`interpolate` 内联

## 8. 文档与最终验证（依赖 7）

- [ ] 8.1 新建 `docs/Module4.md`:实施步骤(4 类清洗主张、cleaning.py API、notebook 流程、诚实区分真实/演示提升)
- [ ] 8.2 验证:`uv run python -c "..."` 跑 module4.ipynb 全 cell(经 _verify_notebooks.py)无 error
- [ ] 8.3 验证:module4.ipynb 含「近似值/非真值/源头/改单」诚实声明
- [ ] 8.4 验证:`clean_basic` 与原 `_clean` 等价(回归)
- [ ] 8.5 验证:ingest_to_deltalake.py 无 `DOC_TYPE`/`CREATE_DATE`
- [ ] 8.6 验证:3 智能修复函数无写盘调用
