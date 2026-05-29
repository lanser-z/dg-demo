#!/usr/bin/env python3
"""
历史数据批量生成器 v3 - 纯向量化 + 列级注入

性能目标: <5分钟生成全部数据
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────────────────
HIST_DIR = Path(__file__).parent.parent / "data" / "historical"
HIST_DIR.mkdir(parents=True, exist_ok=True)

SCALE = dict(
    sap_vbak=6_000_000,
    sap_vbap_ratio=2.0,
    lims_rows=2_000_000,
    pi_tags=100,         # 5矿×5面×4传感器
    pi_interval_min=1,    # 1分钟间隔
    pi_years=2,
    oa_rows=5_000_000,
)

QUALITY = dict(
    null_frac=0.005,    # 0.5% 单元格 null
    outlier_frac=0.005, # 0.5% 单元格 outlier
    dup_frac=0.005,     # 0.5% 重复行
    pi_missing=0.005,   # 0.5% PI 点缺失
)


# ─────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────

def dt_range(start: str, end: str, n: int, rng: np.random.Generator) -> np.ndarray:
    s = np.datetime64(start, "s")
    e = np.datetime64(end, "s")
    total_secs = int((e - s).astype("timedelta64[s]").astype(np.int64))
    offsets = (rng.random(n) * total_secs).astype(np.int64)
    return s + offsets.astype("timedelta64[s]")


def vectorized_nulls(df: pd.DataFrame, frac: float, rng: np.random.Generator) -> pd.DataFrame:
    """列级 null 注入: 随机选若干列，整列置为 NaN/None"""
    if df.empty or frac <= 0:
        return df
    df = df.copy()
    num_cols = [c for c in df.select_dtypes(include=[np.number]).columns]
    obj_cols = [c for c in df.select_dtypes(include=["object"]).columns]
    all_candidate = num_cols + obj_cols
    if not all_candidate:
        return df

    n_cols_to_corrupt = max(1, int(len(all_candidate) * frac * 10))
    cols = rng.choice(all_candidate, size=min(n_cols_to_corrupt, len(all_candidate)), replace=False)
    for col in cols:
        mask = rng.random(len(df)) < frac * 5  # 控制每列污染比例
        if col in num_cols:
            df.loc[mask, col] = np.nan
        else:
            df.loc[mask, col] = None
    return df


def vectorized_outliers(df: pd.DataFrame, frac: float, rng: np.random.Generator) -> pd.DataFrame:
    """列级 outlier 注入: 随机选数值列，置为极值"""
    if df.empty or frac <= 0:
        return df
    df = df.copy()
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        return df

    n_cols = max(1, int(len(num_cols) * frac * 10))
    cols = rng.choice(num_cols, size=min(n_cols, len(num_cols)), replace=False)
    for col in cols:
        mask = rng.random(len(df)) < frac * 5
        # 用列最大值 * 5~15 作为 outlier，避免溢出
        max_val = df[col].max()
        outlier_val = max_val * (5 + rng.random(mask.sum()) * 10)
        df.loc[mask, col] = outlier_val
    return df


def vectorized_duplicates(df: pd.DataFrame, frac: float, rng: np.random.Generator) -> pd.DataFrame:
    """行级重复注入"""
    if df.empty or frac <= 0:
        return df
    dup_n = max(1, int(len(df) * frac))
    indices = rng.integers(0, len(df), size=dup_n)
    dups = df.iloc[indices].copy()
    return pd.concat([df, dups], ignore_index=True)


def inject(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """注入质量问题（三步合并）"""
    df = vectorized_nulls(df, QUALITY["null_frac"], rng)
    df = vectorized_outliers(df, QUALITY["outlier_frac"], rng)
    df = vectorized_duplicates(df, QUALITY["dup_frac"], rng)
    return df


# ─────────────────────────────────────────────────────────────
# SAP-ERP
# ─────────────────────────────────────────────────────────────

def run_sap(rng: np.random.Generator):
    print("\n[1/4] SAP-ERP")

    # KNA1
    print("  KNA1...")
    companies = [
        "内蒙古伊泰煤炭股份有限公司", "山西焦化能源集团", "陕西煤业化工集团",
        "中煤能源集团有限公司", "山东能源集团有限公司", "河南能源化工集团",
        "开滦能源化工股份有限公司", "冀中能源集团", "大同煤矿集团",
        "神华集团有限责任公司", "华能煤炭销售公司", "国电煤炭分公司",
    ]
    cities = ["呼和浩特", "太原", "西安", "北京", "济南", "郑州", "唐山", "邢台", "大同", "鄂尔多斯"]
    n_kna1 = 15000
    kna1 = pd.DataFrame({
        "KUNNR": [f"{i:06d}" for i in range(100001, 100001 + n_kna1)],
        "NAME1": rng.choice(companies, n_kna1),
        "NAME2": [f"分公司{i % 50}" for i in range(n_kna1)],
        "ORT01": rng.choice(cities, n_kna1),
        "STCD1": [f"9{rng.integers(110000, 159999):06d}"
                   f"{rng.integers(1000, 9999):04d}"
                   f"{rng.integers(100, 999):03d}" for _ in range(n_kna1)],
        "ERDAT": dt_range("2021-01-01", "2023-06-01", n_kna1, rng).astype(str),
    })
    kna1.to_parquet(HIST_DIR / "sap_erp" / "kna1.parquet", index=False)
    print(f"  ✓ KNA1 {n_kna1:,} 行")

    # VBAK
    print(f"  VBAK {SCALE['sap_vbak']:,} 行...")
    n_vbak = SCALE["sap_vbak"]

    vbak_dates = dt_range("2022-01-01", "2024-01-01", n_vbak, rng)
    vbak_vbeln = np.arange(1_000_000_001, 1_000_000_001 + n_vbak)

    vbak = pd.DataFrame({
        "VBELN": [f"{v:010d}" for v in vbak_vbeln],
        "ERDAT": vbak_dates.astype(str),
        "ERZET": [f"{h:02d}{m:02d}{s:02d}" for h, m, s in zip(
            rng.integers(6, 22, n_vbak),
            rng.integers(0, 60, n_vbak),
            rng.integers(0, 60, n_vbak))],
        "ERNAM": rng.choice(["SAPUSER", "BATCH_JOB", "ZHANGSAN", "LIISI", "WANGWU"], n_vbak),
        "AUART": rng.choice(["OR", "ZOR", "RET"], n_vbak, p=[0.85, 0.13, 0.02]),
        "KUNNR": [f"{rng.integers(100001, 115000):06d}" for _ in range(n_vbak)],
        "NETWR": np.round(rng.uniform(1_000, 500_000, n_vbak), 2),
        "WAERK": "CNY",
        "BZIRK": rng.choice(["D001", "D002", "D003", "D004", "D005"], n_vbak),
        "VKORG": rng.choice(["CN01", "CN02", "CN03"], n_vbak),
        "VTWEG": rng.choice(["10", "20"], n_vbak, p=[0.8, 0.2]),
        "SPART": rng.choice(["00", "01", "02", "03"], n_vbak, p=[0.6, 0.2, 0.1, 0.1]),
        "BSTNK": [f"PO{rng.integers(100000, 999999)}" for _ in range(n_vbak)],
        "FABKL": rng.choice(["CN01", "CN02", "CN03"], n_vbak),
        "LIFSK": rng.choice(["", "", "", "C"], n_vbak, p=[0.6, 0.2, 0.15, 0.05]),
        "FAKSK": rng.choice(["", "", "C"], n_vbak, p=[0.8, 0.15, 0.05]),
    })
    vbak = inject(vbak, rng)

    for year in [2022, 2023]:
        mask = vbak["ERDAT"].str.startswith(str(year))
        vbak[mask].to_parquet(HIST_DIR / "sap_erp" / f"vbak_year={year}.parquet", index=False)
    print(f"  ✓ VBAK {len(vbak):,} 行")

    # VBAP
    print(f"  VBAP {int(n_vbak * SCALE['sap_vbap_ratio']):,} 行...")
    n_vbap = int(n_vbak * SCALE["sap_vbap_ratio"])

    # 向量化: 用随机索引从 vbak VBELN pool 中选择
    vbak_vbeln_values = vbak["VBELN"].values
    vbap_vbeln_idx = rng.integers(0, len(vbak_vbeln_values), n_vbap)

    vbap = pd.DataFrame({
        "VBELN": vbak_vbeln_values[vbap_vbeln_idx],
        "POSNR": [f"{rng.integers(1, 100):06d}" for _ in range(n_vbap)],
        "MATNR": rng.choice([
            "501010001", "501010002", "501010003",
            "501020001", "501020002",
            "501030001", "501040001",
        ], n_vbap, p=[0.30, 0.15, 0.10, 0.15, 0.10, 0.10, 0.10]),
        "KWMENG": np.round(rng.uniform(10, 5000, n_vbap), 3),
        "VRKME": "TO",
        "NETWR": np.round(rng.uniform(500, 100_000, n_vbap), 2),
        "WAERK": "CNY",
        "CHARG": [f"L{rng.integers(1000, 9999)}" for _ in range(n_vbap)],
        "WERKS": rng.choice(["CN01", "CN02", "CN03"], n_vbap),
        "LGORT": rng.choice(["FG01", "FG02", "FG03", "RM01"], n_vbap),
    })

    # 1% 关联失效（质量注入）
    corrupt_mask = rng.random(n_vbap) < 0.01
    vbap.loc[corrupt_mask, "VBELN"] = "0000000000"

    vbap = inject(vbap, rng)

    half = n_vbap // 2
    vbap[:half].to_parquet(HIST_DIR / "sap_erp" / "vbap_year=2022.parquet", index=False)
    vbap[half:].to_parquet(HIST_DIR / "sap_erp" / "vbap_year=2023.parquet", index=False)
    print(f"  ✓ VBAP {len(vbap):,} 行")
    print(f"  SAP总大小: ", end="")
    sz = sum(f.stat().st_size for f in (HIST_DIR / "sap_erp").rglob("*.parquet"))
    print(f"{sz / 1024**2:.1f} MB")


# ─────────────────────────────────────────────────────────────
# PI-System
# ─────────────────────────────────────────────────────────────

def run_pi(rng: np.random.Generator):
    print("\n[2/4] PI-System 时序数据")

    MINES = ["M001", "M002", "M003", "M004", "M005"]
    FACES = ["FACE_A", "FACE_B", "FACE_C", "FACE_D", "FACE_E"]
    SENSORS = ["WAGAS", "TEMP", "CO", "CO2", "PRESS", "FAN_SPEED"]

    # 50标签: 5矿 × 5面 × 2传感器
    tags = []
    for mine in MINES:
        for face in FACES:
            for sensor in SENSORS[:4]:  # 5×5×4=100标签
                tags.append({"tag": f"{mine}_{face}_{sensor}",
                             "mine": mine,
                             "face": f"{mine}_{face}",
                             "sensor": sensor})
    n_tags = len(tags)
    tag_names = [t["tag"] for t in tags]
    tag_mines = [t["mine"] for t in tags]
    tag_faces = [t["face"] for t in tags]
    tag_sensors = [t["sensor"] for t in tags]

    INTERVAL = SCALE["pi_interval_min"]
    ppd = 1440 // INTERVAL

    print(f"  {n_tags} 标签 × {ppd}/天 × {365 * SCALE['pi_years']} 天（{INTERVAL}min间隔）")

    total = 0
    for year in [2022, 2023]:
        for month in range(1, 13):
            if year == 2023 and month > 6:
                break

            days_in_month = (datetime(year, month + 1, 1) if month < 12
                           else datetime(year + 1, 1, 1)) - datetime(year, month, 1)
            days = days_in_month.days
            n = days * ppd * n_tags

            # ── 时间戳：每个传感器相同，先tile再repeat ──
            base = np.datetime64(datetime(year, month, 1), "s")
            day_offsets = np.repeat(np.arange(days), ppd) * 1440
            minute_offsets = np.tile(np.arange(0, 1440, INTERVAL), days)
            ts_offsets = (day_offsets + minute_offsets).astype("int64")  # 分钟偏移
            ts_per_sensor = base + ts_offsets.astype("timedelta64[m]")
            timestamps = np.tile(ts_per_sensor, n_tags)  # 每传感器重复
            timestamps_str = timestamps.astype(str)

            # ── 标签数组 ──
            tag_flat = np.array(tag_names * (days * ppd))
            mine_flat = np.array(tag_mines * (days * ppd))
            face_flat = np.array(tag_faces * (days * ppd))
            sensor_flat = np.array(tag_sensors * (days * ppd))

            # ── 值生成：按传感器类型 ──
            hours = (timestamps.astype("datetime64[h]").astype(np.int64) % 24).astype(np.float64)
            values = np.zeros(n, dtype=np.float64)

            # WAGAS: 0.35基线 + 时间因子 + 噪声
            mask = sensor_flat == "WAGAS"
            values[mask] = (0.35 + (hours[mask] - 6) * 0.002 +
                           rng.normal(0, 0.02, mask.sum()))
            values[mask] = np.maximum(0, values[mask])

            # TEMP: 基线22 + 白天波动
            mask = sensor_flat == "TEMP"
            values[mask] = (22 + np.where((hours[mask] >= 8) & (hours[mask] <= 18), 3, -2) +
                           rng.normal(0, 0.5, mask.sum()))

            # CO: 指数分布
            mask = sensor_flat == "CO"
            values[mask] = np.maximum(0, 5 + rng.exponential(1.5, mask.sum()))

            # CO2
            mask = sensor_flat == "CO2"
            values[mask] = 400 + rng.normal(0, 15, mask.sum())

            # PRESS
            mask = sensor_flat == "PRESS"
            values[mask] = 101.325 + rng.normal(0, 0.3, mask.sum())

            # FAN_SPEED
            mask = sensor_flat == "FAN_SPEED"
            values[mask] = np.maximum(0, 1450 + rng.normal(0, 20, mask.sum()))

            # 1% 异常突升
            anomaly = rng.random(n) < 0.01
            values[anomaly] *= rng.choice([1.5, 2.0, 3.0], anomaly.sum())

            # 0.5% 缺失
            missing = rng.random(n) < QUALITY["pi_missing"]
            values[missing] = np.nan

            df = pd.DataFrame({
                "tag": tag_flat,
                "timestamp": timestamps_str,
                "value": np.round(values, 3),
                "status": np.where(missing, -1, 0),
                "mine": mine_flat,
                "face": face_flat,
            })

            path = HIST_DIR / "pi_system" / f"tags_year={year}_month={month:02d}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(path, index=False)
            total += len(df)

            if month % 2 == 0:
                print(f"    {year}-{month:02d}: {len(df):,} 行")

    print(f"  ✓ PI-System {total:,} 条")
    sz = sum(f.stat().st_size for f in (HIST_DIR / "pi_system").rglob("*.parquet"))
    print(f"  PI大小: {sz / 1024**2:.1f} MB")


# ─────────────────────────────────────────────────────────────
# LIMS
# ─────────────────────────────────────────────────────────────

def run_lims(rng: np.random.Generator):
    print(f"\n[3/4] LIMS 煤质检测")

    n = SCALE["lims_rows"]
    print(f"  {n:,} 行...")

    dates = dt_range("2022-01-01", "2024-01-01", n, rng)
    mines = ["M001", "M002", "M003", "M004", "M005"]
    mine_names = {
        "M001": "鄂尔多斯一号煤矿", "M002": "榆林李家沟煤矿",
        "M003": "朔州安太堡煤矿", "M004": "吕梁庞庞塔煤矿",
        "M005": "晋城寺河煤矿",
    }
    sample_types = ["原煤", "精煤", "中煤", "矸石", "洗煤"]
    reporters = ["张工", "李工", "王工", "刘工", "陈工", "赵工", "孙工"]

    mine_codes = rng.choice(mines, n)
    s_types = rng.choice(sample_types, n)

    ad_ranges_list = [(15, 35), (6, 12), (20, 40), (50, 80), (8, 18)]
    qgr_ranges_list = [(22, 28), (28, 32), (18, 24), (8, 14), (26, 30)]
    st_to_idx = {"原煤": 0, "精煤": 1, "中煤": 2, "矸石": 3, "洗煤": 4}

    # 向量化: 按类型批量生成指标
    ad_raw = np.zeros(n, dtype=np.float64)
    qgr_raw = np.zeros(n, dtype=np.float64)
    for idx, (ad_r, qgr_r) in enumerate(zip(ad_ranges_list, qgr_ranges_list)):
        mask = (s_types == sample_types[idx])
        cnt = mask.sum()
        ad_raw[mask] = rng.uniform(ad_r[0], ad_r[1], cnt)
        qgr_raw[mask] = rng.uniform(qgr_r[0], qgr_r[1], cnt)

    test_date_offsets = rng.integers(1, 8, n).astype("timedelta64[D]")
    test_dates = (dates.astype("datetime64[D]") + test_date_offsets).astype(str)

    df = pd.DataFrame({
        "SAMPLE_ID": [f"LM{rng.integers(100000, 999999):06d}" for _ in range(n)],
        "MINE_CODE": mine_codes,
        "MINE_NAME": [mine_names.get(m, m) for m in mine_codes],
        "SAMPLE_TYPE": s_types,
        "SAMPLING_DATE": dates.astype(str),
        "TEST_DATE": test_dates,
        "TEST_LAB": rng.choice(["中心化验室", "一分室", "二分室"], n),
        "REPORTER": rng.choice(reporters, n),
        "REPORT_STATUS": rng.choice(["已审核", "已审核", "待审核", "已发布"], n, p=[0.5, 0.3, 0.1, 0.1]),
        "AD": np.round(ad_raw, 2),
        "VD": np.round(rng.uniform(15, 40, n), 2),
        "FC": np.round(rng.uniform(30, 60, n), 2),
        "QGR_AD": np.round(qgr_raw, 2),
        "全水分Mt": np.round(rng.uniform(5, 15, n), 2),
        "全硫St": np.round(rng.uniform(0.3, 2.5, n), 2),
        "Mar": np.round(rng.uniform(8, 20, n), 2),
    })

    df = inject(df, rng)

    for year in [2022, 2023]:
        part = df[df["SAMPLING_DATE"].str.startswith(str(year))]
        (HIST_DIR / "lims").mkdir(parents=True, exist_ok=True)
        part.to_parquet(HIST_DIR / "lims" / f"samples_year={year}.parquet", index=False)

    print(f"  ✓ LIMS {len(df):,} 条")
    sz = sum(f.stat().st_size for f in (HIST_DIR / "lims").rglob("*.parquet"))
    print(f"  LIMS大小: {sz / 1024**2:.1f} MB")


# ─────────────────────────────────────────────────────────────
# OA
# ─────────────────────────────────────────────────────────────

def run_oa(rng: np.random.Generator):
    print(f"\n[4/4] OA 系统")

    n = SCALE["oa_rows"]
    print(f"  {n:,} 行...")

    dates = dt_range("2022-01-01", "2024-01-01", n, rng)
    statuses = rng.choice(["已完成", "审批中", "已驳回", "已撤销"], n, p=[0.6, 0.25, 0.10, 0.05])
    current_nodes = np.where(statuses == "已完成", "归档",
                            rng.choice(["部门负责人", "分管领导", "财务复核"], n))

    df = pd.DataFrame({
        "FLOW_ID": [f"FL{500000 + i:08d}" for i in range(n)],
        "DOC_NO": [f"DOC2022{i % 100000:05d}" for i in range(n)],
        "FLOW_TYPE": rng.choice(["请假", "报销", "采购申请", "付款申请",
                                  "用车申请", "出差", "公文审批", "印章使用"],
                                 n, p=[0.25, 0.20, 0.15, 0.15, 0.08, 0.07, 0.05, 0.05]),
        "INITIATOR": rng.choice(["张明", "李华", "王强", "刘洋", "陈静",
                                  "赵磊", "周涛", "吴霞", "郑伟", "孙杰"], n),
        "INITIATOR_DEPT": rng.choice(["生产部", "安全部", "财务部", "采购部",
                                       "综合办", "技术部", "销售部", "机电队"], n),
        "APPLY_DATE": dates.astype(str),
        "STATUS": statuses,
        "CURRENT_NODE": current_nodes,
        "APPROVER": rng.choice(["李总", "王总", "张总", "刘总", "陈总"], n),
        "AMOUNT": np.where(rng.random(n) < 0.4,
                           np.round(rng.uniform(100, 50_000, n), 2),
                           None),
    })

    df = inject(df, rng)

    for year in [2022, 2023]:
        part = df[df["APPLY_DATE"].str.startswith(str(year))]
        (HIST_DIR / "oa").mkdir(parents=True, exist_ok=True)
        part.to_parquet(HIST_DIR / "oa" / f"doc_flow_year={year}.parquet", index=False)

    print(f"  ✓ OA {len(df):,} 条")
    sz = sum(f.stat().st_size for f in (HIST_DIR / "oa").rglob("*.parquet"))
    print(f"  OA大小: {sz / 1024**2:.1f} MB")


# ─────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────

def main():
    t0 = datetime.now()
    rng = np.random.default_rng(2024)

    print("=" * 60)
    print("A公司 异构系统历史数据生成器 v3")
    print(f"VBAK={SCALE['sap_vbak']:,} VBAP={int(SCALE['sap_vbak']*SCALE['sap_vbap_ratio']):,} "
          f"LIMS={SCALE['lims_rows']:,} OA={SCALE['oa_rows']:,}")
    print("=" * 60)

    run_sap(rng)
    run_pi(rng)
    run_lims(rng)
    run_oa(rng)

    # 总大小
    total_sz = sum(f.stat().st_size for f in HIST_DIR.rglob("*.parquet"))

    meta = {
        "generated_at": datetime.now().isoformat(),
        "scale": SCALE,
        "quality": QUALITY,
        "duration_seconds": (datetime.now() - t0).total_seconds(),
        "total_size_mb": round(total_sz / 1024**2, 1),
    }
    with open(HIST_DIR / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    elapsed = (datetime.now() - t0).total_seconds()
    print("\n" + "=" * 60)
    print(f"完成，耗时 {elapsed:.1f}s | 总大小 {total_sz / 1024**2:.1f} MB")
    print(f"输出: {HIST_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
