"""
6.12 跨系统 DWA — dwa_sales_production（4 表 JOIN 跨主题宽表）

技术选型：DuckDB 替代 ClickHouse/Doris（已在 pyproject.toml；0 setup，4 表 JOIN < 1s）
上游路径：6.11 主题域 DWD（dwd/sales/、dwd/production/、dwd/coal_quality/）
桥接键  ：mine_code（vbak.MINE_CODE ↔ tags.mine ↔ samples.MINE_CODE） + KUNNR（vbak↔kna1）
物化视图模拟：CREATE TABLE dwa_sales_production AS SELECT ... 写 Delta Lake（persistent）
血缘    ：6.9 LineageEmitter 包装（自动 emit START/COMPLETE → GMS dataJobInputOutput）

用法：
    uv run python scripts/build_dwa_sales_production.py
    uv run python scripts/build_dwa_sales_production.py --sample 0.01  # 1% 采样（演示推荐）
    uv run python scripts/build_dwa_sales_production.py --no-lineage   # 跳过 lineage emit
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import duckdb
import pandas as pd
from deltalake.writer import write_deltalake

# 把 src/ 加进 import path，便于 `from dg_platform.lineage_emitter import ...`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dg_platform.lineage_emitter import LineageEmitter  # noqa: E402

# 路径配置
LAKEHOUSE_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "lakehouse",
)
DWD_SALES_VBAK = f"{LAKEHOUSE_ROOT}/dwd/sales/dwd_vbak/*.parquet"
DWD_SALES_KNA1 = f"{LAKEHOUSE_ROOT}/dwd/sales/dwd_kna1/*.parquet"
DWD_PRODUCTION_TAGS = f"{LAKEHOUSE_ROOT}/dwd/production/dwd_tags/*.parquet"
DWD_COAL_QUALITY_SAMPLES = f"{LAKEHOUSE_ROOT}/dwd/coal_quality/dwd_samples/*.parquet"
DWA_OUTPUT = "dwa/dwa_sales_production"  # 落 Delta Lake 的相对路径

# 演示推荐默认采样（避免 9M vbak × 13M tags 笛卡尔积爆内存）
DEFAULT_SAMPLE_RATIO = 0.01


# ============================================================
# SQL 模板：4 个分析场景（教学用，学员可粘贴到 DuckDB CLI 即用）
# ============================================================
SQL_PRODUCTION_SALES = """
-- 场景 1：产销对比 — 各矿井日均产量 vs 日均销售单数
SELECT
    mine_code,
    COUNT(DISTINCT VBELN)                       AS order_count,
    ROUND(AVG(daily_production), 2)             AS avg_production,
    ROUND(AVG(NETWR), 2)                        AS avg_order_amount
FROM dwa_sales_production
WHERE mine_code IS NOT NULL
GROUP BY mine_code
ORDER BY avg_production DESC
"""

SQL_COAL_PRICING = """
-- 场景 2：煤质定价 — 各矿井煤质（灰分/发热量）vs 订单均价
SELECT
    mine_code,
    ROUND(AVG(ash_content), 2)                  AS avg_ash,
    ROUND(AVG(calorific), 2)                    AS avg_calorific,
    ROUND(AVG(NETWR), 2)                        AS avg_price,
    ROUND(AVG(calorific) / NULLIF(AVG(ash_content), 0), 4) AS price_per_calorific
FROM dwa_sales_production
WHERE mine_code IS NOT NULL AND ash_content IS NOT NULL
GROUP BY mine_code
ORDER BY avg_calorific DESC
"""

SQL_SAFETY_TREND = """
-- 场景 3：安全趋势 — 各矿井日均生产（PI tags avg_value）波动
SELECT
    mine_code,
    face,
    ROUND(AVG(daily_production), 2)             AS mean_value,
    ROUND(STDDEV(daily_production), 2)           AS stddev_value,
    COUNT(*)                                    AS sample_size
FROM dwa_sales_production
WHERE face IS NOT NULL
GROUP BY mine_code, face
ORDER BY stddev_value DESC
"""

SQL_ORDER_FULFILLMENT = """
-- 场景 4：订单履约 — 各客户每日订单数 + 平均金额
SELECT
    customer_name,
    COUNT(DISTINCT VBELN)                       AS order_count,
    ROUND(SUM(NETWR), 2)                        AS total_amount,
    ROUND(AVG(NETWR), 2)                        AS avg_order_amount,
    COUNT(DISTINCT SUBSTR(ERDAT, 1, 10))        AS active_days
