# 模块二实施步骤：数据质量检测与根因定位

---

## 1. 模块概述

### 1.1 教学目标

展示质量问题的自动化发现、告警和根因分析能力。

### 1.2 演示场景

| 演示场景 | 发现的问题 | 验证效果 |
|---------|-----------|---------|
| SAP VBAK 空值检测 | NETWR、ERZET 约0.5%空值 | 系统自动告警，定位到列 |
| SAP VBAP 关联失效 | 1%行项目关联到无效订单号 | 血缘断裂告警，定位影响单据 |
| PI 时序断点检测 | 0.5%点位缺失（WAGAS标签） | 连续性规则命中，定位到标签和时间段 |
| PI 异常突升检测 | 1%数值突升3倍以上 | 异常波动规则命中，列出异常时间点 |
| LIMS 煤质有效性 | AD灰分超出煤种合理范围 | 业务规则命中，列出异常样品ID |

### 1.3 质量维度

| 维度 | 说明 | 权重 |
|------|------|------|
| **完整性** | 是否有缺失值 | 30% |
| **一致性** | 跨系统/跨表数据是否一致 | 30% |
| **准确性** | 数据是否真实反映业务 | 20% |
| **唯一性** | 是否有重复记录 | 20% |

### 1.4 评分等级

| 等级 | 分数范围 | 含义 |
|------|----------|------|
| A | ≥95 | 优秀，数据可直接使用 |
| B | 85-94 | 良好，少量质量问题 |
| C | 70-84 | 及格，存在较多问题需关注 |
| D | <70 | 不及格，数据质量问题严重 |

---

## 2. 质量规则定义

### 2.1 规则引擎架构

质量检测采用 GE（Great Expectations）风格规则定义，pandas 执行引擎：

```
┌─────────────────────────────────────────────────────┐
│                    规则定义层                        │
│  scripts/run_great_expectations.py (RULES 字典)       │
│  src/dg_education/quality.py (业务质量函数)           │
└──────────────────────┬──────────────────────────────┘
                       │ expect_xxx() 调用
                       ▼
┌─────────────────────────────────────────────────────┐
│                    执行引擎层                        │
│  GE_FUNCTIONS 映射表 (pandas 实现)                   │
│  - expect_column_values_to_not_be_null              │
│  - expect_column_values_to_be_unique                │
│  - expect_column_values_to_be_between               │
│  - expect_column_value_lengths_to_be_between        │
└──────────────────────┬──────────────────────────────┘
                       │ 质量检测
                       ▼
┌─────────────────────────────────────────────────────┐
│                    报告输出层                        │
│  - 控制台彩色输出 (run_great_expectations.py)         │
│  - JSON 报告 (--output-json)                        │
│  - Jupyter Notebook (module1.ipynb 步骤2)            │
└─────────────────────────────────────────────────────┘
```

### 2.2 SAP-ERP 规则

| 表 | 规则 | 维度 | 预期问题 |
|----|------|------|----------|
| vbak | expect_column_values_to_not_be_null(VBELN) | 完整性 | — |
| vbak | expect_column_values_to_not_be_null(NETWR) | 完整性 | ~0.5% 空值 |
| vbak | expect_column_values_to_not_be_null(ERNAM) | 完整性 | ~0.5% 空值 |
| vbak | expect_column_values_to_not_be_null(KUNNR) | 完整性 | ~0.5% 空值 |
| vbak | expect_column_values_to_be_unique(VBELN) | 唯一性 | ~0.1% 重复 |
| vbak | expect_column_values_to_be_between(NETWR, min=0) | 准确性 | — |
| vbap | expect_column_values_to_not_be_null(VBELN) | 完整性 | — |
| vbap | expect_column_values_to_not_be_null(MATNR) | 完整性 | — |
| vbap | expect_column_values_to_be_unique((VBELN, POSNR)) | 唯一性 | — |
| vbap | expect_column_values_to_be_between(NETWR, min=0) | 准确性 | — |
| kna1 | expect_column_values_to_not_be_null(KUNNR) | 完整性 | — |
| kna1 | expect_column_values_to_not_be_null(NAME1) | 完整性 | — |
| kna1 | expect_column_values_to_not_be_null(STCD1) | 完整性 | — |
| kna1 | expect_column_values_to_be_unique(KUNNR) | 唯一性 | — |
| kna1 | expect_column_value_lengths_to_be_between(STCD1, 17-20) | 一致性 | — |

### 2.3 PI-System 规则

| 表 | 规则 | 维度 | 预期问题 |
|----|------|------|----------|
| tags | expect_column_values_to_not_be_null(tag) | 完整性 | — |
| tags | expect_column_values_to_not_be_null(value) | 完整性 | — |
| tags | expect_column_values_to_not_be_null(timestamp) | 完整性 | — |
| tags | expect_column_values_to_be_between(status, min=0) | 准确性 | ~0.5% status=-1 |
| tags | expect_column_values_to_be_between(value, 0-10000) | 准确性 | — |

