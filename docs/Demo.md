# A公司煤炭数据治理 Demo 指南

## 1. 环境准备

### 1.1 依赖项

```bash
# 仅需 Python 3.10+ 和 uv 包管理器
which uv && uv --version
```

### 1.2 安装

```bash
cd /home/szs/Playground/dg-demo
uv sync
```

### 1.3 目录结构

```
dg-demo/
├── pyproject.toml              # uv 项目配置
├── src/dg_simulator/           # 数据生成器源码
│   ├── __init__.py
│   ├── config.py                # 生成器配置
│   ├── base_generator.py        # 基类（质量问题注入）
│   ├── incremental_base.py      # 增量生成器基类
│   ├── sap_generator.py        # SAP 历史数据生成器
│   ├── pi_generator.py         # PI 时序历史数据生成器
│   ├── lims_generator.py       # LIMS 历史数据生成器
│   ├── sap_incremental.py      # SAP 增量生成器
│   ├── pi_incremental.py       # PI 增量生成器
│   ├── lims_incremental.py     # LIMS 增量生成器
│   ├── oa_incremental.py       # OA 增量生成器
│   └── scada_simulator.py      # SCADA 实时流模拟器（Kafka 推送）
├── scripts/
│   ├── generate_historical.py      # 批量生成历史数据（≈1GB）
│   ├── generate_incremental.py     # 每日增量数据生成
│   └── demo_asset_visualization.py # 数据资产可视化脚本
└── data/
    ├── historical/             # Parquet 分区存储
    │   ├── metadata.json           # 元数据摘要（各系统记录数）
    │   ├── sap_erp/
    │   │   ├── kna1.parquet
    │   │   ├── vbak_year=2022.parquet
    │   │   ├── vbak_year=2023.parquet
    │   │   ├── vbap_year=2022.parquet
    │   │   └── vbap_year=2023.parquet
    │   ├── pi_system/
    │   │   ├── tags_year=2022_month=01.parquet
    │   │   ├── tags_year=2022_month=02.parquet
    │   │   ├── ...
    │   │   └── tags_year=2023_month=06.parquet   # 共18个月（2022-01 ~ 2023-06）
    │   ├── lims/
    │   │   ├── samples_year=2022.parquet
    │   │   └── samples_year=2023.parquet
    │   └── oa/
    │       ├── doc_flow_year=2022.parquet
    │       └── doc_flow_year=2023.parquet
    └── incremental/            # 每日增量数据
        └── {date}/
            ├── _summary.json      # 增量批次摘要
            ├── sap_erp/
            │   ├── VBAK.parquet
            │   ├── VBAP.parquet
            │   ├── LIKP.parquet
            │   ├── LIPS.parquet
            │   └── _meta/         # 各表元数据 JSON
            ├── pi_system/
            │   ├── tags.parquet
            │   └── _meta/
            ├── lims/
            │   ├── samples.parquet
            │   └── _meta/
            └── oa/
                ├── DOC_FLOW.parquet
                ├── CONTRACT.parquet
                ├── MEETING.parquet
                └── _meta/
```

---

## 2. 数据生成

### 2.1 生成历史数据（约1GB）

```bash
uv run python scripts/generate_historical.py
```

**预期输出：**

```
============================================================
A公司 异构系统历史数据生成器 v3
VBAK=6,000,000 VBAP=12,000,000 LIMS=2,000,000 OA=5,000,000
============================================================

[1/4] SAP-ERP
  KNA1...
  ✓ KNA1 15,000 行
  VBAK 6,000,000 行...
  ✓ VBAK 6,030,000 行
  VBAP 12,000,000 行...
  ✓ VBAP 12,060,000 行
  SAP总大小: 456.3 MB

[2/4] PI-System 时序数据
  100 标签 × 1440/天 × 730 天（1min间隔）
    2022-02: 2,016,000 行
    ...
  ✓ PI-System 78,624,000 条
  PI大小: 364.6 MB

[3/4] LIMS 煤质检测
  2,000,000 行...
  ✓ LIMS 2,010,000 条
  LIMS大小: 56.3 MB

[4/4] OA 系统
  5,000,000 行...
  ✓ OA 5,025,000 条
  OA大小: 118.4 MB

============================================================
完成，耗时 149.5s | 总大小 995.6 MB
输出: /home/szs/Playground/dg-demo/data/historical
============================================================
```