FROM dwa_sales_production
WHERE customer_name IS NOT NULL
GROUP BY customer_name
ORDER BY total_amount DESC
LIMIT 20
"""

# 4 表 JOIN 核心 SQL（被 LineageEmitter 解析以推导 inputs）
SQL_4TABLE_JOIN = """
CREATE OR REPLACE TABLE dwa_sales_production AS
SELECT
    v.VBELN, v.ERDAT, v.KUNNR, k.NAME1 AS customer_name,
    v.mine_code, t.face,
    ROUND(t.avg_value, 4)                       AS daily_production,
    ROUND(s.AD, 4)                              AS ash_content,
    ROUND(s.QGR_AD, 4)                          AS calorific,
    ROUND(v.NETWR, 2)                           AS NETWR
FROM dwd_sales_dwd_vbak v
LEFT JOIN dwd_sales_dwd_kna1 k   ON v.KUNNR    = k.KUNNR
LEFT JOIN dwd_production_dwd_tags_agg t ON v.mine_code = t.mine
LEFT JOIN dwd_coal_quality_dwd_samples_agg s ON v.mine_code = s.MINE_CODE
"""


def _build_views_sql(sample_ratio: float) -> str:
    """拼装 4 个 CREATE VIEW 语句串。

    设计差异点（vs design.md 原始模板）：
    1. vbak 视图派生 mine_code：`'M' || SUBSTR(BZIRK, 2, 3)`（D001→M001）。
       因为 vbak 实际数据无 MINE_CODE 列，仅有 BZIRK（销售区），需派生以桥接 PI/LIMS。
       业务解读：销售区与矿井 1:1 映射（district-to-mine mapping）。
    2. tags 与 samples 先 GROUP BY mine 聚合到 (mine) / (mine_code) 粒度，
       避免 9M vbak × 13M tags 的笛卡尔积爆炸（设计文档未明确这步）。
    3. 默认采样 vbak 1%（DEFAULT_SAMPLE_RATIO），控制内存。
    """
    sample_clause = ""
    if sample_ratio < 1.0:
        sample_clause = f" USING SAMPLE {sample_ratio * 100:.2f}%"

    return f"""
CREATE OR REPLACE VIEW dwd_sales_dwd_vbak AS
    SELECT *, 'M' || SUBSTR(BZIRK, 2, 3) AS mine_code
    FROM read_parquet('{DWD_SALES_VBAK}'){sample_clause};

CREATE OR REPLACE VIEW dwd_sales_dwd_kna1 AS
    SELECT KUNNR, NAME1
    FROM read_parquet('{DWD_SALES_KNA1}');

CREATE OR REPLACE VIEW dwd_production_dwd_tags_agg AS
    SELECT mine, face, AVG(value) AS avg_value, COUNT(*) AS sample_count
    FROM read_parquet('{DWD_PRODUCTION_TAGS}')
    GROUP BY mine, face;

CREATE OR REPLACE VIEW dwd_coal_quality_dwd_samples_agg AS
    SELECT MINE_CODE, AVG(AD) AS AD, AVG(QGR_AD) AS QGR_AD, COUNT(*) AS sample_count
    FROM read_parquet('{DWD_COAL_QUALITY_SAMPLES}')
    GROUP BY MINE_CODE;