**业务规则（src/dg_education/quality.py）：**
- `missing_pct`: status=-1 的点位比例（设备掉线）
- `wagas_danger_pct`: WAGAS value > 1.0 的比例（危险阈值）
- `wagas_anomaly_pct`: WAGAS value > 3x 中位数的比例（传感器故障）

### 2.4 LIMS 规则

| 表 | 规则 | 维度 | 预期问题 |
|----|------|------|----------|
| samples | expect_column_values_to_not_be_null(SAMPLE_ID) | 完整性 | — |
| samples | expect_column_values_to_not_be_null(AD) | 完整性 | ~0.5% 空值 |
| samples | expect_column_values_to_not_be_null(VD) | 完整性 | ~0.5% 空值 |
| samples | expect_column_values_to_not_be_null(全硫St) | 完整性 | ~0.5% 空值 |
| samples | expect_column_values_to_be_unique(SAMPLE_ID) | 唯一性 | ~0.5% 重复 |
| samples | expect_column_values_to_be_between(AD, 0-100) | 准确性 | — |
| samples | expect_column_values_to_be_between(全硫St, 0-10) | 准确性 | — |

**煤种灰分合理范围：**

| 煤种 | 灰分(AD)合理范围 | 说明 |
|------|-----------------|------|
| 原煤 | 10-50% | 高灰分原煤 |
| 精煤 | 5-15% | 低灰分精煤 |
| 中煤 | 15-45% | 中等灰分 |
| 矸石 | 45-90% | 废弃物 |
| 洗煤 | 5-20% | 洗选后产品 |

### 2.5 OA 规则

| 表 | 规则 | 维度 | 预期问题 |
|----|------|------|----------|
| doc_flow | expect_column_values_to_not_be_null(FLOW_ID) | 完整性 | — |
| doc_flow | expect_column_values_to_not_be_null(FLOW_TYPE) | 完整性 | — |
| doc_flow | expect_column_values_to_not_be_null(INITIATOR) | 完整性 | — |
| doc_flow | expect_column_values_to_be_between(AMOUNT, min=0) | 准确性 | — |

---

## 3. 执行质量检测

### 3.1 全量检测（所有系统）

```bash
cd /home/szs/Playground/dg-demo
uv run python scripts/run_great_expectations.py
```

**预期输出示例：**
```
============================================================
🔍 数据质量检测（GE 风格规则 / pandas 执行引擎）
时间: 2026-06-11 10:30:00
============================================================

============================================================
📦 SAP_ERP
============================================================

▶ vbak ... [D] 66.7% (4/6)
   🔴 FAIL: expect_column_values_to_not_be_null(NETWR) → 12,688 异常 (2.54%)
   🔴 FAIL: expect_column_values_to_not_be_null(ERNAM) → 8,234 异常 (1.65%)

▶ vbap ... [B] 100.0% (4/4)

▶ kna1 ... [A] 100.0% (5/5)

============================================================
📦 PI_SYSTEM
============================================================

▶ tags ... [D] 40.0% (2/5)
   🔴 FAIL: expect_column_values_to_be_between(status) → 2,518 异常 (0.50%)
   🔴 FAIL: expect_column_values_to_be_between(value) → 156 异常 (0.03%)

============================================================
📦 LIMS
============================================================

▶ samples ... [C] 71.4% (5/7)
   🔴 FAIL: expect_column_values_to_not_be_null(AD) → 3,421 异常 (0.68%)

============================================================
📦 OA
============================================================

▶ doc_flow ... [C] 75.0% (4/4)
   （无失败规则）

============================================================
📊 全局质量评分汇总
============================================================
系统              评分     等级     通过率       失败
------------------------------------------------------------
sap_erp           73.3      C      73.3%        4
pi_system         40.0      D      40.0%        3
lims              71.4      C      71.4%        2
oa                75.0      C      75.0%        1
------------------------------------------------------------
平均              64.9

✅ 检测完成，耗时 45.2s
```

### 3.2 单系统检测

```bash
# 仅检测 SAP-ERP
uv run python scripts/run_great_expectations.py --system sap_erp

# 仅检测 PI-System
uv run python scripts/run_great_expectations.py --system pi_system

# 仅检测 LIMS
uv run python scripts/run_great_expectations.py --system lims

# 仅检测 OA
uv run python scripts/run_great_expectations.py --system oa
```

### 3.3 输出 JSON 报告

```bash
uv run python scripts/run_great_expectations.py --output-json data/quality_report.json
```