**生成规模一览：**

| 系统 | 文件 | 记录数 | 存储大小 |
|------|------|--------|---------|
| SAP-ERP | kna1.parquet | 15,000 | 476 KB |
| SAP-ERP | vbak_year=2022.parquet | 303万 | 97 MB |
| SAP-ERP | vbak_year=2023.parquet | 303万 | 97 MB |
| SAP-ERP | vbap_year=2022.parquet | 603万 | 132 MB |
| SAP-ERP | vbap_year=2023.parquet | 603万 | 133 MB |
| PI-System | tags_year=*_month=*.parquet | 7862万 | 365 MB |
| LIMS | samples_year=2022.parquet | 100万 | 29 MB |
| LIMS | samples_year=2023.parquet | 100万 | 29 MB |
| OA | doc_flow_year=2022.parquet | 250万 | 60 MB |
| OA | doc_flow_year=2023.parquet | 250万 | 60 MB |
| **合计** | | **~1亿** | **995.6 MB** |

### 2.2 生成每日增量数据

```bash
# 生成指定日期范围（闭区间）
uv run python scripts/generate_incremental.py 2024-01-02 2024-01-05

# 生成今天
uv run python scripts/generate_incremental.py
```

**每日增量估算：**

| 系统 | 单日新增 | 增量模式 |
|------|---------|---------|
| SAP-ERP | ~5,000 VBAK / ~12,000 VBAP | upsert（订单可修改） |
| PI-System | ~216,000 条（100标签×2160点/天） | append |
| LIMS | ~3,000 条检测记录 | append |
| OA | ~880 条（DOC_FLOW~800 + CONTRACT~50 + MEETING~30） | append |

### 2.3 运行 SCADA 实时流模拟（可选）

```bash
# 启动 SCADA 模拟器（每秒推送一次 Kafka 消息）
uv run python -m dg_simulator.scada_simulator

# 运行 60 秒后自动停止
timeout 60 uv run python -m dg_simulator.scada_simulator
```

**SCADA 模拟数据示例：**

```
2025-05-28 14:30:01 | M001_FACE_A_RUN  | 1        # 皮带机运行
2025-05-28 14:30:01 | M001_FACE_A_ALARM | 0        # 无报警
2025-05-28 14:30:01 | M001_FACE_B_RUN  | 0        # 皮带机停止
2025-05-28 14:30:02 | M001_FACE_A_WAGAS | 0.38     # 瓦斯正常
```

---

## 3. 数据探查

### 3.1 快速查看数据集

```python
import pandas as pd

# 查看 SAP VBAK
df = pd.read_parquet("data/historical/sap_erp/vbak_year=2023.parquet")
print(df.shape)           # (3030000, 16)
print(df.dtypes)
print(df.head(3))

# 查看 PI 时序
df_pi = pd.read_parquet("data/historical/pi_system/tags_year=2023_month=01.parquet")
print(df_pi.shape)        # (4464000, 6)
print(df_pi["tag"].value_counts().head())
```

### 3.2 主数据质量探查

```python
import pandas as pd

# SAP-ERP 质量探查
vbak = pd.read_parquet("data/historical/sap_erp/vbak_year=2023.parquet")

# 1. 完整性：空值统计
print(vbak.isnull().sum())

# 2. 重复行
print(f"重复行数: {vbak.duplicated().sum()}")

# 3. 异常值检测（NETWR 订单金额）
print(f"NETWR 最大值: {vbak['NETWR'].max()}")
print(f"NETWR 为 0 的行数: {(vbak['NETWR'] == 0).sum()}")

# 4. 枚举值分布
print(vbak["AUART"].value_counts())
print(vbak["VKORG"].value_counts())
```

### 3.3 时序数据探查

