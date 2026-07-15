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
├── pyproject.toml
├── src/
│   ├── dg_simulator/           # 数据生成器
│   │   ├── config.py              # 配置读取（从 config.toml）
│   │   ├── base_generator.py      # 基类（质量问题注入）
│   │   ├── incremental_base.py    # 增量生成器基类
│   │   ├── sap_generator.py       # SAP 历史数据生成器
│   │   ├── pi_generator.py        # PI 历史数据生成器
│   │   ├── lims_generator.py      # LIMS 历史数据生成器
│   │   ├── sap_incremental.py     # SAP 增量生成器
│   │   ├── pi_incremental.py      # PI 增量生成器
│   │   ├── lims_incremental.py    # LIMS 增量生成器
│   │   ├── oa_incremental.py      # OA 增量生成器
│   │   └── scada_simulator.py     # SCADA 实时流模拟器（设备状态机）
│   ├── dg_platform/             # 数据治理平台核心
│   │   ├── asset_visualizer.py    # 资产可视化（系统状态/目录/评分/分级）
│   │   ├── data_profiler.py       # 数据探查（行数/大小/分区发现）
│   │   ├── datahub_client.py      # DataHub 元数据平台集成
│   │   └── lineage_emitter.py     # 血缘上报
│   └── dg_education/            # 教学用例
│       ├── quality.py              # 数据质量检测
│       ├── cleaning.py             # 数据清洗
│       ├── lineage.py              # 血缘分析
│       ├── visualization.py       # 可视化
│       └── business_impact.py      # 业务影响量化
├── scripts/
│   ├── generate_historical.py      # 批量生成历史数据
│   ├── generate_incremental.py     # 每日增量数据生成
│   └── demo_asset_visualization.py # 数据资产可视化脚本
├── openspec/specs/               # OpenSpec 变更规格
│   ├── step1-onboarding/            # 模块一：数据资产可视化
│   ├── module2-quality-detection/   # 模块二：数据质量检测
│   ├── module3-lineage-notebook/   # 模块三：数据血缘
│   ├── auto-lineage-collection/     # 自动化血缘采集
│   ├── quality-root-cause-analysis/ # 质量问题根因分析
│   └── ...（共 25 个规格）
└── data/
    ├── historical/             # Parquet 分区存储
    │   ├── metadata.json           # 元数据摘要
    │   ├── sap_erp/
    │   │   ├── kna1.parquet            # 客户主数据
    │   │   ├── vbak_year=2022.parquet  # 销售订单抬头
    │   │   ├── vbak_year=2023.parquet
    │   │   ├── vbap_year=2022.parquet  # 销售订单行项目
    │   │   └── vbap_year=2023.parquet
    │   ├── pi_system/
    │   │   ├── tags_year=2022_month=01.parquet
    │   │   ├── tags_year=2022_month=02.parquet
    │   │   └── ...（至 2023-06，共 18 个月）
    │   └── oa/
    │       ├── doc_flow_year=2022.parquet  # 审批流程记录
    │       └── doc_flow_year=2023.parquet
    └── incremental/
        └── {date}/
            ├── _summary.json
            ├── sap_erp/       (VBAK / VBAP / LIKP / LIPS + _meta/)
            ├── pi_system/    (tags.parquet + _meta/)
            ├── lims/         (samples.parquet + _meta/)
            └── oa/           (DOC_FLOW / CONTRACT / MEETING + _meta/)
```

> **注意**：LIMS 历史数据不单独输出到 `data/historical/lims/`，而是在增量脚本 `generate_incremental.py` 的 `scripts/` 同级目录中通过 `LIMSIncrementalGenerator` 生成。若需历史 LIMS 数据，需单独运行或修改 `generate_historical.py`。

---

## 2. 数据生成

### 2.1 生成历史数据

```bash
uv run python scripts/generate_historical.py
```

**数据规模一览：**

| 系统 | 表/文件 | 记录数（估算） | 说明 |
|------|---------|---------------|------|
| SAP-ERP | KNA1 | 15,000 | 客户主数据 |
| SAP-ERP | VBAK | 600万 | 销售订单抬头（2022+2023 各半） |
| SAP-ERP | VBAP | 1200万 | 销售订单行项目（2022+2023 各半） |
| PI-System | TAGS | 7862万 | 100 标签 × 1440点/天 × 730天 |
| LIMS | SAMPLES | 200万 | 煤质检测样品（2022+2023 各半） |
| OA | DOC_FLOW | 500万 | 审批流程（2022+2023 各半） |

> **PI 标签拓扑**：5 矿井 × 5 工作面 × 4 传感器（瓦斯/温度/一氧化碳/二氧化碳）= **100 标签**，采样间隔 1 分钟，时间范围 2022-01 ~ 2023-06（18 个月）。

### 2.2 生成每日增量数据

```bash
# 生成指定日期范围（闭区间）
uv run python scripts/generate_incremental.py 2024-01-02 2024-01-05

