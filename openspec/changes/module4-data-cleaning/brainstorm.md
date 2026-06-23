## Feedback

| 角色 | 核心反馈 |
|------|----------|
| 用户(教学设计者) | 模块一二三已覆盖看资产/找问题/追血缘,但「发现问题后怎么把脏数据变干净」教学空白,需要模块四独立 notebook |
| 用户 | 要把原理讲清楚、演示做全面,不用受之前「离线/不写」那些限制束缚;但 notebook 里不宜出现大段代码打断思路,大段代码放 script 后续慢慢理解 |
| 用户 | Background §6.4 列的 3 个待办(VBAP IS_VALID_LINK / PI 插值 / LIMS 灰分修正)全补上 |
| Background §6.4 文档 | 现状是「干净但不修复」,3 类智能修复列为待办;演示剧本第 1 步寄生在 module1.ipynb,无独立 notebook |

## Ideas

- [x] 想法 1:从 `ingest_to_deltalake.py:_clean()` 抽出清洗逻辑为 `src/dg_education/cleaning.py`,notebook 调库而非 subprocess,避免 notebook 堆代码
- [x] 想法 2:补 VBAP `IS_VALID_LINK` 标记列(VBELN ∈ vbak.VBELN 集合),改值不删行
- [x] 想法 3:补 PI 异常值线性插值(超 3x 中位数 → interpolate),复用模块二 quality.py 阈值
- [x] 想法 4:补 LIMS 灰分夹逼修正(超煤种区间 → clamp 到 [lo,hi]),复用 quality.py `AD_RANGES_BY_COAL_TYPE`
- [x] 想法 5:notebook 调 `clean_and_write_dwd()` 落 Delta Lake,演示 ACID/Time Travel(show_delta_history)
- [x] 想法 6:清洗前后质量评分卡对比(复用模块二 run_ge_scan),演示 C/D → B/A
- [ ] 想法 7:智能修复默默落库到 lakehouse/dwd —— 否决(修复有业务争议,只演示不落库)
- [x] 想法 8:修 ingest_to_deltalake.py 的 oa/doc_flow description bug(DOC_TYPE/CREATE_DATE → FLOW_TYPE/APPLY_DATE)

## Value

| Idea | 影响的非功能属性 | 价值描述 | 是否值得转为变更? |
|------|----------------|----------|-------------------|
| 1 | 可维护性 | 清洗规则单一真相源,notebook 与 CLI 共享,避免规则漂移 | ✅ 是 |
| 2 | 准确性/可观测性 | 60375 行孤儿行现形可标记,下游可决策,教学冲击力强 | ✅ 是 |
| 3 | 准确性 | PI 时序异常修复,演示插值修复 vs 仅识别的区别 | ✅ 是 |
| 4 | 准确性 | LIMS 灰分 AD 1200→15 夹逼,演示业务规则修正 | ✅ 是 |
| 5 | 用户体验/教学完整性 | Delta Lake 是 §6.4 技术卖点,纯读会讲空;封装后 notebook 一行调用 | ✅ 是 |
| 6 | 教学完整性 | 清洗前后质量分对比是模块四核心冲击点 | ✅ 是 |
| 7 | — | 否决:修复落库有业务争议,违背「DWD 保证格式统一,质量问题归源头改单」边界 | ❌ 否 |
| 8 | 可维护性/准确性 | description 与代码不符会教错,必修 | ✅ 是 |

---

## Plan

### 立即实现

- **Idea 1-6, 8**:合成一个变更 `module4-data-cleaning`
- **初步方案**:
  - 新增 `src/dg_education/cleaning.py`:`clean_basic()`(从 _clean 抽)+ 3 个智能修复函数 + `clean_and_write_dwd()` / `show_delta_history()` 封装
  - 3 类智能修复设计原则:**改值/加列不删行**,与基础清洗(去空去重删行)互补,形成 4 类清洗主张
  - 复用 `quality.py` 的 `AD_RANGES_BY_COAL_TYPE` 与 median 3x 阈值,不重复造常量
  - 智能修复在 notebook 用临时 DataFrame 演示,不落 lakehouse(业务争议)
  - `ingest_to_deltalake.py:_clean()` 改委托 cleaning.clean_basic() + 修 description bug
  - module4.ipynb:3 步(清洗前画像 → 4 类清洗 → 质量分对比)+ Delta Time Travel 附加
- **关键设计决策**(已与用户对齐):
  - notebook 不堆代码,调封装函数;大段逻辑在 cleaning.py
  - 不受「离线/不写」限制,可写 Delta 演示 Time Travel
  - 3 待办全补
- **预计耗时**:propose→apply 全流程约 1 个会话

### 等待观察

- 无。所有决策已基于 explore 阶段数据核实(VBAP 60375 孤儿行 / PI 3x median / LIMS AD 6-1200 / quality.py 常量复用)与用户对齐。

## Explore 阶段关键发现(留痕)

- **VBAP 孤儿行**:`vbap_year=2022.parquet` 600 万行,其中 `VBELN=0000000000` 60375 行(1%,与 Background §2.3 一致)。IS_VALID_LINK = VBELN ∈ vbak.VBELN 集合
- **PI 异常**:模块二 `quality.py:55-57` 已用 `median_w * 3` 阈值识别;插值修复需先 `sort_values(timestamp)` + `groupby(tag)` 再 interpolate
- **LIMS 灰分**:AD 范围 6.0-1199.97(正常煤种≤90),AD<0 行数=0;修正=超区间夹逼到边界,非处理负值;`AD_RANGES_BY_COAL_TYPE` 在 quality.py:14
- **description bug**:`ingest_to_deltalake.py` DWD_TABLES 的 oa/doc_flow description 写 DOC_TYPE/CREATE_DATE,代码(line 170)过滤 FLOW_TYPE/APPLY_DATE(代码对描述错)
- **教学主张升级**:§6.4「干净但不修复」→「干净且修复可修复的」,在 Module4.md/notebook 体现,不改 Background.md(硬约束)
