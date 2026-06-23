"""
DWA 层汇总宽表 — 用 DuckDB 对 Delta Lake / Parquet 数据做 OLAP 聚合，
结果写回 Delta Lake。

用法：
    uv run python scripts/build_dwa_models.py [--layer dwa|dwd|all]
"""
import argparse
import os
import time

import duckdb
import pandas as pd
from deltalake.writer import write_deltalake
from deltalake import DeltaTable

# 路径配置
LAKEHOUSE_ROOT = "/home/szs/Playground/dg-demo/data/lakehouse"
DATA_ROOT = "/home/szs/Playground/dg-demo/data/historical"

# DWA 聚合 LIMIT 常量（教学用）
DWA_SALES_LIMIT = 30   # 日销售汇总最大天数


def get_duckdb():
    """获取 DuckDB 连接（读写 Parquet + Delta Lake）"""
    conn = duckdb.connect()
    # 注册 Delta Lake 表
    for subdir, dirs, files in os.walk(LAKEHOUSE_ROOT):
        for d in dirs:
            if d in ("ods", "dwd"):
                table_path = os.path.join(subdir, d)
                rel_path = os.path.relpath(table_path, LAKEHOUSE_ROOT)
                # DuckDB 支持直接读取 Delta Lake
                try:
                    conn.execute(f"""
                        CREATE VIEW IF NOT EXISTS delta_{rel_path.replace('/', '_')}
                        AS SELECT * FROM delta_scan('{table_path}')
                    """)
                except Exception:
                    pass
    return conn


def write_delta(table_key: str, df: pd.DataFrame):
    """写 Delta Lake 表"""
    table_uri = os.path.join(LAKEHOUSE_ROOT, table_key)
    os.makedirs(table_uri, exist_ok=True)
    df = df.where(pd.notnull(df), None)
    write_deltalake(
        table_uri, df, mode="overwrite",
        configuration={"delta.enableChangeDataFeed": "false"}
    )


# ============================================================
# DWA 模型1：每日销售汇总
# ============================================================
def build_dwa_sales_daily(conn) -> pd.DataFrame:
    """每日销售汇总宽表（来自清洗后 DWD vbak）"""
    print("\n▶ dwa_sales_daily（每日销售汇总）")

    # 注册 ODS Parquet 文件为虚拟表
    conn.execute("""
        CREATE VIEW IF NOT EXISTS vbak_parquet AS
        SELECT *, '2022' AS year
        FROM read_parquet('{DATA}/sap_erp/vbak_year=2022.parquet')
    """.format(DATA=DATA_ROOT))

    result = conn.execute("""
        SELECT
            STRFTIME(CAST(ERDAT AS DATE), '%Y-%m-%d') AS sale_date,
            COUNT(*)                        AS order_count,
            COUNT(DISTINCT KUNNR)          AS customer_count,
            ROUND(SUM(NETWR), 2)           AS total_amount,
            ROUND(AVG(NETWR), 2)           AS avg_order_amount,
            COUNT(DISTINCT AUART)           AS order_type_count,
            COUNT(DISTINCT VKORG)          AS sales_org_count
        FROM vbak_parquet
        WHERE ERDAT IS NOT NULL AND ERDAT != '00000000'
        GROUP BY STRFTIME(CAST(ERDAT AS DATE), '%Y-%m-%d')
        ORDER BY sale_date
        LIMIT {DWA_SALES_LIMIT}
    """.format(DATA=DATA_ROOT, DWA_SALES_LIMIT=DWA_SALES_LIMIT)).df()

    print(f"  汇总天数: {len(result)} 天")
    print(f"  示例: {result.head(3).to_string()}")
    return result


