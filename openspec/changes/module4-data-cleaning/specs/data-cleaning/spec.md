## ADDED Requirements

### Requirement: cleaning.py 抽出基础清洗为 clean_basic,ingest_to_deltalake.py 委托调用

`src/dg_education/cleaning.py` MUST 提供 `clean_basic(source: str, df: pd.DataFrame) -> pd.DataFrame` 函数,逻辑与原 `scripts/ingest_to_deltalake.py:_clean()` 完全一致(去空/去重/规范化,覆盖 6 张表)。`scripts/ingest_to_deltalake.py:_clean()` MUST 改为委托 `cleaning.clean_basic()`(单一真相源)。

#### Scenario: clean_basic 与原 _clean 等价
- **WHEN** 对同一份 ODS Parquet 分别跑原 `_clean()`(实现委托前)与 `cleaning.clean_basic()`
- **THEN** 二者输出 DataFrame 的行数、列、值 MUST 完全一致

#### Scenario: ingest_to_deltalake 委托 cleaning
- **WHEN** 在 `scripts/ingest_to_deltalake.py` 中检查 `_clean` 函数体
- **THEN** MUST 调用 `dg_education.cleaning.clean_basic()`,MUST NOT 内联重复清洗规则

### Requirement: 补 VBAP 关联失效标记 IS_VALID_LINK 列

`cleaning.py` MUST 提供 `mark_vbap_valid_link(vbap: pd.DataFrame, vbak: pd.DataFrame) -> pd.DataFrame`,为 vbap 加 `IS_VALID_LINK` 布尔列,值为 `vbap.VBELN ∈ set(vbak.VBELN)`。MUST NOT 删除孤儿行(改值/加列不删行原则)。

**关键约束**:vbap 的 VBELN 从全量 vbak pool 抽样(跨年份),调用方 MUST 传入**全量 vbak**(2022+2023 合计),MUST NOT 只传单年 vbak。只传单年会导致约 50% 假性悬空(因 vbap 引用了其他年份的订单),与 Background §2.3 的 1% 孤儿预期不符。

#### Scenario: 孤儿行被标记而非删除
- **WHEN** 对含 `VBELN=0000000000` 的 vbap 调用 `mark_vbap_valid_link(vbap, vbak)`
- **THEN** 返回 df 行数 MUST 等于输入行数(不删行),且 `IS_VALID_LINK=False` 的行数 MUST > 0(孤儿行被标记)

#### Scenario: 用全量 vbak 校验得 1% 孤儿
- **WHEN** 对 `vbap_year=2022` 调用 `mark_vbap_valid_link`,vbak 传入 2022+2023 全量合计
- **THEN** `IS_VALID_LINK=False` 的行数 MUST 约为 60375(1%,即注入的 `0000000000`),MUST NOT 出现 ~50% 的假性悬空

#### Scenario: 正常行标记为 True
- **WHEN** vbap 某行 VBELN 存在于 vbak.VBELN 集合
- **THEN** 该行 `IS_VALID_LINK` MUST 为 True

### Requirement: 补 PI 异常值线性插值修复

`cleaning.py` MUST 提供 `repair_pi_anomalies(pi_df: pd.DataFrame) -> tuple[pd.DataFrame, int]`,对超 `3x 中位数`阈值的 value 用线性插值替代,返回修复后 df 与修复行数。MUST 先 `sort_values('timestamp')` 再 `groupby('tag').interpolate()`,避免乱序插值。MUST NOT 删除异常行。

#### Scenario: 异常值被插值替代
- **WHEN** 对含 value > 3x median 的 PI 数据调用 `repair_pi_anomalies`
- **THEN** 返回 df 行数 MUST 等于输入(不删行),返回的修复行数 MUST > 0,且原异常位置的 value MUST 被替换为插值近似值

#### Scenario: 插值前先排序分组
- **WHEN** 检查 `repair_pi_anomalies` 源码
- **THEN** MUST 包含 `sort_values('timestamp')` 与 `groupby('tag')` 在 `interpolate()` 之前

### Requirement: 补 LIMS 灰分夹逼修正

`cleaning.py` MUST 提供 `repair_lims_ad(lims_df: pd.DataFrame) -> tuple[pd.DataFrame, int]`,对超煤种区间的 AD 夹逼到 `[lo, hi]` 边界(超上限→hi,超下限→lo),返回修复后 df 与修复行数。MUST 复用 `dg_education.quality.AD_RANGES_BY_COAL_TYPE` 常量,不重复定义。MUST NOT 删除异常行。

#### Scenario: 超区间灰分被夹逼
- **WHEN** 对含 AD=1200 的精煤样品(正常区间 5-15)调用 `repair_lims_ad`
- **THEN** 该行 AD MUST 被夹逼为 15(hi),返回 df 行数不变,修复行数 > 0

#### Scenario: 复用 quality 常量
- **WHEN** 检查 `cleaning.py` 源码
- **THEN** MUST 包含 `from dg_education.quality import AD_RANGES_BY_COAL_TYPE`(或等价 import),MUST NOT 在 cleaning.py 内重新定义该字典

### Requirement: 智能修复不落库 lakehouse,仅返回临时 df

`clean_basic` 的结果可通过 `clean_and_write_dwd()` 落 Delta Lake;但 3 个智能修复函数(`mark_vbap_valid_link`/`repair_pi_anomalies`/`repair_lims_ad`)MUST 仅返回 DataFrame, MUST NOT 写入 `data/lakehouse/`。智能修复在 notebook 用临时变量演示,不污染 lakehouse。

#### Scenario: 智能修复函数无写盘
- **WHEN** 检查 3 个智能修复函数源码
- **THEN** MUST NOT 包含 `write_deltalake`、`to_parquet`、`to_delta` 等写盘调用

### Requirement: 提供 Delta Lake 落库与 Time Travel 查询封装

`cleaning.py` MUST 提供 `clean_and_write_dwd(table_key: str) -> dict`(基础清洗 + 落 Delta Lake,返回行数/存储统计)与 `show_delta_history(table_key: str) -> list`(读 `_delta_log` 返回版本历史)供 notebook 一行调用演示 ACID/Time Travel。

#### Scenario: clean_and_write_dwd 落库
- **WHEN** 调用 `clean_and_write_dwd('sap_erp/vbak')`
- **THEN** MUST 将基础清洗结果写入 `data/lakehouse/dwd/sap_erp/vbak/`,返回 dict 含 before/after 行数与存储大小

#### Scenario: show_delta_history 读版本
- **WHEN** 调用 `show_delta_history('sap_erp/vbak')`
- **THEN** MUST 返回 list,每个元素含版本号与操作时间,数据来自 `_delta_log`

### Requirement: 修 oa/doc_flow 的 description bug

`scripts/ingest_to_deltalake.py` 中 `DWD_TABLES` 的 `oa/doc_flow` description MUST 改为「过滤 FLOW_TYPE/APPLY_DATE 为空」(与代码实际过滤的列一致),MUST NOT 再出现 `DOC_TYPE` 或 `CREATE_DATE`。

#### Scenario: description 与代码一致
- **WHEN** 检查 `ingest_to_deltalake.py` 的 `oa/doc_flow` DWD_TABLES description
- **THEN** MUST 包含 `FLOW_TYPE` 与 `APPLY_DATE`,MUST NOT 包含 `DOC_TYPE` 或 `CREATE_DATE`
