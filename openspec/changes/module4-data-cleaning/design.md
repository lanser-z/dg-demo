# Module 4 Data Cleaning — Design

## Context

模块四「数据清洗与质量提升」(Background §6.4)的教学空白与实现缺口:

- **清洗逻辑已存在**:`scripts/ingest_to_deltalake.py:_clean()`(148-171 行)做了去空/去重/规范化,覆盖 6 张表,真实可用
- **3 类智能修复承诺未兑现**:§6.4 把 VBAP IS_VALID_LINK 标记、PI 异常插值、LIMS 灰分修正列为待办
- **清洗逻辑锁在 CLI**:`_clean()` 是内部函数,notebook 无法调,无法做清洗前后质量分对比
- **description bug**:`oa/doc_flow` description 写 `DOC_TYPE/CREATE_DATE`,代码过滤 `FLOW_TYPE/APPLY_DATE`
- **无独立教学 notebook**:§6.4 演示剧本寄生在 module1.ipynb

**已核实数据现状**(explore 阶段):
- VBAP 孤儿行:`vbap_year=2022` 600 万行,`VBELN=0000000000` 60375 行(1%)
- PI 异常:模块二 `quality.py:55-57` 已用 `median_w * 3` 阈值识别
- LIMS 灰分:AD 范围 6.0-1199.97(正常≤90),无负值;`AD_RANGES_BY_COAL_TYPE` 在 `quality.py:14`
- 复用点:智能修复的阈值/区间常量已在 `quality.py`,cleaning.py 应复用不重复定义

**用户对齐的设计原则**:
- notebook 不堆代码,调封装函数;大段逻辑在 cleaning.py
- 不受「离线/不写」限制,可写 Delta Lake 演示 Time Travel
- 3 个待办全补

## Goals / Non-Goals

**Goals:**
- `src/dg_education/cleaning.py`:抽基础清洗 + 新增 3 类智能修复 + Delta 落库/Time Travel 封装
- `notebook/module4.ipynb`:3 步教学,调函数不堆代码,含 Delta Time Travel 演示
- 4 类清洗主张(去空/去重/规范化/智能修复),教学主张升级为「干净且修复可修复的」
- 修 description bug;ingest_to_deltalake.py 委托 cleaning.py(单一真相源)
- 清洗前后质量评分卡对比(复用模块二 run_ge_scan)

**Non-Goals:**
- 不实现定时清洗调度(Phase 2/3 范围)
- 不改 Background.md(硬约束);教学主张升级在 Module4.md/notebook 体现
- 不把智能修复默默落库到 lakehouse/dwd(业务争议,只演示)
- 不改模块一/二/三任何代码
- 不实现列级清洗规则(当前是行级)

## Decisions

### Decision 1: 抽 cleaning.py,ingest_to_deltalake.py 委托它

**选择**:新建 `src/dg_education/cleaning.py`,把 `_clean()` 抽为 `clean_basic(source, df)`;`ingest_to_deltalake.py` 的 `_clean()` 改为 `return clean_basic(source, df)` 委托调用。

**理由**:
- 单一真相源:notebook 与 CLI 共享同一份清洗规则,避免规则漂移
- notebook 能直接 import 调用(纯内存演示),不必 subprocess 跑全量入湖
- 与模块二 `ge_scan.py` 抽 CLI 的模式一致

**备选**:
- ~~notebook 用 subprocess 调 ingest_to_deltalake.py~~ → 全量入湖慢、有副作用、notebook 看不到中间 df
- ~~cleaning.py 与 _clean 并存两套规则~~ → 漂移风险

### Decision 2: 智能修复 = 改值/加列,不删行

**选择**:3 类智能修复都用「改值或加列」而非「删行」:
- IS_VALID_LINK:加布尔列,不删孤儿行
- PI 插值:超阈值 value 用 interpolate 替代,不删行
- LIMS 灰分:超区间 AD 夹逼到 [lo,hi],不删行

**理由**:
- 与基础清洗(去空去重删行)互补,形成 4 类清洗,职责清晰
- 删行会丢业务信息(孤儿行可能需源头补单),标记/修复更安全
- 教学上「修复 vs 删除」对比鲜明

**备选**:
- ~~删孤儿行~~ → 丢 60375 行业务记录,下游无法追溯
- ~~不修复只标记~~ → 与基础清洗重复,失去智能修复卖点

### Decision 3: 复用 quality.py 常量,不重复定义

**选择**:`cleaning.py` 从 `dg_education.quality` import `AD_RANGES_BY_COAL_TYPE`;PI median 3x 阈值逻辑参照 `quality.py:55-57` 实现(不 import 函数,因为 quality 那个是统计用,cleaning 要的是修复用,但阈值常量语义一致)。

**理由**:
- 灰分区间是业务规则,单一真相源
- 避免两处定义漂移(quality 改了 cleaning 没改)

**备选**:
- ~~cleaning.py 重新定义 AD_RANGES~~ → 漂移风险
- ~~把常量提到独立 constants.py~~ → 过度设计,quality.py 已是合理归属

### Decision 4: 智能修复在 notebook 用临时 df,不落 lakehouse

**选择**:`repair_*` 函数返回新 df,notebook 在临时变量上演示;`clean_and_write_dwd()` 只落基础清洗(去空去重规范化)的结果到 `data/lakehouse/dwd/`。智能修复不写盘。

**理由**:
- 修复有业务争议(插值/夹蔽是近似值),默默落库会让下游误以为是真值
- DWD 边界应保持「格式统一、可消费」,修复决策归源头/业务
- 演示用临时 df 教学效果一样(看前后对比),且不污染 lakehouse