"""


def build_dwa_sales_production(
    sample_ratio: float = DEFAULT_SAMPLE_RATIO,
    emit_lineage: bool = True,
) -> pd.DataFrame:
    """构建跨系统 4 表 JOIN 宽表 dwa_sales_production，落 Delta Lake + emit lineage。

    Returns:
        写入 Delta Lake 的最终 DataFrame
    """
    t0 = time.time()
    conn = duckdb.connect()
    conn.execute("SET enable_progress_bar=false")

    # 6.9 LineageEmitter：用 SQL_4TABLE_JOIN 推导 inputs（4 个 dwd_*.{view}）
    lineage_ctx: LineageEmitter | None = None
    if emit_lineage:
        lineage_ctx = LineageEmitter(
            job_name="build_dwa_sales_production",
            sql=SQL_4TABLE_JOIN,
        )
        lineage_ctx.__enter__()

    print(f"\n{'='*60}")
    print(f"📊 6.12 跨系统 DWA — dwa_sales_production（4 表 JOIN）")
    print(f"{'='*60}")
    print(f"   采样比: {sample_ratio * 100:.2f}%（vbak 侧）")
    print(f"   上游: sales.dwd_vbak / dwd_kna1 + production.dwd_tags + coal_quality.dwd_samples")
    print(f"   桥接键: mine_code (sales↔production↔coal_quality) + KUNNR (sales↔kna1)")

    # Step 1: 4 个 CREATE VIEW
    print("\n▶ Step 1: 4 个 CREATE VIEW（读 subject-分区 Parquet）")
    t_view = time.time()
    conn.execute(_build_views_sql(sample_ratio))
    print(f"   ✅ 4 views created in {time.time() - t_view:.2f}s")

    # Step 2: CREATE TABLE AS 4-table JOIN
    print("\n▶ Step 2: CREATE TABLE dwa_sales_production AS SELECT ... 4-table JOIN")
    t_join = time.time()
    conn.execute(SQL_4TABLE_JOIN)
    df = conn.execute("SELECT * FROM dwa_sales_production").df()
    print(f"   ✅ 4-table JOIN done in {time.time() - t_join:.2f}s, rows: {len(df):,}")

    # Step 3: 写 Delta Lake
    print(f"\n▶ Step 3: write_deltalake → {DWA_OUTPUT}/")
    table_uri = os.path.join(LAKEHOUSE_ROOT, DWA_OUTPUT)
    os.makedirs(table_uri, exist_ok=True)
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("")
        elif df[col].dtype.kind in "fi":
            df[col] = df[col].fillna(0)
    t_write = time.time()
    write_deltalake(
        table_uri, df, mode="overwrite",
        configuration={"delta.enableChangeDataFeed": "false"},
    )
    print(f"   ✅ Delta Lake written in {time.time() - t_write:.2f}s")
    files = [f for f in os.listdir(table_uri) if f.endswith(".parquet")]
    size_mb = sum(os.path.getsize(os.path.join(table_uri, f)) for f in files) / 1024 / 1024
    print(f"   files: {len(files)}, size: {size_mb:.2f} MB")

    # Step 4: re-query Delta Lake（验证读回 < 1s）
    print(f"\n▶ Step 4: DuckDB re-query Delta Lake 验证")
    t_rq = time.time()
    reread = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM delta_scan('{table_uri}')"
    ).df()
    rq_time = time.time() - t_rq
    print(f"   ✅ delta_scan() count: {reread['cnt'].iloc[0]:,} rows in {rq_time:.3f}s "
          f"({'< 1s OK' if rq_time < 1.0 else '> 1s SLOW'})")

    # Step 5: emit lineage
    if lineage_ctx is not None:
        out_urn = (
            f"urn:li:dataset:(urn:li:dataPlatform:{DWA_OUTPUT.split('/')[0]},"
            f"{DWA_OUTPUT.split('/')[-1]},PROD)"
        )
        lineage_ctx.emit_output(out_urn, df)
        lineage_ctx.__exit__(None, None, None)
        print(f"\n▶ Step 5: lineage emitted → {out_urn}")

    elapsed = time.time() - t0
    print(f"\n✅ dwa_sales_production 构建完成，耗时 {elapsed:.2f}s")
    print(f"   schema: {list(df.columns)}")
    print(f"   sample:\n{df.head(3).to_string()}")
    return df


def run_scenario(scenario_name: str, sql: str) -> pd.DataFrame:
    """跑一个分析场景 SQL 并打印结果（教学演示用）"""
    conn = duckdb.connect()
    conn.execute("SET enable_progress_bar=false")
    table_uri = os.path.join(LAKEHOUSE_ROOT, DWA_OUTPUT)
    conn.execute(
        f"CREATE OR REPLACE VIEW dwa_sales_production "
        f"AS SELECT * FROM delta_scan('{table_uri}')"
    )
    print(f"\n=== {scenario_name} ===")
    df = conn.execute(sql).df()
    print(df.to_string(index=False))
    print(f"rows: {len(df)}")
    return df


def main():
    parser = argparse.ArgumentParser(description="6.12 跨系统 DWA — dwa_sales_production")
    parser.add_argument("--sample", type=float, default=DEFAULT_SAMPLE_RATIO,
                        help=f"vbak 采样比（0, 1]，默认 {DEFAULT_SAMPLE_RATIO}")
    parser.add_argument("--no-lineage", action="store_true",
                        help="跳过 lineage emit（GMS 未启时用）")
    parser.add_argument("--scenario", choices=[
        "production_sales", "coal_pricing", "safety_trend", "order_fulfillment",
    ], help="跑一个分析场景 SQL（不写 Delta Lake）")
    args = parser.parse_args()

    if args.scenario:
        scenarios = {
            "production_sales": ("场景 1：产销对比", SQL_PRODUCTION_SALES),
            "coal_pricing":     ("场景 2：煤质定价", SQL_COAL_PRICING),
            "safety_trend":     ("场景 3：安全趋势", SQL_SAFETY_TREND),
            "order_fulfillment":("场景 4：订单履约", SQL_ORDER_FULFILLMENT),
        }
        name, sql = scenarios[args.scenario]
        run_scenario(name, sql)
        return

    if not 0 < args.sample <= 1.0:
        parser.error(f"--sample must be in (0, 1], got {args.sample}")

    build_dwa_sales_production(
        sample_ratio=args.sample,
        emit_lineage=not args.no_lineage,
    )


if __name__ == "__main__":
    main()