**JSON 报告结构：**
```json
{
  "timestamp": "2026-06-11T10:30:00",
  "overall_avg_score": 64.9,
  "results": {
    "sap_erp": [...],
    "pi_system": [...],
    "lims": [...],
    "oa": [...]
  },
  "summary": [
    {"system": "sap_erp", "score": 73.3, "grade": "C", ...},
    {"system": "pi_system", "score": 40.0, "grade": "D", ...},
    {"system": "lims", "score": 71.4, "grade": "C", ...},
    {"system": "oa", "score": 75.0, "grade": "C", ...}
  ]
}
```

---

## 4. 根因定位分析

### 4.1 SAP VBAP 关联失效分析

**问题描述**：VBAP 行项目中约 1% 关联到无效订单号（VBELN='0000000000'）

```bash
# 分析无效关联的分布
uv run python -c "
import pandas as pd

df = pd.read_parquet('data/historical/sap_erp/vbap_year=2022.parquet')
invalid = df[df['VBELN'] == '0000000000']
print(f'总行数: {len(df):,}')
print(f'无效关联: {len(invalid):,} ({len(invalid)/len(df)*100:.2f}%)')
print(f'影响订单类型分布:')
print(invalid['AUART'].value_counts().head(10))
"
```

**根因分析**：无效关联行主要集中在特定订单类型（AUART），需联系 SAP 顾问排查该类型订单的创建逻辑。

### 4.2 PI 时序断点分析

**问题描述**：PI 系统每日约 0.5% 的点位数据缺失

```bash
# 分析 WAGAS 标签的缺失情况
uv run python -c "
import pandas as pd

df = pd.read_parquet('data/historical/pi_system/tags_year=2022_month=01.parquet')
wagas = df[df['tag'].str.contains('WAGAS', na=False)]
missing = wagas[wagas['status'] == -1]
print(f'WAGAS 标签总数: {len(wagas):,}')
print(f'缺失数据: {len(missing):,} ({len(missing)/len(wagas)*100:.2f}%)')
print(f'缺失标签分布:')
print(missing['tag'].value_counts().head(10))
"
```

**根因分析**：设备掉线是主因，需检查传感器网络连接和采集网关状态。

### 4.3 PI 异常突升分析

**问题描述**：传感器数据存在约 1% 的异常波动（WAGAS 读数突增 3 倍以上）

```bash
# 分析异常突升的标签和时间
uv run python -c "
import pandas as pd

df = pd.read_parquet('data/historical/pi_system/tags_year=2022_month=01.parquet')
wagas = df[df['tag'].str.contains('WAGAS', na=False)]
median_w = wagas['value'].median()
threshold = median_w * 3
anomaly = wagas[wagas['value'] > threshold]
print(f'WAGAS 中位数: {median_w:.4f}')
print(f'异常阈值 (3x): {threshold:.4f}')
print(f'异常记录数: {len(anomaly):,} ({len(anomaly)/len(wagas)*100:.2f}%)')
print(f'异常标签:')
print(anomaly['tag'].value_counts().head(10))
"
```

**根因分析**：需判断是设备故障（传感器漂移）还是真实异常（瓦斯涌出）。

### 4.4 LIMS 煤质有效性分析

**问题描述**：部分样品的灰分超出煤种合理范围

```bash
# 分析异常样品的分布
uv run python -c "
import pandas as pd

df = pd.read_parquet('data/historical/lims/samples_year=2022.parquet')
ad_ranges = {
    '原煤': (10, 50),
    '精煤': (5, 15),
    '中煤': (15, 45),
    '矸石': (45, 90),
    '洗煤': (5, 20),
}

invalid_samples = []
for stype, (lo, hi) in ad_ranges.items():
    mask = df['SAMPLE_TYPE'] == stype
    if mask.any():
        ad_vals = df.loc[mask, 'AD']
        invalid = df.loc[mask & ((ad_vals < lo) | (ad_vals > hi))]
        invalid_samples.extend(invalid['SAMPLE_ID'].tolist())

print(f'异常样品总数: {len(invalid_samples):,}')
print(f'异常率: {len(invalid_samples)/len(df)*100:.2f}%')
"
```

**根因分析**：可能是采样记录错误或化验操作失误，需联系煤质中心核实。

---

## 5. 质量评分卡

### 5.1 四维评分计算

质量评分通过 `src/dg_education/quality.py` 中的函数计算：

