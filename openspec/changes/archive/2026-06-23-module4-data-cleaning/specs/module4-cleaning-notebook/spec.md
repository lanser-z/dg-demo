## ADDED Requirements

### Requirement: module4.ipynb 必须以「痛点故事」cell 开头

`notebook/module4.ipynb` 的第一个 cell MUST 是 markdown cell,包含两幕对照的"痛点故事",回答"为什么需要数据清洗"。幕一 MUST 描述**脏数据进报表**的痛点(如老板看到「客户甲订了 -5000 元的煤」「精煤灰分 1200%」)。幕二 MUST 描述**清洗后**的顺利场景(报表数字可信、下游不再逐条挑异常)。两幕同一 cell,长度 < 200 中文字符。

#### Scenario: 痛点故事 cell 位于第一位
- **WHEN** 查看 module4.ipynb 第 1 个 cell
- **THEN** MUST 是 markdown,且 MUST 包含「幕一」与「幕二」标签

#### Scenario: 故事长度可控
- **WHEN** 统计该 cell 中文字符数
- **THEN** MUST < 200

### Requirement: module4.ipynb 调封装函数,不堆大段代码

`notebook/module4.ipynb` 的清洗逻辑 MUST 通过 `dg_education.cleaning` 子模块的封装函数(`clean_basic`/`mark_vbap_valid_link`/`repair_pi_anomalies`/`repair_lims_ad`/`clean_and_write_dwd`/`show_delta_history`)完成。单个 code cell 的清洗相关代码 MUST NOT 超过 10 行(调函数 + 展示结果),大段实现逻辑留在 cleaning.py。notebook 可写 Delta Lake(调 `clean_and_write_dwd`),但写盘细节不暴露在 notebook。

#### Scenario: 使用 cleaning 子模块
- **WHEN** 在 module4.ipynb 全文搜索 `clean_basic` 或 `from dg_education.cleaning` 或 `dg_education.cleaning`
- **THEN** MUST 至少 1 次命中

#### Scenario: 不内联清洗规则
- **WHEN** 检查 module4.ipynb 的 code cell
- **THEN** MUST NOT 出现 `dropna`、`drop_duplicates`、`interpolate` 等清洗原语直接调用(应通过 cleaning 函数间接调)

### Requirement: module4.ipynb 演示 4 类清洗

`notebook/module4.ipynb` 步骤 2 MUST 演示 4 类清洗:
1. 基础清洗(去空/去重/规范化):`clean_basic`,展示剔除行数与比例
2. VBAP 关联失效标记:`mark_vbap_valid_link`,展示孤儿行数(约 60375)
3. PI 异常插值:`repair_pi_anomalies`,展示修复前后曲线对比
4. LIMS 灰分夹逼:`repair_lims_ad`,展示 AD 1200→15 修正

每类 MUST 配「业务影响」白话翻译(参考 module1/2/3 风格)。

#### Scenario: 4 类清洗全覆盖
- **WHEN** 检查 module4.ipynb 步骤 2
- **THEN** MUST 调用 `clean_basic`、`mark_vbap_valid_link`、`repair_pi_anomalies`、`repair_lims_ad` 四者

#### Scenario: VBAP 孤儿行数展示
- **WHEN** 运行 `mark_vbap_valid_link` 后
- **THEN** MUST 展示 `IS_VALID_LINK=False` 的行数(约 60375)

### Requirement: module4.ipynb 演示清洗前后质量评分卡对比

`notebook/module4.ipynb` 步骤 3 MUST 调用 `dg_education.run_ge_scan`(模块二)对 ODS 原始数据与清洗后数据分别评分,展示清洗前后质量分变化(如 C/D → B/A)。MUST 明确区分:基础清洗(删脏行)的真实提升 vs 智能修复(近似值)的演示性提升,不混为一谈。

#### Scenario: 质量分对比
- **WHEN** 检查 module4.ipynb 步骤 3
- **THEN** MUST 调用 `run_ge_scan`,且 MUST 展示清洗前后两组评分

### Requirement: module4.ipynb 演示 Delta Lake Time Travel

`notebook/module4.ipynb` 附加章节 MUST 调用 `show_delta_history` 演示 Delta Lake 版本回溯(Time Travel),配 markdown 讲解 ACID 事务/Schema 演进/Time Travel 三个 Delta 优势(对应 Background §6.4 技术视角)。

#### Scenario: Time Travel 演示
- **WHEN** 检查 module4.ipynb 附加章节
- **THEN** MUST 调用 `show_delta_history`,且 MUST 包含 ACID/Schema 演进/Time Travel 的 markdown 说明

### Requirement: module4.ipynb 诚实区分真实提升与演示性提升

`notebook/module4.ipynb` MUST 在智能修复章节明确说明:插值/夹逼是**近似值非真值**,真实修正需源头系统改单;DWD 边界是「格式统一、可消费」,修复决策归源头/业务。MUST NOT 声称智能修复后的值是「真实数据」。

#### Scenario: 含诚实声明
- **WHEN** 在 module4.ipynb 全文搜索「近似值」或「非真值」或「源头」或「改单」
- **THEN** MUST 至少 1 次命中

### Requirement: module4.ipynb 末尾必须引用 module1/2/3 notebook

`notebook/module4.ipynb` 最后 1-3 个 cell 之一 MUST 包含 markdown 引用 `notebook/module1.ipynb`、`module2.ipynb`、`module3.ipynb`,让小白知道模块四与前置模块的关系(看资产→找问题→追血缘→清洗修复)。

#### Scenario: 末尾包含前置模块引用
- **WHEN** 查看 module4.ipynb 最后 1-3 个 cell
- **THEN** MUST 同时包含 `module1.ipynb`、`module2.ipynb`、`module3.ipynb` 的引用