**备选**:
- ~~智能修复也落 dwd~~ → 业务争议落库,违背 DWD 边界
- ~~完全不写 lakehouse~~ → 失去 Delta Lake/Time Travel 教学卖点

### Decision 5: notebook 调封装函数演示 Delta Time Travel

**选择**:`cleaning.py` 提供 `clean_and_write_dwd(table_key)`(内部 write_deltalake)+ `show_delta_history(table_key)`(读 _delta_log 版本)。notebook 一行调用,不看 write_deltalake 细节。

**理由**:
- 用户原则:notebook 不堆代码,大段逻辑在 script
- Delta Lake 是 §6.4 技术卖点(ACID/Schema 演进/Time Travel),需演示
- 封装后 notebook 清爽,代码后续可看 cleaning.py

### Decision 6: 清洗前后质量分对比复用模块二

**选择**:notebook 步骤 3 调 `dg_education.run_ge_scan`(模块二)对 ODS 原始 df 和清洗后 df 分别评分,对比 C/D → B/A。

**理由**:
- 模块二 GE 扫描已稳定,直接复用
- 「清洗前后质量分提升」是模块四核心教学冲击点
- GE 规则跑在 DWD(清洗只删行不改列)不会因列差异报错

## 架构图(PlantUML)

### 4 类清洗分层与数据流

```plantuml
@startuml
skinparam rectangleBackgroundColor #F5F5F5
file "data/historical/\n(ODS 原始)" as ods
rectangle "cleaning.py\n(新增)" as lib {
  rectangle "基础清洗\nclean_basic()" as basic
  rectangle "智能修复\nmark_vbap_valid_link()\nrepair_pi_anomalies()\nrepair_lims_ad()" as smart
  rectangle "Delta 封装\nclean_and_write_dwd()\nshow_delta_history()" as delta
}
file "data/lakehouse/dwd/\n(Delta Lake)" as dwd
notebook "module4.ipynb" as nb
rectangle "ingest_to_deltalake.py\n(_clean 委托)" as cli
rectangle "quality.py\n(复用常量)" as q

ods --> basic : 读 Parquet
ods --> smart : 读 Parquet\n(临时 df 演示)
q --> smart : AD_RANGES_BY_COAL_TYPE\nmedian 3x 阈值
basic --> delta : 基础清洗结果
delta --> dwd : write_deltalake\n(基础清洗落库)
delta --> dwd : 读 _delta_log\n(Time Travel)
smart -.-> nb : 返回修复前后 df\n(不落库)
nb --> lib : import 调用\n(一行函数,不堆代码)
cli --> basic : 委托\nclean_basic()
@enduml
```

### module4.ipynb 教学流程

```plantuml
@startuml
skinparam rectangleBackgroundColor #F5F5F5
notebook "module4.ipynb" as nb
state "痛点故事\n(脏数据进报表)" as s0
state "步骤1: 清洗前画像\n(cleaning.stats on ODS)" as s1
state "步骤2: 4 类清洗" as s2
state "步骤3: 质量分对比\n(run_ge_scan ODS vs DWD)" as s3
state "附加: Delta Time Travel\n(show_delta_history)" as s4

s0 --> s1
s1 --> s2
s2 --> s3
s3 --> s4
@enduml
```

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| cleaning.py 委托后 ingest_to_deltalake.py 行为变化 | `clean_basic` 逻辑与原 `_clean` 完全一致(逐行对照),tasks 加等价性验证 |
| PI 插值需先 sort+groupby,顺序错会乱插 | `repair_pi_anomalies` 内部强制 `sort_values(timestamp).groupby(tag).interpolate()`,tasks 验证 |
| LIMS 夹逼边界值是否合理(夹到 lo 还是 hi) | 超上限夹到 hi,超下限夹到 lo,语义清晰;notebook 标注「近似值非真值」 |
| 智能修复改值后 GE 评分提升是「假提升」 | notebook 明确区分:基础清洗(删脏行)的真实提升 vs 智能修复(近似)的演示性提升,不混为一谈 |
| notebook 写 Delta 有副作用(改 lakehouse/dwd) | `clean_and_write_dwd` 是覆盖写(已有行为),tasks 验证可重跑;Time Travel 读不写 |
| description bug 修复后是否影响其他文档 | 全项目搜 `DOC_TYPE/CREATE_DATE`,仅 ingest_to_deltalake.py 一处 |

## Migration Plan

**一次性 commit,分 6 组**:
1. 新建 `src/dg_education/cleaning.py`(clean_basic 抽出 + 3 智能修复 + Delta 封装)
2. 改 `scripts/ingest_to_deltalake.py`(`_clean` 委托 + description bug)
3. 扩 `src/dg_education/visualization.py`(清洗前后对比可视化)
4. 更新 `src/dg_education/__init__.py`(导出)
5. 新建 `notebook/module4.ipynb`(3 步 + Time Travel)
6. 新建 `docs/Module4.md` + 最终验证

**验证**:
- `clean_basic` 与原 `_clean` 等价(同输入同输出)
- `ingest_to_deltalake.py --layer dwd` 仍可跑
- module4.ipynb 全 cell 跑通
- 清洗前后 GE 评分有提升

**回滚**:`git revert`;cleaning.py/module4.ipynb/Module4.md 删除;ingest_to_deltalake.py 还原内联 _clean(description bug 修复保留)。

## Open Questions

无。所有决策(4 类清洗、复用常量、智能修复不落库、notebook 调封装)已基于 explore 数据核实与用户对齐。
