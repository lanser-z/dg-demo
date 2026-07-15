#!/usr/bin/env python3
"""Auto-lineage 验证 — DataHub v1.6.0 把 lineage 从 dataset.upstreamLineage 改成 dataJob.dataJobInputOutput。"""
from __future__ import annotations

import json
import subprocess
import sys

ETL_JOBS = {
    "ingest_dwd": "urn:li:dataFlow:(python,ingest_dwd,dg-demo)",
    "build_dwa_sales_daily": "urn:li:dataFlow:(python,build_dwa_sales_daily,dg-demo)",
    "build_dwa_tag_alarm": "urn:li:dataFlow:(python,build_dwa_tag_alarm,dg-demo)",
    "build_dwa_coal_quality": "urn:li:dataFlow:(python,build_dwa_coal_quality,dg-demo)",
    "build_dim_mine": "urn:li:dataFlow:(python,build_dim_mine,dg-demo)",
    "build_dim_customer": "urn:li:dataFlow:(python,build_dim_customer,dg-demo)",
    "build_dim_material": "urn:li:dataFlow:(python,build_dim_material,dg-demo)",
}

EXPECTED_INPUT_FRAGMENTS = {
    "ingest_dwd": ["vbak", "tags", "samples"],
    "build_dwa_sales_daily": ["vbak"],
    "build_dwa_tag_alarm": ["tags"],
    "build_dwa_coal_quality": ["samples"],
    "build_dim_mine": ["tags", "samples"],
    "build_dim_customer": ["kna1"],
    "build_dim_material": ["vbap"],
}


def mysql_query(sql: str) -> str:
    cmd = [
        "docker", "exec", "datahub-mysql-1",
        "mysql", "-u", "root", "-pdatahub", "datahub", "-N", "-B", "-e", sql,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return r.stdout.strip() if r.returncode == 0 else ""


def find_data_job_urn(flow_urn: str) -> str:
    sql = (
        f"SELECT urn FROM metadata_aspect_v2 "
        f"WHERE aspect='dataJobKey' AND metadata LIKE '%{flow_urn}%' LIMIT 1;"
    )
    return mysql_query(sql)


def check_lineage(job_urn: str) -> tuple[list[str], list[str]]:
    sql = (
        f"SELECT metadata FROM metadata_aspect_v2 "
        f"WHERE urn='{job_urn}' AND aspect='dataJobInputOutput' "
        f"ORDER BY version DESC LIMIT 1;"
    )
    raw = mysql_query(sql)
    if not raw:
        return [], []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return [], []
    inputs = [
        e.get("destinationUrn", "")
        for e in data.get("inputDatasetEdges", [])
    ]
    outputs = [
        e.get("destinationUrn", "")
        for e in data.get("outputDatasetEdges", [])
    ]
    return inputs, outputs


def main() -> int:
    print("=" * 60)
    print("Auto-lineage 验证 — GMS v1.6.0 dataJob.dataJobInputOutput")
    print("=" * 60)
    total = passed = 0
    for job_name, flow_urn in ETL_JOBS.items():
        total += 1
        job_urn = find_data_job_urn(flow_urn)
        if not job_urn:
            print(f"  ⚠️  {job_name}: dataJob 未找到（ETL 未跑过或 lineage 未 emit）")
            continue
        inputs, outputs = check_lineage(job_urn)
        expected_inputs = EXPECTED_INPUT_FRAGMENTS.get(job_name, [])
        ok = bool(inputs) and all(
            any(frag in u for u in inputs) for frag in expected_inputs
        )
        status = "✅" if ok else "⚠️ "
        short = job_urn.split(",")[-1].rstrip(")") if "," in job_urn else job_urn
        print(f"  {status} {job_name} ({short}):")
        for frag in expected_inputs:
            found = any(frag in u for u in inputs)
            mark = "✓" if found else "✗"
            print(f"      {mark} 期望 input 包含: {frag}")
        print(f"        inputs:  {len(inputs)} datasets")
        for u in inputs:
            tail = u.split(",")[1] if "," in u else u
            print(f"          → {tail}")
        print(f"        outputs: {len(outputs)} datasets")
        for u in outputs:
            tail = u.split(",")[1] if "," in u else u
            print(f"          → {tail}")
        if ok:
            passed += 1
    print()
    print(f"结果: {passed}/{total} 通过")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
