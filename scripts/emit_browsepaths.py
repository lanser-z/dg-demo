"""
通过 GMS REST API 为数据集写入 browsePaths 和 browsePathsV2 aspect。
使用 GMS 的 MCP REST endpoint，不依赖 datahub SDK。
"""
import requests
import time

GMS_URL = "http://localhost:28080"
AUTH = ("datahub", "datahub")

DATASETS = [
    {"platform": "lims",          "table": "samples"},
    {"platform": "sap_erp",       "table": "kna1"},
    {"platform": "sap_erp",       "table": "vbak"},
    {"platform": "sap_erp",       "table": "vbap"},
    {"platform": "sap_erp",       "table": "likp"},
    {"platform": "sap_erp",       "table": "lips"},
    {"platform": "sap_erp",       "table": "mara"},
    {"platform": "pi_system",     "table": "tags"},
    {"platform": "oa",            "table": "doc_flow"},
    {"platform": "oa",            "table": "contract"},
    {"platform": "oa",            "table": "meeting"},
    {"platform": "scada",         "table": "equipment_status"},
]


def build_urn(platform, table):
    return f"urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)"


def write_browse_path_v2(urn, platform, table):
    """写入 browsePathsV2 aspect"""
    payload = {
        "entityUrn": urn,
        "entityType": "dataset",
        "aspectName": "browsePathsV2",
        "changeType": "UPSERT",
        "aspect": {
            "path": [
                {"id": platform},
                {"id": table},
            ]
        },
    }
    r = requests.post(
        f"{GMS_URL}/aspects",
        json=payload,
        auth=AUTH,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    return r


def write_dataset_properties(urn, platform, table):
    """写入 datasetProperties aspect（中文名/描述）"""
    chinese_names = {
        "lims":          {"samples":           "LIMS煤质检测批次"},
        "sap_erp":       {"kna1":             "SAP客户主数据",
                           "vbak":             "SAP销售订单抬头",
                           "vbap":             "SAP销售订单行项",
                           "likp":             "SAP交货单抬头",
                           "lips":             "SAP交货单行项目",
                           "mara":             "SAP物料主数据"},
        "pi_system":     {"tags":              "PI时序传感器标签"},
        "oa":            {"doc_flow":          "OA审批流程记录",
                           "contract":          "OA合同记录",
                           "meeting":          "OA会议记录"},
        "scada":         {"equipment_status":  "SCADA设备状态"},
    }
    security_map = {
        "lims": "重要资产", "sap_erp": "重要资产",
        "pi_system": "核心资产", "oa": "一般资产", "scada": "核心资产",
    }

    name = chinese_names.get(platform, {}).get(table, f"{platform}/{table}")
    desc = f"[{security_map.get(platform, '一般资产')}] {name}"
    tags = [security_map.get(platform, "一般资产")]

    payload = {
        "entityUrn": urn,
        "entityType": "dataset",
        "aspectName": "datasetProperties",
        "changeType": "UPSERT",
        "aspect": {
            "description": desc,
            "tags": tags,
        },
    }
    r = requests.post(
        f"{GMS_URL}/aspects",
        json=payload,
        auth=AUTH,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    return r


def write_ownership(urn, platform):
    """写入 ownership aspect"""
    owner_map = {
        "lims":        ("coal_quality_team", "煤质中心"),
        "sap_erp":     ("sales_dept",        "销售部"),
        "pi_system":   ("safety_dept",        "安全部"),
        "oa":          ("admin_dept",         "综合管理部"),
        "scada":       ("safety_dept",        "安全部"),
    }
    owner_id, owner_name = owner_map.get(platform, ("unknown", "未知"))

    payload = {
        "entityUrn": urn,
        "entityType": "dataset",
        "aspectName": "ownership",
        "changeType": "UPSERT",
        "aspect": {
            "owners": [
                {
                    "owner": f"urn:li:corpuser:{owner_id}",
                    "type": "DATAOWNER",
                    "source": "DATA_PROCESS",
                }
            ]
        },
    }
    r = requests.post(
        f"{GMS_URL}/aspects",
        json=payload,
        auth=AUTH,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    return r


def main():
    print(f"=== 写入 BrowsePaths + DatasetProperties + Ownership ===")
    print(f"GMS: {GMS_URL}")
    print(f"Datasets: {len(DATASETS)}")
    print()

    results = {"browseV2": 0, "properties": 0, "ownership": 0, "failed": 0}

    for ds in DATASETS:
        platform = ds["platform"]
        table = ds["table"]
        urn = build_urn(platform, table)
        print(f"\n[{platform}/{table}]")

        # browsePathsV2
        r1 = write_browse_path_v2(urn, platform, table)
        if r1.status_code in (200, 201):
            print(f"  browsePathsV2: {r1.status_code} OK")
            results["browseV2"] += 1
        else:
            print(f"  browsePathsV2: {r1.status_code} FAIL — {r1.text[:100]}")
            results["failed"] += 1

        # datasetProperties
        r2 = write_dataset_properties(urn, platform, table)
        if r2.status_code in (200, 201):
            print(f"  datasetProperties: {r2.status_code} OK")
            results["properties"] += 1
        else:
            print(f"  datasetProperties: {r2.status_code} FAIL — {r2.text[:100]}")

        # ownership
        r3 = write_ownership(urn, platform)
        if r3.status_code in (200, 201):
            print(f"  ownership: {r3.status_code} OK")
            results["ownership"] += 1
        else:
            print(f"  ownership: {r3.status_code} FAIL — {r3.text[:100]}")

        time.sleep(0.3)

    print("\n=== 汇总 ===")
    print(f"  browsePathsV2 写入: {results['browseV2']}/{len(DATASETS)} OK")
    print(f"  datasetProperties 写入: {results['properties']}/{len(DATASETS)} OK")
    print(f"  ownership 写入: {results['ownership']}/{len(DATASETS)} OK")
    if results["failed"] == 0:
        print("\n✅ 全部完成")
    else:
        print(f"\n⚠️  {results['failed']} 条失败")

    print("\n注意：写入 MySQL 后需等待 GMS 将数据同步到 OpenSearch 索引。")
    print("可通过 Browse API 验证导航路径是否生效。")


if __name__ == "__main__":
    main()