# 生成今天
uv run python scripts/generate_incremental.py

# 多天并行生成（当前串行，可选 --parallel）
uv run python scripts/generate_incremental.py 2024-01-01 2024-01-31 --parallel
```

**每日增量估算（实际值由生成器随机波动）：**

| 系统 | 表 | 单日新增（估算） | 增量模式 |
|------|----|----------------|---------|
| SAP-ERP | VBAK | ~4,000 条 | upsert |
| SAP-ERP | VBAP | ~10,000 条 | upsert |
| SAP-ERP | LIKP | ~2,600 条 | upsert（交货单头） |
| SAP-ERP | LIPS | ~5,800 条 | upsert（交货单行） |
| PI-System | TAGS | ~43,200 条（150 标签 × 288 点） | append |
| LIMS | SAMPLES | ~3,000 条 | append |
| OA | DOC_FLOW | ~800 条 | append |
| OA | CONTRACT | ~50 条 | append |
| OA | MEETING | ~30 条 | append |

> **PI 增量说明**：历史数据用 1 分钟间隔（1440 点/天/标签），增量用 5 分钟间隔（288 点/天/标签），目的是平衡数据体积与时间粒度。PI 增量标签拓扑为 2+3+2+3+2=12 个工作面 × 6 传感器 = **150 标签**，与历史数据不同（历史 100 标签 × 4 传感器）。

### 2.3 SCADA 实时流模拟（可选）

SCADA 模拟器是独立于 PI-System 的**设备状态机模拟器**，推送皮带机/排水泵/通风机/提升机/采煤机等实时设备数据，**不经过 PI-System**。

```bash
# 启动（每秒推送一次，持续运行直到 Ctrl+C）
uv run python -m dg_simulator.scada_simulator

# 运行 60 秒后自动停止
timeout 60 uv run python -m dg_simulator.scada_simulator
```

**SCADA 点位清单（共 30+ 个）：**

| 分类 | 点位 | 类型 | 说明 |
|------|------|------|------|
| 皮带运输 | BELT_001_SPEED, BELT_001_STATUS, ... | float/int | 皮带速度(0~5m/s)、状态(1=运行/2=停止/3=故障) |
| 排水系统 | PUMP_001_STATUS, PUMP_001_FLOW, ... | int/float | 排水泵状态(0~3)、流量(0~200m³/h)、压力 |
| 通风系统 | FAN_001_SPEED, FAN_001_TEMP, ... | float | 风机转速(0~1500rpm)、温度(0~80℃)、状态 |
| 提升系统 | HOIST_001_POSITION/SPEED/STATUS/LOAD | float/int | 提升机位置/速度/状态/载重 |
| 采煤系统 | SHIELD_001_PRESSURE, MINER_001_STATUS | float/int | 液压支架压力(0~50MPa)、采煤机状态 |
| 环境监测 | CH4_001_LEVEL, CO_001_LEVEL, TEMP_001_LEVEL | float | 甲烷(0~10%)、一氧化碳(0~100ppm)、温度 |

**输出示例（含报警）：**

```
2025-05-28T14:30:02.123456 [🚨报警] CH4_001_LEVEL=0.85%
2025-05-28T14:30:02.234567 [⚠️预警] BELT_001_SPEED=4.42m/s
2025-05-28T14:30:03.001234 [正常]  PUMP_001_STATUS=1
```

---

## 3. 数据探查

### 3.1 快速查看数据集

```python
import pandas as pd

# 查看 SAP VBAK
df = pd.read_parquet("data/historical/sap_erp/vbak_year=2023.parquet")
print(df.shape)
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