```python
import pandas as pd

df_pi = pd.read_parquet("data/historical/pi_system/tags_year=2023_month=01.parquet")

# 1. 查看标签列表
print(df_pi["tag"].unique())

# 2. 检查缺失（status=-1）
missing = df_pi[df_pi["status"] == -1]
print(f"缺失点数: {len(missing)} / {len(df_pi)} ({len(missing)/len(df_pi)*100:.2f}%)")

# 3. 异常值检测（WAGAS > 1.0% 危险阈值）
wagas = df_pi[df_pi["tag"].str.contains("WAGAS")]
danger = wagas[wagas["value"] > 1.0]
print(f"危险告警次数: {len(danger)}")

# 4. 按矿井统计均值
print(df_pi.groupby("mine")["value"].describe())
```

---

## 4. 数据清洗演示

### 4.1 清洗 VBAP 关联失效

```python
import pandas as pd

vbap = pd.read_parquet("data/historical/sap_erp/vbap_year=2023.parquet")

# 检测关联失效（VBELN = 0000000000）
invalid = vbap[vbap["VBELN"] == "0000000000"]
print(f"关联失效行数: {len(invalid)}")

# 策略：标记为"脏数据"，不删除
vbap_clean = vbap.copy()
vbap_clean["IS_VALID_LINK"] = vbap_clean["VBELN"] != "0000000000"

# 关联有效率
valid_rate = vbap_clean["IS_VALID_LINK"].mean()
print(f"关联有效率: {valid_rate:.2%}")
```

### 4.2 清洗 PI 时序异常

```python
import pandas as pd
import numpy as np

df_pi = pd.read_parquet("data/historical/pi_system/tags_year=2023_month=01.parquet")

# 检测 WAGAS 异常突升（超过基线3倍）
def detect_anomaly(series, threshold_multiplier=3):
    median = series.median()
    mad = np.median(np.abs(series - median))
    upper = median + threshold_multiplier * mad * 1.4826
    return series > upper

wagas = df_pi[df_pi["tag"].str.contains("WAGAS")].copy()
wagas["IS_ANOMALY"] = detect_anomaly(wagas["value"])

print(f"异常点数: {wagas['IS_ANOMALY'].sum()} / {len(wagas)}")
print(f"异常比例: {wagas['IS_ANOMALY'].mean():.2%}")

# 策略：用前后均值填充
wagas.loc[wagas["IS_ANOMALY"], "value"] = np.nan
wagas["value"] = wagas["value"].interpolate(method="linear")
```

---

## 5. 数据质量监控演示

### 5.1 增量数据质量检查

```python
import pandas as pd
from pathlib import Path

incremental_dir = Path("data/incremental/2024-01-02")

def check_incremental_quality(date: str):
    p = Path(f"data/incremental/{date}")

    results = {}

    # SAP VBAK 完整性
    vbak = pd.read_parquet(p / "sap_erp/VBAK.parquet")
    results["vbaK_null_count"] = vbak.isnull().sum().to_dict()
    results["vbaK_duplicate"] = vbak.duplicated().sum()

    # PI 连续性
    pi = pd.read_parquet(p / "pi_system/tags.parquet")
    results["pi_missing_rate"] = (pi["status"] == -1).mean()

    # LIMS 有效性
    lims = pd.read_parquet(p / "lims/samples.parquet")
    ad_ranges = {"原煤": (10,50), "精煤": (5,15), "中煤": (15,45), "矸石": (45,90), "洗煤": (5,20)}
    invalid_lims = 0
    for st, (lo, hi) in ad_ranges.items():
        mask = lims["SAMPLE_TYPE"] == st
        invalid_lims += ((lims.loc[mask, "AD"] < lo) | (lims.loc[mask, "AD"] > hi)).sum()
    results["lims_invalid_ad"] = invalid_lims

    return results

print(check_incremental_quality("2024-01-02"))
```

---

## 6. 数据血缘演示

### 6.1 从 PI 到 SAP 的产销链路追溯

```
[PI-System]  M001_FACE_A_WAGAS  (某矿某工作面瓦斯浓度)
       │
       │  同一矿井同一工作面
       ▼
[LIMS]       LM_2023_008721     (该工作面采煤样批次)
       │
       │  批次号 CHARG → 物料号 MATNR
       ▼
[SAP-VBAP]   VBELN=1000001301 / MATNR=501010001 / CHARG=L3829
       │
       │  订单号 VBELN
       ▼
[SAP-VBAK]   VBELN=1000001301 / KUNNR=102847 / NETWR=285,000 CNY
       │
       │  客户号 KUNNR
       ▼
[SAP-KNA1]   KUNNR=102847 / NAME1="山西焦化能源集团" / STCD1=91410000...
       │
       │  触发审批
       ▼
[OA-DOC_FLOW] FL05000123 / FLOW_TYPE="付款申请" / STATUS="审批中"
```