```python
from src.dg_education.quality import (
    check_sap_quality,
    check_pi_quality,
    check_lims_quality,
    check_oa_quality,
    calc_quality_score,
)

# 加载数据
vbak = pd.read_parquet('data/historical/sap_erp/vbak_year=2022.parquet')
vbap = pd.read_parquet('data/historical/sap_erp/vbap_year=2022.parquet')
kna1 = pd.read_parquet('data/historical/sap_erp/kna1.parquet')
df_pi = pd.read_parquet('data/historical/pi_system/tags_year=2022_month=01.parquet')
df_lims = pd.read_parquet('data/historical/lims/samples_year=2022.parquet')
df_oa = pd.read_parquet('data/historical/oa/doc_flow_year=2022.parquet')

# 计算各系统质量分数
sap_scores = check_sap_quality(vbak, vbap, kna1)
pi_scores = check_pi_quality(df_pi)
lims_scores = check_lims_quality(df_lims)
oa_scores = check_oa_quality(df_oa)

# 组装评分卡
system_scores = {
    "SAP-ERP": sap_scores,
    "PI-System": pi_scores,
    "LIMS": lims_scores,
    "OA": oa_scores,
}

scorecard = calc_quality_score(system_scores)
print(scorecard)
```

### 5.2 评分卡输出示例

```
              完整性    一致性    准确性    唯一性    综合得分
系统
SAP-ERP        97.5     95.0     98.0     99.5       97.4
PI-System      99.5     95.0     98.0     99.9       98.1
LIMS           98.0     95.5     97.0     99.5       97.5
OA             99.0     96.0     99.0     99.8       98.4
```

---

## 6. 教学演示流程

### 6.1 演示一：质量检测全流程（10分钟）

**教学目标**：用 GE 规则引擎发现数据质量问题

```
Step 1: 启动服务
  docker compose -f datahub-quickstart.yml up -d
  → 确认 DataHub 服务健康

Step 2: 运行质量检测
  uv run python scripts/run_great_expectations.py
  → 查看各系统评分和失败规则

Step 3: 定位根因
  选择一个失败规则，分析其影响范围
  → 定位到具体列、时间段、样品ID

Step 4: 生成报告
  uv run python scripts/run_great_expectations.py --output-json data/quality_report.json
  → 查看 JSON 报告结构
```

**Before**：不知道数据质量如何
**After**：量化评分 + 失败规则详情，质量问题一目了然

### 6.2 演示二：业务质量函数（10分钟）

**教学目标**：使用业务语义的质量检测函数

教学入口：`notebook/module1.ipynb` → 「步骤 2：质量评分卡 + 业务影响翻译」

```bash
# Jupyter 环境
jupyter notebook notebook/module1.ipynb
# → 运行"步骤 2"单元格
```

**关键函数：**
- `check_sap_quality()`: SAP-ERP 业务规则（无效关联、空值、重复）
- `check_pi_quality()`: PI-System 业务规则（设备掉线、危险值、异常突升）
- `check_lims_quality()`: LIMS 业务规则（灰分范围、重复检测）
- `check_oa_quality()`: OA 业务规则（重复、状态异常）

---

## 7. 快速启动命令汇总

```bash
# 一键启动 DataHub（如果尚未启动）
docker compose -f datahub-quickstart.yml up -d

# 全量质量检测
uv run python scripts/run_great_expectations.py

# 单系统检测
uv run python scripts/run_great_expectations.py --system sap_erp
uv run python scripts/run_great_expectations.py --system pi_system
uv run python scripts/run_great_expectations.py --system lims
uv run python scripts/run_great_expectations.py --system oa

# 输出 JSON 报告
uv run python scripts/run_great_expectations.py --output-json data/quality_report.json

# 教学入口（Jupyter Notebook）
jupyter notebook notebook/module1.ipynb
```

---

## 8. 当前状态

**质量规则层（100%）**
- [x] GE 风格规则定义（scripts/run_great_expectations.py）
- [x] 4 系统全覆盖（sap_erp / pi_system / lims / oa）
- [x] 评分等级 A/B/C/D 自动判定
- [x] JSON 格式质量报告输出

**业务质量函数层（100%）**
- [x] check_sap_quality() - SAP-ERP 业务规则
- [x] check_pi_quality() - PI-System 业务规则（WAGAS 异常、缺失）
- [x] check_lims_quality() - LIMS 业务规则（灰分范围）
- [x] check_oa_quality() - OA 业务规则

**四维评分层（100%）**
- [x] 完整性、一致性、准确性、唯一性 四个维度
- [x] 30/30/20/20 权重配置
- [x] calc_quality_score() 综合评分计算

**演示场景层（100%）**
- [x] SAP VBAK 空值检测（NETWR、ERNAM）
- [x] SAP VBAP 关联失效检测（VBELN='0000000000'）
- [x] PI 时序断点检测（status=-1）
- [x] PI 异常突升检测（WAGAS > 3x 中位数）
- [x] LIMS 煤质有效性检测（AD 超出煤种范围）

**待提升项（Phase 2/3）**
- [ ] 定时调度（Airflow DAG 每日凌晨自动跑）
- [ ] 告警通知（邮件/钉钉/飞书）
- [ ] 质量分数历史趋势（ClickHouse 存储 + 折线图）
- [ ] 问题工单自动派发（OA 集成）
- [ ] 实时质量监控（Flink 流式规则引擎）