# 3. 坏点检测（status=-2，值为 99999）
bad = df_pi[df_pi["status"] == -2]
print(f"坏点数: {len(bad)} / {len(df_pi)} ({len(bad)/len(df_pi)*100:.2f}%)")

# 4. 异常值检测（WAGAS > 1.0% 危险阈值）
wagas = df_pi[df_pi["tag"].str.contains("WAGAS")]
danger = wagas[wagas["value"] > 1.0]
print(f"危险告警次数: {len(danger)}")

# 5. 按矿井统计均值
print(df_pi.groupby("mine")["value"].describe())
```

---

## 4. 数据质量监控演示

### 4.1 增量数据质量检查

```python
import pandas as pd
from pathlib import Path

def check_incremental_quality(date: str):
    p = Path(f"data/incremental/{date}")

    results = {}

    # SAP VBAK 完整性
    vbak = pd.read_parquet(p / "sap_erp/VBAK.parquet")
    results["vbaK_null_count"] = vbak.isnull().sum().to_dict()
    results["vbaK_duplicate"] = vbak.duplicated().sum()

    # PI 连续性（status=-1 为缺失，status=-2 为坏点）
    pi = pd.read_parquet(p / "pi_system/tags.parquet")
    results["pi_missing_rate"] = (pi["status"] == -1).mean()
    results["pi_bad_point_rate"] = (pi["status"] == -2).mean()

    # LIMS 有效性（灰分按煤种有合理范围）
    lims = pd.read_parquet(p / "lims/samples.parquet")
    ad_ranges = {"原煤": (15,35), "精煤": (6,12), "中煤": (20,40), "矸石": (50,80), "洗煤": (8,18)}
    invalid_lims = 0
    for st, (lo, hi) in ad_ranges.items():
        mask = lims["SAMPLE_TYPE"] == st
        if mask.any():
            invalid_lims += ((lims.loc[mask, "AD"] < lo) | (lims.loc[mask, "AD"] > hi)).sum()
    results["lims_invalid_ad"] = invalid_lims

    return results

print(check_incremental_quality("2024-01-02"))
```

---

## 5. 数据资产可视化

运行可视化脚本，快速了解 5 个系统的接入状态、资产目录、质量评分和安全分级：

```bash
uv run python scripts/demo_asset_visualization.py
```

**系统定义（`src/dg_platform/asset_visualizer.py`）：**

| 系统 | 显示名 | 负责部门 | 安全级别 | 表 |
|------|--------|---------|---------|-----|
| SAP-ERP | SAP企业资源计划 | 销售部 | 重要资产 | VBAK, VBAP, KNA1, MARA, LIKP, LIPS |
| PI-System | PI实时数据系统 | 安全部 | 核心资产 | TAGS |
| SCADA | SCADA数据采集系统 | 调度中心 | 核心资产 | EQUIPMENT_STATUS |
| LIMS | 实验室信息管理系统 | 煤质中心 | 重要资产 | SAMPLES |
| OA | 办公自动化系统 | 综合管理部 | 一般资产 | DOC_FLOW, CONTRACT, MEETING |

---

## 6. 数据血缘演示

### 6.1 从 PI 到 SAP 的产销链路追溯

```
[PI-System]  MINE_001_FACE_A1_WAGAS  (某矿某工作面瓦斯浓度)
       │
       │  同一矿井同一工作面
       ▼
[LIMS]       LM1000001              (该工作面采煤样批次)
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

### 6.2 血缘路径查询

```python
import pandas as pd

def trace_lineage(tag: str, batch_id: str):
    """从 PI 标签追溯到 OA 流程"""
    # Step 1: PI → LIMS（通过矿井编码关联）
    mine = tag.split("_")[1]  # e.g. "MINE_001"
    lims = pd.read_parquet("data/historical/lims/samples_year=2023.parquet")
    lims_match = lims[lims["MINE_CODE"] == mine.replace("MINE_", "M")].tail(1)

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

print(trace_lineage("MINE_001_FACE_A1_WAGAS", "LM100001"))
```

---

## 7. 数据安全分级演示

