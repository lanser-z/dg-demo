"""
将模拟数据系统的元数据直接写入 DataHub OpenSearch datasetindex_v2。
不依赖 GMS/MySQL，直接 bulk 写入 ES。
"""
import json
import os
import glob
import pandas as pd
import requests
import time

ES_URL = "http://localhost:29200"
INDEX = "datasetindex_v2"

# ============================================================
# 1. 定义要上报的数据资产（与各系统表结构对应）
# ============================================================
ASSETS = [
    # SAP-ERP
    {
        "platform": "sap_erp",
        "table": "kna1",
        "urn": "urn:li:dataset:(urn:li:dataPlatform:sap_erp,kna1,PROD)",
        "name": "kna1,PROD",
        "description": "[重要资产] SAP客户主数据 — 包含客户编码/名称/地址/统一社会信用代码",
        "browsePath": [{"id": "sap_erp"}, {"id": "kna1"}],
        "browsePathV2": ["sap_erp", "kna1"],
        "tags": ["重要资产"],
        "owner": "sales_dept",
    },
    {
        "platform": "sap_erp",
        "table": "vbak",
        "urn": "urn:li:dataset:(urn:li:dataPlatform:sap_erp,vbak,PROD)",
        "name": "vbak,PROD",
        "description": "[重要资产] SAP销售订单抬头 — 包含订单号/客户/金额/日期/订单类型",
        "browsePath": [{"id": "sap_erp"}, {"id": "vbak"}],
        "browsePathV2": ["sap_erp", "vbak"],
        "tags": ["重要资产"],
        "owner": "sales_dept",
    },
    {
        "platform": "sap_erp",
        "table": "vbap",
        "urn": "urn:li:dataset:(urn:li:dataPlatform:sap_erp,vbap,PROD)",
        "name": "vbap,PROD",
        "description": "[重要资产] SAP销售订单行项目 — 包含物料/数量/单价/批次/矿井",
        "browsePath": [{"id": "sap_erp"}, {"id": "vbap"}],
        "browsePathV2": ["sap_erp", "vbap"],
        "tags": ["重要资产"],
        "owner": "sales_dept",
    },
    {
        "platform": "sap_erp",
        "table": "likp",
        "urn": "urn:li:dataset:(urn:li:dataPlatform:sap_erp,likp,PROD)",
        "name": "likp,PROD",
        "description": "[重要资产] SAP交货单抬头 — 包含交货单号/发货状态/交货日期",
        "browsePath": [{"id": "sap_erp"}, {"id": "likp"}],
        "browsePathV2": ["sap_erp", "likp"],
        "tags": ["重要资产"],
        "owner": "sales_dept",
    },
    {
        "platform": "sap_erp",
        "table": "lips",
        "urn": "urn:li:dataset:(urn:li:dataPlatform:sap_erp,lips,PROD)",
        "name": "lips,PROD",
        "description": "[重要资产] SAP交货单行项目 — 包含物料/数量/交货单号",
        "browsePath": [{"id": "sap_erp"}, {"id": "lips"}],
        "browsePathV2": ["sap_erp", "lips"],
        "tags": ["重要资产"],
        "owner": "sales_dept",
    },
    {
        "platform": "sap_erp",
        "table": "mara",
        "urn": "urn:li:dataset:(urn:li:dataPlatform:sap_erp,mara,PROD)",
        "name": "mara,PROD",
        "description": "[重要资产] SAP物料主数据 — 包含物料编码/物料类型/计量单位",
        "browsePath": [{"id": "sap_erp"}, {"id": "mara"}],
        "browsePathV2": ["sap_erp", "mara"],
        "tags": ["重要资产"],
        "owner": "sales_dept",
    },
    # PI-System
    {
        "platform": "pi_system",
        "table": "tags",
        "urn": "urn:li:dataset:(urn:li:dataPlatform:pi_system,tags,PROD)",
        "name": "tags,PROD",
        "description": "[核心资产] PI时序传感器标签 — 100个传感器标签时序数据，含瓦斯/温度/CO等告警阈值",
        "browsePath": [{"id": "pi_system"}, {"id": "tags"}],
        "browsePathV2": ["pi_system", "tags"],
        "tags": ["核心资产"],
        "owner": "safety_dept",
    },
    # LIMS
    {
        "platform": "lims",
        "table": "samples",
        "urn": "urn:li:dataset:(urn:li:dataPlatform:lims,samples,PROD)",
        "name": "samples,PROD",
        "description": "[重要资产] LIMS煤质检测批次 — 含灰分/挥发分/硫分/发热量等指标",
        "browsePath": [{"id": "lims"}, {"id": "samples"}],
        "browsePathV2": ["lims", "samples"],
        "tags": ["重要资产"],
        "owner": "coal_quality_team",
    },
    # OA
    {
        "platform": "oa",
        "table": "doc_flow",
        "urn": "urn:li:dataset:(urn:li:dataPlatform:oa,doc_flow,PROD)",
        "name": "doc_flow,PROD",
        "description": "[一般资产] OA审批流程记录 — 包含合同/付款/采购等审批流",
        "browsePath": [{"id": "oa"}, {"id": "doc_flow"}],
        "browsePathV2": ["oa", "doc_flow"],
        "tags": ["一般资产"],
        "owner": "admin_dept",
    },
    {
        "platform": "oa",
        "table": "contract",
        "urn": "urn:li:dataset:(urn:li:dataPlatform:oa,contract,PROD)",
        "name": "contract,PROD",
        "description": "[一般资产] OA合同记录 — 包含合同编号/甲方/乙方/金额/签订日期",
        "browsePath": [{"id": "oa"}, {"id": "contract"}],
        "browsePathV2": ["oa", "contract"],
        "tags": ["一般资产"],
        "owner": "admin_dept",
    },
    {
        "platform": "oa",
        "table": "meeting",
        "urn": "urn:li:dataset:(urn:li:dataPlatform:oa,meeting,PROD)",
        "name": "meeting,PROD",
        "description": "[一般资产] OA会议记录 — 包含会议主题/参会人/会议纪要",
        "browsePath": [{"id": "oa"}, {"id": "meeting"}],
        "browsePathV2": ["oa", "meeting"],
        "tags": ["一般资产"],
        "owner": "admin_dept",
    },
    # SCADA
    {
        "platform": "scada",
        "table": "equipment_status",
        "urn": "urn:li:dataset:(urn:li:dataPlatform:scada,equipment_status,PROD)",
        "name": "equipment_status,PROD",
        "description": "[核心资产] SCADA设备状态 — 皮带机/排水泵/提升机的实时开关机状态",
        "browsePath": [{"id": "scada"}, {"id": "equipment_status"}],
        "browsePathV2": ["scada", "equipment_status"],
        "tags": ["核心资产"],
        "owner": "safety_dept",
    },
]