### 6.2 血缘路径查询（代码示例）

```python
import pandas as pd

def trace_lineage(tag: str, batch_id: str):
    """从 PI 标签追溯到 OA 流程"""
    # Step 1: PI → LIMS（通过矿井编码关联）
    mine = tag.split("_")[0]  # e.g. "M001"
    lims = pd.read_parquet("data/historical/lims/samples_year=2023.parquet")
    lims_match = lims[lims["MINE_CODE"] == mine].tail(1)

    # Step 2: LIMS → SAP-VBAP（通过批次号）
    batch = lims_match.iloc[0]["SAMPLE_ID"]
    vbap = pd.read_parquet("data/historical/sap_erp/vbap_year=2023.parquet")
    vbap_match = vbap[vbap["CHARG"].str.endswith(batch[-4:], na=False)].head(1)

    # Step 3: SAP-VBAP → SAP-VBAK
    vbeln = vbap_match.iloc[0]["VBELN"]
    vbak = pd.read_parquet("data/historical/sap_erp/vbak_year=2023.parquet")
    vbak_match = vbak[vbak["VBELN"] == vbeln]

    return {
        "pi_tag": tag,
        "lims_sample": batch,
        "sap_vbap_vbeln": vbeln,
        "sap_vbak_customer": vbak_match.iloc[0]["KUNNR"] if len(vbak_match) else None,
        "sap_vbak_amount": vbak_match.iloc[0]["NETWR"] if len(vbak_match) else None,
    }

print(trace_lineage("M001_FACE_A_WAGAS", "LM008721"))
```

---

## 7. 数据安全分级演示

```python
import pandas as pd

# 标注各数据集安全级别
SECURITY_LEVELS = {
    "pi_system/tags": "核心资产",      # 实时告警阈值
    "sap_erp/vbak": "重要资产",        # 销售订单
    "sap_erp/kna1": "重要资产",        # 客户主数据
    "lims/samples": "重要资产",         # 煤质检测
    "oa/doc_flow": "一般资产",          # 流程数据
}

def classify_access(user_role: str, dataset: str):
    """简单的访问控制模拟"""
    level = SECURITY_LEVELS.get(dataset, "一般资产")
    rules = {
        "核心资产": ["安全管理员", "数据治理管理员"],
        "重要资产": ["业务分析师", "安全管理员", "数据治理管理员"],
        "一般资产": ["所有认证用户"],
    }
    allowed = user_role in rules.get(level, [])
    return {"dataset": dataset, "level": level, "access_granted": allowed}

# 测试
print(classify_access("业务分析师", "pi_system/tags"))     # False
print(classify_access("安全管理员", "pi_system/tags"))     # True
print(classify_access("业务分析师", "sap_erp/vbak"))       # True
```

---

## 8. 模拟数据规格速查

### 8.1 SAP-ERP

| 表 | 年份 | 记录数 | 列 |
|----|------|--------|-----|
| KNA1（客户主数据） | — | 15,000 | KUNNR, NAME1, ORT01, STCD1, ERDAT |
| VBAK（销售订单抬头） | 2022 | 303万 | VBELN, ERDAT, ERZET, ERNAM, AUART, KUNNR, NETWR, VKORG... |
| VBAK（销售订单抬头） | 2023 | 303万 | 同上 |
| VBAP（销售订单行项目） | 2022 | 603万 | VBELN, POSNR, MATNR, KWMENG, NETWR, CHARG, WERKS... |
| VBAP（销售订单行项目） | 2023 | 603万 | 同上 |

**质量问题：**
- NETWR/ERZET 等数值/时间字段约0.5%为空
- NETWR 约0.5%存在异常高值（ outlier）
- 约0.5%完全重复的行
- VBAP 约1%关联到无效 VBELN（`0000000000`）