```python
import pandas as pd

# 标注各数据集安全级别
SECURITY_LEVELS = {
    "PI-System/TAGS":    "核心资产",   # 实时告警阈值
    "SCADA":             "核心资产",   # 设备安全
    "SAP-ERP/VBAK":      "重要资产",   # 销售订单
    "SAP-ERP/KNA1":      "重要资产",   # 客户主数据
    "LIMS/SAMPLES":      "重要资产",   # 煤质检测
    "OA":                "一般资产",   # 流程数据
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
print(classify_access("业务分析师", "PI-System/TAGS"))     # False
print(classify_access("安全管理员", "PI-System/TAGS"))     # True
print(classify_access("业务分析师", "SAP-ERP/VBAK"))       # True
```

---

## 8. 模拟数据规格速查

### 8.1 SAP-ERP

| 表 | 年份 | 记录数 | 关键列 |
|----|------|--------|--------|
| KNA1（客户主数据） | — | 15,000 | KUNNR, NAME1, ORT01, STCD1, ERDAT |
| VBAK（销售订单抬头） | 2022 | ~303万 | VBELN, ERDAT, AUART, KUNNR, NETWR, VKORG... |
| VBAK（销售订单抬头） | 2023 | ~303万 | 同上 |
| VBAP（销售订单行项目） | 2022 | ~603万 | VBELN, POSNR, MATNR, KWMENG, CHARG, WERKS... |
| VBAP（销售订单行项目） | 2023 | ~603万 | 同上 |

**质量问题：**
- 单元格空值：~0.5%
- 单元格异常值（outlier）：~0.5%
- 完全重复行：~0.5%
- VBAP 关联失效（VBELN=`0000000000`）：~1%

### 8.2 PI-System

| 维度 | 历史数据 | 增量数据 |
|------|---------|---------|
| 标签数量 | 100（5矿×5面×4传感器） | 150（12工作面×6传感器） |
| 传感器 | WAGAS, TEMP, CO, CO2 | WAGAS, TEMP, CO, CO2, PRESS, FAN_SPEED |
| 采样间隔 | 1 分钟 | 5 分钟 |
| 时间范围 | 2022-01 ~ 2023-06 | 每日追加 |
| 总记录数（历史） | ~7862万 | ~43,200 条/天 |

**传感器基线值：**

| 传感器 | 基线 | 波动特征 |
|--------|------|---------|
| WAGAS | 0.35% | 时间因子 + 噪声 σ=0.02 |
| TEMP | 22℃ | 白天+3℃，夜间-2℃ |
| CO | 5ppm | 指数分布，均值1.5 |
| CO2 | 400ppm | 正态分布，σ=15 |

**质量问题（历史）：**
- 0.5% 点位缺失（status=-1）
- 1% 异常突升（数值 × 1.5/2.0/3.0）

**质量问题（增量）：**
- 0.5% 缺失（status=-1）
- 1% 坏点（value=99999, status=-2）

### 8.3 LIMS

| 字段 | 说明 |
|------|------|
| SAMPLE_ID | 格式：`LMXXXXXX`，6位数字 |
| MINE_CODE | M001-M005 |
| SAMPLE_TYPE | 原煤/精煤/中煤/矸石/洗煤 |
| AD | 灰分（%，按类型有合理范围） |
| VD | 挥发分（%） |
| FC | 固定碳（%） |
| QGR_AD | 收到基低位发热量（MJ/kg） |
| 全水分Mt | 5-15% |
| 全硫St | 0.3-2.5% |
| Mar | 水分（收到基，8-20%） |
| 全磷P / 全砷As | 微量元素（部分煤种较高） |
| 粒度 | <50mm / 50-100mm / >100mm / 混煤 |
| SAMPLING_POINT | 矿井内具体采样位置 |

**质量问题：** ~0.5% 空值 + ~0.5% outlier + ~0.5% 重复行

### 8.4 OA

**历史表 `doc_flow`：**

| 字段 | 说明 |
|------|------|
| FLOW_ID | 格式：`FLXXXXXXXX` |
| DOC_NO | 格式：`DOCYYYYXXXXX` |
| FLOW_TYPE | 请假/报销/采购申请/付款申请/用车申请/出差/公文审批/印章使用 |
| INITIATOR | 发起人 |
| INITIATOR_DEPT | 发起人部门 |
| STATUS | 已完成/审批中/已驳回/已撤销 |
| CURRENT_NODE | 当前审批节点 |
| AMOUNT | 仅付款/采购类流程有，约40%有值 |

