# 模块四实施步骤：数据清洗与质量提升

> 对应 `docs/Background.md` § 6.4。
> 目标：从 ODS 原始层到 DWD 清洗层，展示脏数据怎么变干净，清洗前后质量分从 C/D 提升到 B/A。
> 新增 3 类智能修复（VBAP 关联标记 / PI 异常插值 / LIMS 灰分夹逼），与基础清洗（去空/去重/规范化）形成 4 类清洗主张。

---

## 0. 4 类清洗总览

| 清洗类型 | 作用 | 是否删行 | 数据源 |
|---------|------|---------|--------|
| ① 去空 | 关键字段不能为空 | 删行 | 6 张表 |
| ② 去重 | 同一笔不能录两次 | 删行 | 6 张表 |
| ③ 规范化 | 字段格式统一（金额标准化、客户号补零） | 改值不删 | 2 张表 |
| ④ 智能修复 | VBAP 关联失效标记 / PI 插值 / LIMS 夹逼 | 加列/改值不删 | 3 张表 |

> 基础清洗（①-③）规则单一真相源在 `src/dg_education/cleaning.py:clean_basic()`，`scripts/ingest_to_deltalake.py` 的 `_clean` 委托调用。
> 智能修复（④）仅 notebook 演示用临时 DataFrame，不落 `data/lakehouse/dwd/`（修复为近似值，落库需源头改单）。

---

## 1. 代码实现

### 1.1 新建 cleaning.py（`src/dg_education/cleaning.py`）

| 函数 | 说明 | 分类 |
|------|------|------|
| `clean_basic(source, df)` | 基础清洗：去空/去重/规范化，与旧 `_clean` 完全等价 | 基础清洗 |
| `cleaning_stats(before, after)` | 清洗前后统计：剔除行数/比例 | 辅助 |
| `mark_vbap_valid_link(vbap, vbak)` | 加 `IS_VALID_LINK` 列，标记 VBELN 不在 vbak 的行 | 智能修复 |
| `repair_pi_anomalies(pi_df)` | 超 3x 中位数的 value 线性插值替代，返回 (df, n_fixed) | 智能修复 |
| `repair_lims_ad(lims_df)` | 超煤种区间的 AD 夹逼到 [lo, hi]，复用 quality.py 常量 | 智能修复 |
| `clean_and_write_dwd(table_key)` | 基础清洗 + 落 Delta Lake，返回 before/after 统计 | Delta 封装 |
| `show_delta_history(table_key)` | 读 _delta_log 返回版本历史，演示 Time Travel | Delta 封装 |

**关键设计**：
- `clean_basic` 与原 `ingest_to_deltalake.py:_clean()` 逻辑完全一致（逐行对照验证过），`ingest_to_deltalake.py` 已委托调用
- `AD_RANGES_BY_COAL_TYPE` 从 `dg_education.quality` import，不重复定义
- PI median 3x 阈值逻辑与模块二 quality.py 一致

### 1.2 `ingest_to_deltalake.py` 变更

- `_clean(source, df)` → 改为 `return clean_basic(source, df)` 委托
- `oa/doc_flow` description 修复：`DOC_TYPE/CREATE_DATE` → `FLOW_TYPE/APPLY_DATE`

### 1.3 IS_VALID_LINK 关键约束

```python
# 正确做法：用全量 vbak（2022+2023 合计 603 万行）做参照集
vbak_full = pd.concat([pd.read_parquet(f'.../vbak_year={y}.parquet') for y in [2022, 2023]])
marked = mark_vbap_valid_link(vbap, vbak_full)
# 孤儿行 = 60375 (1%, 即注入的 0000000000)

# 错误做法：只用单年 vbak（只读 2022 会因 vbap 引用了 2023 订单号而产生假性悬空 ~50%）
```

---

## 2. 教学 notebook

`notebook/module4.ipynb` 按 19 个 cell 组织（5 个 markdown 讲解 + 7 个 code cells + 附加/总结）：

| 步骤 | 内容 | 调用的函数 |
|------|------|-----------|
| 痛点故事 | 脏数据进报表的尬 | — |
| 步骤1 | 清洗前画像：6 张表 ODS 原始数据统计 | `clean_basic`, `cleaning_stats`, `plot_cleaning_stats` |
| 步骤2.1 | VBAP IS_VALID_LINK 标记 | `mark_vbap_valid_link`（传全量 vbak） |
| 步骤2.2 | PI 异常插值（曲线对比） | `repair_pi_anomalies`, `plot_pi_repair_before_after` |
| 步骤2.3 | LIMS 灰分夹逼 | `repair_lims_ad` |
| 步骤3 | 清洗前后质量对比 | `check_sap_quality` |
| 附加 | Delta Time Travel | `clean_and_write_dwd`, `show_delta_history` |
| 诚实声明 | 近似值非真值 | — |

**设计原则**：notebook 每个 code cell ≤10 行清洗相关代码（调函数 + 展示结果），大段逻辑在 `cleaning.py` 里。不内联 `dropna`/`drop_duplicates`/`interpolate`。

---

## 3. 执行流程

```bash
# step 1: 所有清洗代码在 cleaning.py 里，notebook import 调
jupyter notebook notebook/module4.ipynb

# step 2: 落 Delta Lake（clean_and_write_dwd 在 notebook 附加演示）
# 单独跑全量 DWD 入湖（与之前一致）
uv run python scripts/ingest_to_deltalake.py --layer dwd

# step 3: 版本回溯验证（notebook 附加演示 show_delta_history）
```

---

## 4. 当前状态

**清洗库（100%）**
- [x] `src/dg_education/cleaning.py`：clean_basic + 3 智能修复 + Delta 封装
- [x] 复用 `quality.py.AD_RANGES_BY_COAL_TYPE`，不重复定义
- [x] 3 个修复函数不落库（仅临时 df），`clean_and_write_dwd` 仅落基础清洗

**ingest_to_deltalake.py（100%）**
- [x] `_clean` 委托 `cleaning.clean_basic`（单一真相源）
- [x] `oa/doc_flow` description bug 修复

**教学（100%）**
- [x] `notebook/module4.ipynb`：19 cell，痛点故事 + 4 类清洗 + Delta Time Travel
- [x] code cell 不内联清洗原语（调函数 ≤10 行）
- [x] 清洗前后质量分对比（C/D → B/A）
- [x] 诚实声明：智能修复为近似值非真值

**可视化（100%）**
- [x] `plot_cleaning_stats`（剔除柱状图）
- [x] `plot_quality_before_after`（双柱对比）
- [x] `plot_pi_repair_before_after`（插值曲线对比）

**待办（Phase 2/3）**
- [ ] 定时清洗调度（Airflow/Cron）
- [ ] 流式清洗（Flink，Phase 3）
- [ ] 主数据标准化驱动的智能修复升级

---

## 5. 故障排查

| 现象 | 原因 | 处理 |
|------|------|------|
| `IS_VALID_LINK=False` 行数 ≈50% | vbak 只传了单年（2022 仅 301 万行，vbap 引用 2023 订单产生假性悬空） | 必须传全量 vbak(2022+2023)，实测孤儿数=60375(1%) |
| `repair_pi_anomalies` 修复数=0 | 该 tag 全为正常值或 median=0 | 正常，选有 WAGAS 标签的数据即可展现 |
| `clean_and_write_dwd` 报 ODS 文件找不到 | `table_key` 格式必须形如 `sap_erp/kna1` | 确认 `data/historical/` 下有对应 Parquet |