### 8.2 PI-System

| 维度 | 规格 |
|------|------|
| 标签数量 | 100（5矿井 × 5工作面 × 4传感器） |
| 传感器类型 | WAGAS, TEMP, CO, CO2, PRESS, FAN_SPEED（各面取前4种） |
| 采样间隔 | 1分钟 |
| 时间范围 | 2022-01 至 2023-06（18个月） |
| 总记录数 | 7862万 |
| 存储大小 | 364.6 MB |

**传感器基线值：**

| 传感器 | 基线 | 波动特征 |
|--------|------|---------|
| WAGAS | 0.35% | 时间因子 + 噪声 σ=0.02 |
| TEMP | 22℃ | 白天+3℃，夜间-2℃ |
| CO | 5ppm | 指数分布，均值1.5 |
| CO2 | 400ppm | 正态分布，σ=15 |
| PRESS | 101.325kPa | 正态分布，σ=0.3 |
| FAN_SPEED | 1450 RPM | 正态分布，σ=20 |

**质量问题：**
- 0.5% 点位缺失（status=-1）
- 1% 异常突升（数值 × 1.5/2.0/3.0）

### 8.3 LIMS

| 字段 | 说明 |
|------|------|
| SAMPLE_ID | 格式：`LMXXXXXX`，6位数字 |
| MINE_CODE | M001-M005 |
| SAMPLE_TYPE | 原煤/精煤/中煤/矸石/洗煤 |
| AD | 灰分（%，按类型有不同合理范围） |
| QGR_AD | 收到基低位发热量（MJ/kg） |
| 全水分Mt | 5-15% |
| 全硫St | 0.3-2.5% |

**质量问题：** 0.5%空值 + 0.5% outlier + 0.5% 重复行

### 8.4 OA

OA 系统在历史数据中仅存储 `doc_flow` 表，每日增量包含 3 张表：

**历史表 `doc_flow`：**

| 字段 | 说明 |
|------|------|
| FLOW_ID | 格式：`FL00050XXXXXXX` |
| FLOW_TYPE | 请假/报销/采购申请/付款申请/用车申请/出差/公文审批/印章使用 |
| STATUS | 已完成/审批中/已驳回/已撤销 |
| AMOUNT | 仅付款/采购类流程有，约40%有值 |

**增量表 `CONTRACT`：**

| 字段 | 说明 |
|------|------|
| CONTRACT_ID | 合同编号 |
| CONTRACT_NAME | 合同名称 |
| CONTRACT_TYPE | 合同类型 |
| COUNTERPARTY | 对方单位 |
| AMOUNT | 合同金额 |
| STATUS | 合同状态 |

**增量表 `MEETING`：**

| 字段 | 说明 |
|------|------|
| MEETING_ID | 会议编号 |
| MEETING_DATE | 会议日期 |
| MEETING_TYPE | 会议类型 |
| CHAIRMAN | 主持人 |
| ATTENDEES | 参会人 |
| SUMMARY | 会议摘要 |
| DECISIONS | 决议事项 |
| FOLLOW_UP | 跟进事项 |

**质量问题：** 0.5%空值 + 0.5% outlier + 0.5% 重复行

---

## 9. 常见问题

**Q: 历史数据生成太慢怎么办？**

A: 当前 v3 版本全向量化，100标签1分钟间隔约7862万条记录在约2分钟内生成完毕。如需更快速，可将 PI 间隔调大为5分钟（减少到约1567万条）。

**Q: 如何重新生成特定系统的数据？**

A: 直接修改 `scripts/generate_historical.py` 中对应的 `run_xxx()` 函数后重新运行。历史数据每次重新生成会完整覆盖。

**Q: 增量数据如何接入真实数仓？**

A: 增量数据输出到 `data/incremental/{date}/` 后，可配置 Flume/Kafka Connect 监听该目录，或编写脚本将 Parquet 转为 CSV/JSON 后通过 API 推送至数据湖。

**Q: 如何修改矿井名称或编码？**

A: 编辑 `config/schemas/sap_erp.yaml` 和 `src/dg_simulator/lims_generator.py` 中的矿井定义，重新运行生成器即可。