**增量表 `CONTRACT`：**

| 字段 | 说明 |
|------|------|
| CONTRACT_ID | 合同编号（格式：`CTYYYYXXXXX`） |
| CONTRACT_NAME | 合同名称 |
| CONTRACT_TYPE | 采购合同/销售合同/服务合同/租赁合同/施工合同/运输合同 |
| COUNTERPARTY | 对方单位 |
| SIGN_DATE | 签约日期 |
| EFFECTIVE_DATE | 生效日期 |
| EXPIRY_DATE | 到期日期 |
| AMOUNT | 合同金额（5万~5000万） |
| PAYMENT_TERM | 付款条件 |
| STATUS | 执行中/已终止/已到期 |
| CONTRACT_MANAGER | 合同管理员 |
| DEPT | 负责部门 |

**增量表 `MEETING`：**

| 字段 | 说明 |
|------|------|
| MEETING_ID | 会议编号 |
| MEETING_DATE | 会议日期 |
| MEETING_TYPE | 安全生产例会/生产调度会/技术研讨会/班前会/专题会 |
| VENUE | 会议地点 |
| CHAIRMAN | 主持人 |
| RECORDER | 记录人 |
| ATTENDEES | 参会人（逗号分隔） |
| SUMMARY | 会议摘要 |
| DECISIONS | 决议事项 |
| FOLLOW_UP | 跟进事项 |

**质量问题：** ~0.5% 空值 + ~0.5% outlier + ~0.5% 重复行

### 8.5 SCADA

独立于 PI-System 的设备状态流模拟器，共 30+ 个点位：

| 分类 | 点位前缀 | 值域 | 报警逻辑 |
|------|---------|------|---------|
| 皮带机 | BELT_001_SPEED/STATUS | 速度0~5m/s，状态1~3 | 速度>4.5m/s报警 |
| 排水泵 | PUMP_001_STATUS/FLOW/PRESSURE | 流量0~200m³/h，压力0~2MPa | 流量>180m³/h报警 |
| 通风机 | FAN_001_SPEED/TEMP/STATUS | 转速0~1500rpm，温度0~80℃ | 转速>1450rpm报警 |
| 提升机 | HOIST_001_POSITION/SPEED/STATUS/LOAD | 位置0~500m，速度0~10m/s | 超载>18t报警 |
| 采煤机 | SHIELD_001_PRESSURE, MINER_001_STATUS | 压力0~50MPa，状态0~4 | 压力>45MPa报警 |
| 环境 | CH4_001_LEVEL, CO_001_LEVEL, TEMP_001_LEVEL | 甲烷0~10%，CO 0~100ppm | 甲烷>0.8%报警 |

**状态值含义（int 型）：**
- 皮带机：1=运行 2=停止 3=故障
- 排水泵：0=停止 1=运行 2=故障 3=备用
- 提升机：0=到位 1=上行 2=下行 3=急停

---

## 9 Parquet 文件字段说明

本节说明各 Parquet 文件中所有列的业务含义。字段来源为 `src/dg_simulator/` 下各生成器源码。

### 9.1 SAP-ERP

#### KNA1（客户主数据）

| 字段 | 类型 | 业务含义 |
|------|------|---------|
| KUNNR | VARCHAR(6) | 客户编码，6位数字，主键 |
| NAME1 | VARCHAR | 客户名称 |
| NAME2 | VARCHAR | 客户名称2（分公司/分支机构） |
| ORT01 | VARCHAR | 客户所在城市 |
| STCD1 | VARCHAR | 统一社会信用代码（18位） |
| STCD2 | VARCHAR | 纳税人识别号 |
| TELF1 | VARCHAR | 联系电话 |
| ERDAT | VARCHAR | 记录创建日期（YYYY-MM-DD） |

#### VBAK（销售订单抬头）

