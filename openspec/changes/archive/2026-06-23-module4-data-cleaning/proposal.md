## Why

模块一/二/三已覆盖「看资产 → 找问题 → 追血缘」。但**发现问题后怎么把脏数据变干净**这一环,教学上还是空白——`scripts/ingest_to_deltalake.py --layer dwd` 能跑,清洗逻辑也真实存在(`_clean()` 函数做了去空/去重/规范化),但:

1. **没有独立教学 notebook**:Background §6.4 的演示剧本第 1 步是「打开 module1.ipynb 步骤1」——写 §6.4 时模块四寄生在模块一上,没有自己的 notebook。
2. **3 类「智能修复」承诺未兑现**:§6.4 明确把 VBAP 关联失效标记(IS_VALID_LINK)、PI 异常值插值、LIMS 灰分修正列为「暂时做不到的待办」。用户要求演示做全面,**3 项全补**。
3. **清洗逻辑锁在 CLI 里**:`_clean()` 是 `ingest_to_deltalake.py` 的内部函数,notebook 无法直接调用演示,也无法做清洗前后质量分对比。需要抽成 `dg_education.cleaning` 库。
4. **存在 description bug**:`ingest_to_deltalake.py` 的 `oa/doc_flow` DWD_TABLES description 写「过滤 DOC_TYPE/CREATE_DATE」,实际代码过滤的是 `FLOW_TYPE/APPLY_DATE`(代码对、描述错)。

本变更实现模块四:抽 `cleaning.py` 库 + 补 3 类智能修复 + 建 module4.ipynb(调封装函数,可写 Delta 演示 Time Travel,代码不堆在 notebook 里)+ 修 description bug + 配 Module4.md。

## What Changes

- **新增 `src/dg_education/cleaning.py`**:从 `ingest_to_deltalake.py:_clean()` 抽出基础清洗(去空/去重/规范化)为 `clean_basic(source, df)`;新增 3 类智能修复函数;提供 `clean_and_write_dwd()` / `show_delta_history()` 封装供 notebook 一行调用
- **新增 3 类智能修复**(全补,Background §6.4 待办):
  - `mark_vbap_valid_link(vbap, vbak)`:加 `IS_VALID_LINK` 列,标记 VBELN 是否在 vbak 中存在(改值不删行)
  - `repair_pi_anomalies(pi_df)`:超 3x 中位数的 value 用线性插值替代(复用模块二 quality.py 阈值逻辑)
  - `repair_lims_ad(lims_df)`:超煤种区间的 AD 夹逼到 `[lo, hi]` 边界(复用 quality.py `AD_RANGES_BY_COAL_TYPE`)
- **修改 `scripts/ingest_to_deltalake.py`**:`_clean()` 改为调 `cleaning.clean_basic()`(单一真相源,避免规则漂移);修 `oa/doc_flow` description bug(`DOC_TYPE/CREATE_DATE` → `FLOW_TYPE/APPLY_DATE`)
- **新增 `notebook/module4.ipynb`**:3 步教学(清洗前画像 → 4 类清洗演示 → 清洗前后质量分对比),调封装函数不堆代码,含 Delta Lake Time Travel 演示
- **扩展 `src/dg_education/visualization.py`**:新增清洗前后对比可视化(剔除行数/质量分变化)
- **更新 `src/dg_education/__init__.py`**:导出 cleaning + 新 visualization API
- **新增 `docs/Module4.md`**:实施步骤(对应 Background §6.4,写正确实现与 4 类清洗主张)

**BREAKING**:`ingest_to_deltalake.py:_clean()` 签名不变但实现改为委托 cleaning.py;`oa/doc_flow` description 文本变更。无外部 CLI 行为变化。

## Capabilities

### New Capabilities

- `data-cleaning`:数据清洗能力,含 4 类清洗(去空/去重/规范化/智能修复)+ Delta Lake 落库封装 + Time Travel 查询
- `module4-cleaning-notebook`:模块四教学 notebook,清洗前后质量提升对比

### Modified Capabilities

无(模块一/二/三的 spec 不变;cleaning.py 是新增库,ingest_to_deltalake.py 的清洗行为本身不变,只是实现委托)。

## Impact

**受影响模块**:
- 模块二(`quality-root-cause-analysis` / `module2-quality-detection`):cleaning.py 复用其 `AD_RANGES_BY_COAL_TYPE` 常量与 median 3x 阈值逻辑,只读复用,不改模块二行为
- 模块三(`data-lineage-ingestion`):module4 notebook 末尾引用 module3.ipynb,无代码依赖
- 模块一:module4 末尾引用 module1/2/3,无代码依赖

**代码影响**:
- 新增:`src/dg_education/cleaning.py`、`notebook/module4.ipynb`、`docs/Module4.md`
- 修改:`scripts/ingest_to_deltalake.py`(`_clean` 委托 + description bug 修复)、`src/dg_education/visualization.py`(追加对比可视化)、`src/dg_education/__init__.py`(导出)
- 依赖:无新增(`pandas`/`deltalake`/`matplotlib` 已有;复用 quality.py 常量)

**数据影响**:
- 智能修复在 notebook 中用**临时 DataFrame 演示**,不默默改 `data/lakehouse/dwd/`(修复有业务争议,落库需源头改单)
- 基础清洗(去空去重)可通过 `clean_and_write_dwd()` 落 Delta Lake(演示 Delta ACID/Time Travel),写入路径 `data/lakehouse/dwd/`(已有,覆盖写)
- 不修改 `data/historical/` 源数据

**下游影响**:
- 后续模块五(ELT + DWA)可复用 cleaning.py
- 4 类清洗主张(含智能修复)升级 Background §6.4 的「干净但不修复」为「干净且修复可修复的」,在 Module4.md 与 notebook 体现(不改 Background.md)

**回滚计划**:
- `git revert` 本次 commit
- `cleaning.py` / module4.ipynb / Module4.md 为新增,删除即可
- `ingest_to_deltalake.py` 的 `_clean` 委托可还原为内联实现;description bug 修复保留(本就是修错)
- 已落的 Delta Lake 数据用 `clean_and_write_dwd` 重跑覆盖,无残留