# ============================================================
# DWA 模型2：传感器告警汇总
# ============================================================
def build_dwa_tag_alarm(conn) -> pd.DataFrame:
    """PI 传感器告警汇总宽表"""
    print("\n▶ dwa_tag_alarm（传感器告警汇总）")

    conn.execute(f"""
        CREATE VIEW IF NOT EXISTS pi_tags AS
        SELECT *
        FROM read_parquet('{DATA_ROOT}/pi_system/tags_year=2022_month=01.parquet')
        LIMIT 500000
    """)

    result = conn.execute("""
        SELECT
            mine,
            face,
            tag,
            COUNT(*)                           AS total_records,
            SUM(CASE WHEN status = -1 THEN 1 ELSE 0 END)    AS missing_count,
            SUM(CASE WHEN value > 8000 THEN 1 ELSE 0 END)   AS high_value_count,
            ROUND(AVG(value), 4)                           AS avg_value,
            ROUND(STDDEV(value), 4)                        AS stddev_value,
            ROUND(MIN(value), 4)                           AS min_value,
            ROUND(MAX(value), 4)                           AS max_value
        FROM pi_tags
        GROUP BY mine, face, tag
        ORDER BY high_value_count DESC
        LIMIT 20
    """).df()

    print(f"  告警传感器数: {len(result)}")
    print(f"  TOP 告警: {result.head(5)[['mine','tag','high_value_count','missing_count']].to_string()}")
    return result


# ============================================================
# DWA 模型3：煤质月汇总
# ============================================================
def build_dwa_coal_quality(conn) -> pd.DataFrame:
    """LIMS 煤质月汇总宽表"""
    print("\n▶ dwa_coal_quality（煤质月汇总）")

    conn.execute(f"""
        CREATE VIEW IF NOT EXISTS lims_samples AS
        SELECT *
        FROM read_parquet('{DATA_ROOT}/lims/samples_year=2022.parquet')
        LIMIT 200000
    """)

    result = conn.execute("""
        SELECT
            MINE_CODE,
            MINE_NAME,
            SUBSTR(SAMPLING_DATE, 1, 7)                    AS month,
            SAMPLE_TYPE,
            COUNT(*)                                        AS sample_count,
            ROUND(AVG(AD), 2)                             AS avg_ash_content,      -- 灰分
            ROUND(AVG(VD), 2)                             AS avg_volatile_content,  -- 挥发分
            ROUND(AVG(全硫St), 2)                         AS avg_sulfur_content,   -- 全硫
            ROUND(AVG(QGR_AD), 2)                          AS avg_gross_calorific,  -- 发热量
            ROUND(MIN(AD), 2)                              AS min_ash_content,
            ROUND(MAX(AD), 2)                             AS max_ash_content,
            COUNT(DISTINCT TEST_LAB)                       AS lab_count
        FROM lims_samples
        WHERE SAMPLING_DATE IS NOT NULL
          AND MINE_CODE IS NOT NULL
        GROUP BY MINE_CODE, MINE_NAME, SAMPLE_TYPE,
                 SUBSTR(SAMPLING_DATE, 1, 7)
        ORDER BY month, MINE_CODE
        LIMIT 50
    """).df()

    print(f"  汇总记录数: {len(result)}")
    print(f"  示例: {result.head(5).to_string()}")
    return result