| 字段 | 类型 | 业务含义 |
|------|------|---------|
| VBELN | VARCHAR(10) | 销售凭证号（订单号），主键 |
| ERDAT | VARCHAR | 凭证日期（YYYY-MM-DD） |
| ERZET | VARCHAR | 凭证时间（HHMMSS） |
| ERNAM | VARCHAR | 创建人 |
| AUART | VARCHAR | 订单类型（OR=标准销售, ZOR=出口, RET=退货） |
| KUNNR | VARCHAR(6) | 客户编码，外键→KNA1 |
| NETWR | DECIMAL | 订单净价（CNY） |
| WAERK | VARCHAR | 货币代码（固定CNY） |
| BZIRK | VARCHAR | 销售区域（D001-D005） |
| VKORG | VARCHAR | 销售组织（CN01/CN02/CN03） |
| VTWEG | VARCHAR | 分销渠道（10=直销, 20=分销） |
| SPART | VARCHAR | 产品组（00=通用, 01/02/03=专项） |
| BSTNK | VARCHAR | 客户采购订单号 |
| IHREZ | VARCHAR | 客户参考文本 |
| FABKL | VARCHAR | 工厂所在国家 |
| LIFSK | VARCHAR | 交货冻结标识（C=冻结, 空=正常） |
| FAKSK | VARCHAR | 开票冻结标识（C=冻结, 空=正常） |

#### VBAP（销售订单行项目）

| 字段 | 类型 | 业务含义 |
|------|------|---------|
| VBELN | VARCHAR(10) | 关联的销售凭证号，外键→VBAK |
| POSNR | VARCHAR(6) | 行项目号（000001-099999） |
| MATNR | VARCHAR | 物料编码（9位数字，501XXXXXX） |
| KWMENG | DECIMAL | 销售数量（计量单位见VRKME） |
| VRKME | VARCHAR | 销售计量单位（TO=吨） |
| NETWR | DECIMAL | 行项目净价（CNY） |
| WAERK | VARCHAR | 货币代码 |
| CHARG | VARCHAR | 批次号（L+4位数字） |
| WERKS | VARCHAR | 工厂编码（CN01/CN02/CN03） |
| LGORT | VARCHAR | 库存地点（FG01/FG02=成品, RM01=原料） |
| EDATU | VARCHAR | 交货日期（YYYY-MM-DD，增量数据有） |

#### LIKP（交货单抬头，增量数据）

| 字段 | 类型 | 业务含义 |
|------|------|---------|
| VBELN | VARCHAR(10) | 交货单号（与订单号段区分） |
| ERDAT | VARCHAR | 创建日期 |
| ERZET | VARCHAR | 创建时间 |
| KUNNR | VARCHAR(6) | 客户编码 |
| VSTEL | VARCHAR | 装运点（DC01/DC02/DC03） |
| LIFEX | VARCHAR | 外部交货号 |
| WOERK | VARCHAR | 工厂 |
| WADAT | VARCHAR | 计划发货日期 |
| WADAT_IST | VARCHAR | 实际发货日期 |
| KOSTL | VARCHAR | 过账标识（C=已过账） |

#### LIPS（交货单行项目，增量数据）

| 字段 | 类型 | 业务含义 |
|------|------|---------|
| VBELN | VARCHAR(10) | 交货单号，外键→LIKP |
| POSNR | VARCHAR(6) | 行项目号 |
| MATNR | VARCHAR | 物料编码 |
| LFIMG | DECIMAL | 交货数量 |
| VRKME | VARCHAR | 计量单位 |
| WERKS | VARCHAR | 工厂 |
| LGORT | VARCHAR | 库存地点 |

### 9.2 PI-System

| 字段 | 类型 | 业务含义 |
|------|------|---------|
| tag | VARCHAR | 标签名，格式 `{矿井}_{工作面}_{传感器}`（如 `MINE_001_FACE_A1_WAGAS`） |
| timestamp | VARCHAR | 数据时间戳（ISO格式） |
| value | FLOAT | 传感器读数 |
| status | INT | 状态（0=正常, -1=缺失, -2=坏点/超限） |
| mine | VARCHAR | 矿井编码（如 `MINE_001`） |
| face | VARCHAR | 工作面标识（如 `FACE_A1`） |
| sensor | VARCHAR | 传感器类型（增量数据有） |
| unit | VARCHAR | 单位（增量数据有：%, ℃, ppm, kPa, rpm） |

**传感器类型与值域：**

| 传感器 | 业务含义 | 正常基线 | 单位 |
|--------|---------|---------|------|
| WAGAS | 瓦斯浓度 | 0.35% | % |
| TEMP | 环境温度 | 22℃ | ℃ |
| CO | 一氧化碳浓度 | 5ppm | ppm |
| CO2 | 二氧化碳浓度 | 400ppm | ppm |
| PRESS | 气压（增量有） | 101.325 | kPa |
| FAN_SPEED | 风机转速（增量有） | 1450 | rpm |