# ============================================================
# 2. 按系统读取 Parquet 补充行数/存储大小信息
# ============================================================
def get_parquet_stats(system, table):
    """从 Parquet 文件读取行数和存储大小"""
    root = "/home/szs/Playground/dg-demo/data/historical"
    pattern = os.path.join(root, system, "**", "*.parquet")
    files = sorted(glob.glob(pattern, recursive=True))
    if not files:
        return 0, 0
    total_rows = 0
    total_size = 0
    for f in files:
        total_size += os.path.getsize(f)
        total_rows += len(pd.read_parquet(f))
    return total_rows, total_size / 1024 / 1024


def build_es_doc(asset, rows=None, size_mb=None):
    """构造 ES 文档"""
    return {
        "urn": asset["urn"],
        "name": asset["name"],
        "description": asset["description"],
        "platform": asset["platform"],
        "tags": asset.get("tags", []),
        "browsePath": asset["browsePath"],
        "browsePathV2": asset["browsePathV2"],
        "rowCount": rows,
        "sizeInBytes": int(size_mb * 1024 * 1024) if size_mb else None,
    }


# ============================================================
# 3. Bulk 写入 ES
# ============================================================
def main():
    print(f"=== DataHub 资产上报（直接写入 OpenSearch）===")
    print(f"ES URL: {ES_URL}")
    print(f"Index: {INDEX}")
    print(f"Assets to ingest: {len(ASSETS)}")
    print()

    bulk_lines = []
    for asset in ASSETS:
        # 补充 Parquet 统计信息
        rows, size_mb = get_parquet_stats(asset["platform"], asset["table"])
        doc = build_es_doc(asset, rows=rows, size_mb=size_mb)

        # URL-encode URN 作为 _id
        import urllib.parse
        doc_id = urllib.parse.quote(asset["urn"], safe="")

        bulk_lines.append(json.dumps({"update": {"_id": doc_id, "_index": INDEX}}))
        bulk_lines.append(json.dumps({"doc": doc, "doc_as_upsert": True}))

        size_str = f"{size_mb:.1f}MB" if size_mb else "?"
        rows_str = f"{rows:,}" if rows else "?"
        print(f"  {asset['platform']}/{asset['table']}: rows={rows_str}, size={size_str}")

    print()
    print(f"Bulk request: {len(bulk_lines)} lines ({len(bulk_lines)//2} docs)")

    body = "\n".join(bulk_lines) + "\n"
    resp = requests.post(
        f"{ES_URL}/_bulk",
        headers={"Content-Type": "application/x-ndjson"},
        data=body.encode(),
        timeout=30,
    )
    result = resp.json()
    print(f"ES response: status={resp.status_code}, errors={result.get('errors')}")

    errors = []
    for item in result.get("items", []):
        action = list(item.keys())[0]
        r = item[action]
        if r.get("error"):
            errors.append(f"  {action} {r.get('_id', '')[:60]}: ERROR {r['error'].get('type')}")
        else:
            print(f"  OK: {r.get('result')} — {r.get('_id', '')[:60]}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(e)

    # ============================================================
    # 4. 验证
    # ============================================================
    print("\n=== 验证写入结果 ===")
    time.sleep(1)
    r = requests.get(f"{ES_URL}/{INDEX}/_count", timeout=10)
    cnt = r.json().get("count", 0)
    print(f"Total documents in {INDEX}: {cnt}")

    if cnt == len(ASSETS):
        print(f"✅ 全部 {len(ASSETS)} 条资产上报成功")
    else:
        print(f"⚠️  预期 {len(ASSETS)} 条，实际 {cnt} 条")

    print("\n=== 按平台统计 ===")
    platform_counts = {}
    for asset in ASSETS:
        p = asset["platform"]
        platform_counts[p] = platform_counts.get(p, 0) + 1
    for p, cnt in sorted(platform_counts.items()):
        print(f"  {p}: {cnt} 张表")

    print("\nDone.")


if __name__ == "__main__":
    main()
