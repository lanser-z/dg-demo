#!/usr/bin/env python3
"""
模块一演示脚本：数据资产可视化

用法：
    uv run python scripts/demo_asset_visualization.py

依赖 DataHub（可选），DataHub 不可用时优雅降级。
"""
from __future__ import annotations

import sys
from pathlib import Path

# 确保 dg_platform 可导入
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dg_platform import (
    get_system_status,
    get_asset_catalog,
    get_quality_score_card,
    get_security_classification,
)
from dg_platform.datahub_client import is_datahub_available


def print_divider(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def main():
    print_divider("模块一：数据资产可视化")

    # ── 1. 系统接入状态 ───────────────────────────────────────
    print_divider("1. 系统接入状态")
    systems = get_system_status()
    print(f"{'系统':<12} {'状态':<12} {'行数':>12} {'大小(MB)':>12} {'负责部门'}")
    print("-" * 62)
    for s in systems:
        print(f"{s['name']:<12} {s['status']:<12} {s['record_count']:>12,} {s['size_mb']:>12.1f} {s['owner']}")

    total = sum(s["record_count"] for s in systems)
    print("-" * 62)
    print(f"{'合计':<12} {'':12} {total:>12,} {sum(s['size_mb'] for s in systems):>12.1f}")

    # ── 2. 资产目录 ───────────────────────────────────────────
    print_divider("2. 资产目录")
    df = get_asset_catalog()
    print(f"共 {len(df)} 张数据表：")
    print(df[["system", "table_name", "chinese_name", "row_count", "size_mb", "security_level"]].to_string(index=False))

    # ── 3. 质量评分卡 ────────────────────────────────────────
    print_divider("3. 质量评分卡")
    scores = get_quality_score_card()
    print(scores.to_string(index=False))
    print("\n评分说明：")
    print("  完整性(30%)：非空率")
    print("  一致性(30%)：跨系统编码一致性")
    print("  时效性(20%)：数据到达及时率")
    print("  准确性(20%)：数据准确率（异常值比例）")

    # ── 4. 安全分级 ──────────────────────────────────────────
    print_divider("4. 安全分级")
    sec = get_security_classification()
    # 统计各级别数量
    level_counts = sec["security_level"].value_counts()
    print(f"  核心资产：  {level_counts.get('核心资产', 0)} 张表")
    print(f"  重要资产：  {level_counts.get('重要资产', 0)} 张表")
    print(f"  一般资产：  {level_counts.get('一般资产', 0)} 张表")

    # ── 5. DataHub 集成检查 ─────────────────────────────────
    print_divider("5. DataHub 连接状态")
    if is_datahub_available():
        print("  ✓ DataHub 运行正常，可以进行元数据上报")
        print("  提示：运行以下命令上报资产目录到 DataHub：")
        code = (
            "from dg_platform import get_asset_catalog; "
            "from dg_platform.datahub_client import get_client; "
            "client = get_client(); "
            "result = client.ingest_metadata(get_asset_catalog()); "
            "print(result)"
        )
        print("    uv run python -c \"" + code + "\"")
    else:
        print("  ⚠ DataHub 暂不可用（正常现象，请先启动 Docker 服务）")
        print("  启动命令：")
        print("    docker-compose -f docker-compose.all-in-one.yml up -d")
        print("  验证：curl http://localhost:8080/health")

    print_divider("演示完成")


if __name__ == "__main__":
    main()