### 9.3 LIMS

| 字段 | 类型 | 业务含义 |
|------|------|---------|
| SAMPLE_ID | VARCHAR | 样品编号，格式 `LMXXXXXX`（6位数字） |
| MINE_CODE | VARCHAR | 矿井编码（M001-M005） |
| MINE_NAME | VARCHAR | 矿井名称 |
| SAMPLE_TYPE | VARCHAR | 煤种（原煤/精煤/中煤/矸石/洗煤） |
| SAMPLING_DATE | VARCHAR | 采样日期 |
| SAMPLING_POINT | VARCHAR | 采样位置（矿井内具体地点） |
| SAMPLING_PERSON | VARCHAR | 采样人 |
| TEST_DATE | VARCHAR | 化验日期 |
| TEST_LAB | VARCHAR | 化验室（一分室/二分室/三分室/中心化验室） |
| REPORTER | VARCHAR | 报告人 |
| REPORT_STATUS | VARCHAR | 报告状态（已审核/待审核/已发布） |
| AD | FLOAT | **灰分**（Air Dry basis，%） |
| VD | FLOAT | **挥发分**（%） |
| FC | FLOAT | **固定碳**（%，计算得出） |
| QGR_AD | FLOAT | **收到基低位发热量**（MJ/kg） |
| 全水分Mt | FLOAT | 全水分（%） |
| 全硫St | FLOAT | 全硫分（%） |
| Mar | FLOAT | 水分（收到基，%） |
| 全磷P | FLOAT | 磷含量（微量元素，%） |
| 全砷As | FLOAT | 砷含量（微量元素，ppm） |
| 粒度 | VARCHAR | 粒度分级（<50mm/50-100mm/>100mm/混煤） |

### 9.4 OA

#### DOC_FLOW（审批流程记录）

| 字段 | 类型 | 业务含义 |
|------|------|---------|
| FLOW_ID | VARCHAR | 流程编号，格式 `FLXXXXXXXX` |
| DOC_NO | VARCHAR | 文档编号，格式 `DOC{年份}{序号}` |
| FLOW_TYPE | VARCHAR | 流程类型（请假/报销/采购申请/付款申请/用车申请/出差/公文审批/印章使用） |
| INITIATOR | VARCHAR | 发起人 |
| INITIATOR_DEPT | VARCHAR | 发起人部门 |
| APPLY_DATE | VARCHAR | 申请日期 |
| CURRENT_NODE | VARCHAR | 当前审批节点 |
| STATUS | VARCHAR | 流程状态（已完成/审批中/已驳回/已撤销） |
| APPROVER | VARCHAR | 审批人 |
| APPROVE_DATE | VARCHAR | 审批日期 |
| AMOUNT | FLOAT | 流程金额（仅付款/采购类流程有值，约40%） |
| REMARK | VARCHAR | 备注 |

#### CONTRACT（合同台账，增量数据）

| 字段 | 类型 | 业务含义 |
|------|------|---------|
| CONTRACT_ID | VARCHAR | 合同编号，格式 `CT{年份}{5位序号}` |
| CONTRACT_NAME | VARCHAR | 合同名称 |
| CONTRACT_TYPE | VARCHAR | 合同类型（采购合同/销售合同/服务合同/租赁合同/施工合同/运输合同） |
| COUNTERPARTY | VARCHAR | 对方单位 |
| SIGN_DATE | VARCHAR | 签约日期 |
| EFFECTIVE_DATE | VARCHAR | 生效日期 |
| EXPIRY_DATE | VARCHAR | 到期日期 |
| AMOUNT | FLOAT | 合同金额（CNY） |
| CURRENCY | VARCHAR | 币种 |
| PAYMENT_TERM | VARCHAR | 付款条件（预付30%/月结30天/月结60天/到货付款） |
| STATUS | VARCHAR | 合同状态（执行中/已终止/已到期） |
| CONTRACT_MANAGER | VARCHAR | 合同管理员 |
| DEPT | VARCHAR | 负责部门 |

#### MEETING（会议纪要，增量数据）