# ============================================================
# DWD 扩展：增加衍生字段
# ============================================================
def build_dwd_with_derived(conn) -> dict:
    """DWD 层增加衍生字段（业务附加）"""
    print("\n▶ DWD 扩展：增加衍生字段")

    # DWD vbak 扩展
    conn.execute(f"""
        CREATE VIEW IF NOT EXISTS dwd_vbak_ext AS
        SELECT
            v.*,
            CASE
                WHEN NETWR > 100000 THEN '大额订单'
                WHEN NETWR > 10000  THEN '中额订单'
                ELSE '小额订单'
            END AS order_size_category,
            SUBSTR(ERDAT, 1, 4) || '-' || SUBSTR(ERDAT, 5, 2) || '-' || SUBSTR(ERDAT, 7, 2) AS sale_date_formatted,
            KUNNR || '_' || VKORG AS customer_salesorg_key
        FROM (
            SELECT *, '2022' AS year
            FROM read_parquet('{DATA_ROOT}/sap_erp/vbak_year=2022.parquet')
            WHERE ERDAT IS NOT NULL
        ) v
    """)

    ext = conn.execute("SELECT COUNT(*) AS cnt FROM dwd_vbak_ext").df()
    print(f"  VBAK 扩展记录数: {ext['cnt'].iloc[0]}")

    # DWD lims 扩展
    conn.execute(f"""
        CREATE VIEW IF NOT EXISTS dwd_lims_ext AS
        SELECT
            s.*,
            CASE
                WHEN AD > 40 THEN '高灰煤'
                WHEN AD > 20 THEN '中灰煤'
                ELSE '低灰煤'
            END AS ash_grade,
            ROUND(全硫St * 100 / NULLIF(AD, 0), 2) AS sulfur_ash_ratio
        FROM (
            SELECT *, '2022' AS year
            FROM read_parquet('{DATA_ROOT}/lims/samples_year=2022.parquet')
        ) s
        WHERE AD IS NOT NULL
    """)

    ext_lims = conn.execute("SELECT COUNT(*) AS cnt FROM dwd_lims_ext").df()
    print(f"  LIMS 扩展记录数: {ext_lims['cnt'].iloc[0]}")

    return {"dwd_vbak_ext": "dwd_ext/dwd_vbak_ext",
             "dwd_lims_ext": "dwd_ext/dwd_lims_ext"}


# ============================================================
# 主函数
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="DWA 层汇总建模")
    parser.add_argument("--layer", default="all",
                        choices=["dwa", "dwd", "all"])
    args = parser.parse_args()

    t0 = time.time()
    conn = get_duckdb()

    print(f"\n{'='*60}")
    print(f"📊 DWA 层汇总建模（DuckDB OLAP）")
    print(f"{'='*60}\n")

    if args.layer in ("dwd", "all"):
        print("=== DWD 扩展层 ===")
        dwd_ext_map = build_dwd_with_derived(conn)
        print("✅ DWD 扩展完成")

    if args.layer in ("dwa", "all"):
        print("\n=== DWA 汇总层 ===")

        # DWA 1：每日销售汇总
        df_sales = build_dwa_sales_daily(conn)
        write_delta("dwa/sap_erp/dwa_sales_daily", df_sales)
        cnt, sz = _delta_stats("dwa/sap_erp/dwa_sales_daily")
        print(f"  ✅ dwa_sales_daily: {cnt} files, {sz:.1f} MB")

        # DWA 2：传感器告警
        df_alarm = build_dwa_tag_alarm(conn)
        write_delta("dwa/pi_system/dwa_tag_alarm", df_alarm)
        cnt, sz = _delta_stats("dwa/pi_system/dwa_tag_alarm")
        print(f"  ✅ dwa_tag_alarm: {cnt} files, {sz:.1f} MB")

        # DWA 3：煤质月汇总
        df_quality = build_dwa_coal_quality(conn)
        write_delta("dwa/lims/dwa_coal_quality", df_quality)
        cnt, sz = _delta_stats("dwa/lims/dwa_coal_quality")
        print(f"  ✅ dwa_coal_quality: {cnt} files, {sz:.1f} MB")

    conn.close()
    elapsed = time.time() - t0
    print(f"\n✅ DWA 建模完成，耗时 {elapsed:.1f}s")


def _delta_stats(table_key: str):
    table_uri = os.path.join(LAKEHOUSE_ROOT, table_key)
    try:
        files = [f for f in os.listdir(table_uri)
                 if f.endswith('.parquet')]
        total_size = sum(os.path.getsize(os.path.join(table_uri, f))
                         for f in files)
        return len(files), total_size / 1024 / 1024
    except Exception:
        return 0, 0


if __name__ == "__main__":
    main()
