# 项目概览 — CLAUDE.md

本项目是 A公司煤炭数据治理 Demo 环境，通过模拟5个异构系统的真实数据，展示数据治理全流程能力。

---

## 必读文档

按此顺序阅读，可完整理解本项目：

```
1. docs/Background.md      ← 业务背景、数据问题、演示目标
   看完 → 你知道"这个项目要解决什么问题"

2. docs/Design.md           ← 技术架构、选型理由、分层设计
   看完 → 你知道"怎么实现"

3. docs/ELTvsETL.md         ← ELT vs ETL 选型分析
   看完 → 你理解"为什么这样设计"

4. docs/Demo.md              ← 演示脚本、数据探查代码示例
   看完 → 你知道"怎么用这个项目做演示"

5. docs/Deps.md              ← 依赖安装、服务部署
   看完 → 你知道"需要装什么"
```

**捷径**：如果你只需要快速了解项目，优先读 `docs/Background.md` 的：
- 名词术语说明节（所有专业术语的通俗解释）
- 第6节 演示目标（6个演示模块一览）

---

## 项目结构

```
dg-demo/
├── docs/                   # 所有设计文档（见上方必读顺序）
├── src/dg_simulator/       # Python 数据生成器源码
│   ├── base_generator.py   # 基类（质量问题注入逻辑）
│   ├── sap_incremental.py  # SAP-ERP 每日增量
│   ├── pi_incremental.py   # PI-System 每日增量
│   ├── lims_incremental.py # LIMS 每日增量
│   └── ...
├── scripts/                # 可执行脚本
│   ├── generate_historical.py  # 生成 ~1GB 历史数据
│   └── generate_incremental.py # 生成每日增量数据
├── data/                   # 生成的模拟数据（不提交到 git）
│   ├── historical/         # Parquet 分区存储（~1GB）
│   └── incremental/        # 每日增量
├── config/                 # YAML 表结构配置
│   └── schemas/            # sap_erp.yaml、pi_system.yaml 等
├── pyproject.toml          # 依赖管理 + 数据生成配置
└── CLAUDE.md              # 本文件
```

---

## 技术栈速查

| 领域 | 技术 |
|------|------|
| 包管理 | **uv**（`uv sync` / `uv run python`） |
| 数据生成 | Python + pandas + numpy + pyarrow |
| 输出格式 | Parquet 分区存储 |
| 数据湖（设计） | Delta Lake |
| 元数据（设计） | DataHub |
| OLAP（设计） | Apache Doris |
| 消息队列（设计） | Apache Kafka |
| 流处理（设计） | Apache Flink |
| 调度（设计） | DolphinScheduler |

---

## 常用命令

```bash
# 安装依赖
uv sync

# 生成历史数据（~1GB，约3分钟）
uv run python scripts/generate_historical.py

# 生成每日增量
uv run python scripts/generate_incremental.py 2024-01-01 2024-01-31

# 快速探查数据
uv run python -c "
import pandas as pd
df = pd.read_parquet('data/historical/sap_erp/vbak_year=2022.parquet')
print(df.shape, df.columns.tolist())
"
```

---

## 关键设计决策（供参考）

1. **数据孤岛模拟**：5个系统独立生成，无主外键关联，矿井编码格式不一致
2. **质量问题注入**：约2%比例注入 null/outlier/duplicate，与真实场景一致
3. **ELT 为主**：ODS之后全部用 SQL/Spark 处理，仅 CDC 入湖前有极轻量 ETL 前置
4. **增量优先**：历史数据一次生成，每日增量支持日期范围灵活生成
5. **文档先行**：所有设计决策先落文档，再写代码

---

## 遇到问题时的思路

- **数据质量问题**：看 `src/dg_simulator/data_quality.py` 的检测逻辑
- **血缘追踪**：看 `src/dg_simulator/lineage_tracker.py`
- **生成器报错**：检查 `scripts/generate_historical.py` 的向量化逻辑是否超时
- **配置疑问**：优先看 `docs/Background.md` 的名词说明节

---

## 注意

- `data/` 目录下的数据文件已加入 `.gitignore`，不提交到仓库
- 模拟数据规模目标约 1GB（实际约 995MB）
- 演示环境推荐内存 16GB+，否则历史数据生成可能 OOM