| 字段 | 类型 | 业务含义 |
|------|------|---------|
| MEETING_ID | VARCHAR | 会议编号，格式 `MT{年份}{序号}` |
| MEETING_DATE | VARCHAR | 会议日期 |
| MEETING_TYPE | VARCHAR | 会议类型（安全生产例会/生产调度会/技术研讨会/班前会/专题会） |
| VENUE | VARCHAR | 会议地点 |
| CHAIRMAN | VARCHAR | 主持人 |
| RECORDER | VARCHAR | 记录人 |
| ATTENDEES | VARCHAR | 参会人（逗号分隔多人姓名） |
| SUMMARY | VARCHAR | 会议摘要 |
| DECISIONS | VARCHAR | 决议事项 |
| FOLLOW_UP | VARCHAR | 跟进事项（责任部门+完成时间） |

### 9.5 SCADA

| 字段 | 类型 | 业务含义 |
|------|------|---------|
| timestamp | VARCHAR | 采集时间（ISO格式） |
| point | VARCHAR | 点位名称（如 `BELT_001_SPEED`） |
| value | FLOAT/INT | 实时值 |
| unit | VARCHAR | 单位 |
| status | INT | 状态（0=正常, 1=预警, 2=报警） |

---

## 10. OpenSpec 变更规格索引

本项目使用 OpenSpec 变更驱动开发，主要规格如下：

| 模块 | 规格目录 | 核心内容 |
|------|---------|---------|
| 模块一 | `step1-onboarding/` | 痛点故事、DataHub 接入、质量告警业务影响量化 |
| 模块二 | `module2-quality-detection/` | Great Expectations 扫描、多维质量评分 |
| 模块三 | `module3-lineage-notebook/` | 从 PI 到 SAP 到 OA 全链路血缘追溯 |
| 自动化血缘 | `auto-lineage-collection/` | Delta Lake 自动发现、血缘上报 |
| 血缘上报 | `datahub-actions-kafka-sync/` | DataHub Actions Kafka 同步 |
| 维度建模 | `dim-customer/`, `dim-material/`, `dim-mine/` | 客户/物料/矿井维度表 |
| DWA 模型 | `dwa-sales-daily/`, `dwa-coal-quality/`, `dwa-tag-alarm/` | 销售日报/煤质分析/标签告警汇总 |
| 根因分析 | `quality-root-cause-analysis/` | 质量问题溯源分析 |

---

## 11. 常见问题

**Q: 历史数据生成太慢怎么办？**

A: 当前 v3 版本全向量化，100 标签 1 分钟间隔约 7862 万条记录在约 2 分钟内生成完毕。如需更快速，可修改 `SCALE` 字典中的 `pi_interval_min`（调大间隔）或 `pi_years`（减少年数）。

**Q: 如何重新生成特定系统的数据？**

A: 直接修改 `scripts/generate_historical.py` 中对应的 `run_xxx()` 函数后重新运行。历史数据每次重新生成会完整覆盖。

**Q: 增量数据如何接入真实数仓？**

A: 增量数据输出到 `data/incremental/{date}/` 后，可配置 Flume/Kafka Connect 监听该目录，或编写脚本将 Parquet 转为 CSV/JSON 后通过 API 推送至数据湖。

**Q: 如何修改矿井名称或编码？**

A: 编辑 `src/dg_simulator/pi_incremental.py` 中的 `TAG_HIERARCHY` 和 `src/dg_simulator/lims_incremental.py` 中的 `MINE_CODES` / `MINE_NAMES`，重新运行增量生成器即可。

**Q: DataHub 上报失败怎么办？**

A: 检查 DataHub GMS 是否启动：`curl http://localhost:8080/api/graphql -d '{"query":"{ __typename }"}'`。若返回 `{"data":{"__typename":"Query"}}` 表示正常。若数据库未初始化，需先执行 DataHub 初始化脚本。

**Q: SCADA 和 PI-System 的区别是什么？**

A: PI-System 是**时序数据库**，存储传感器历史采样值（瓦斯/温度/CO 等），用于历史分析和趋势预测。SCADA 是**实时设备监控系统**，模拟皮带机/水泵/风机等设备的状态机数据，强调实时报警，**不经过 PI**，直接推送。每秒一次推送，包含设备运行状态、告警级别等。
