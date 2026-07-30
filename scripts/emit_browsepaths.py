"""
通过 DataHub Python SDK (rest_emitter) 写入 dataset 的
browsePathsV2 / datasetProperties / ownership / globalTags aspect 到 MySQL。

旧版本走 GMS `/aspects` 端点（v1.6.0 返回 400）或 `/openapi/v3/entity/dataset`
（202 Accepted 但实际未处理到 MySQL）。改用官方 SDK 的 rest_emitter 是稳定路径。
"""
import logging
import time

from datahub.emitter.mce_builder import (
    make_dataset_urn,
    make_tag_urn,
    make_user_urn,
)
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import (
    BrowsePathEntryClass,
    BrowsePathsV2Class,
    DatasetPropertiesClass,
    GlobalTagsClass,
    OwnerClass,
    OwnershipClass,
    OwnershipTypeClass,
    TagAssociationClass,
)

logging.basicConfig(level=logging.WARN)

GMS_URL = "http://localhost:28080"
TOKEN = ""

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

CHINESE_NAMES = {
    "lims":          {"samples":           "煤质化验样品"},
    "sap_erp":       {"kna1":              "客户主数据",
                       "vbak":             "销售订单抬头",
                       "vbap":             "销售订单行项目",
                       "likp":             "交货单抬头",
                       "lips":             "交货单行项目",
                       "mara":             "物料主数据"},
    "pi_system":     {"tags":              "PI时序标签数据"},
    "oa":            {"doc_flow":          "文档流转记录",
                       "contract":          "合同记录",
                       "meeting":          "会议记录"},
    "scada":         {"equipment_status":  "设备状态"},
}

SECURITY_MAP = {
    "lims": "重要资产", "sap_erp": "重要资产",
    "pi_system": "核心资产", "oa": "一般资产", "scada": "核心资产",
}

OWNER_MAP = {
    "lims":        ("coal_quality_team", "煤质中心"),
    "sap_erp":     ("sales_dept",        "销售部"),
    "pi_system":   ("safety_dept",       "安全部"),
    "oa":          ("admin_dept",        "综合管理部"),
    "scada":       ("safety_dept",       "安全部"),
}


def main():
    print(f"=== 写入 12 张表 aspect (DataHub SDK rest_emitter) ===")
    print(f"GMS: {GMS_URL}")
    print()

    emitter = DatahubRestEmitter(gms_server=GMS_URL, token=TOKEN)

    results = {"datasets_ok": 0, "datasets_fail": 0}
    for ds in DATASETS:
        platform = ds["platform"]
        table = ds["table"]
        urn = make_dataset_urn(platform=platform, name=table, env="PROD")
        name = CHINESE_NAMES.get(platform, {}).get(table, f"{platform}/{table}")
        sec = SECURITY_MAP.get(platform, "一般资产")
        desc = f"[{sec}] {name}"
        owner_id, _owner_name = OWNER_MAP.get(platform, ("unknown", "未知"))

        # 1. browsePathsV2
        bp = BrowsePathsV2Class(
            path=[
                BrowsePathEntryClass(id=platform, urn=f"urn:li:container:{platform}"),
                BrowsePathEntryClass(id=table,    urn=urn),
            ]
        )
        # 2. datasetProperties
        dp = DatasetPropertiesClass(
            name=name,
            description=desc,
            customProperties={
                "system":   platform,
                "table":    table,
                "security": sec,
            },
        )
        # 3. ownership
        own = OwnershipClass(
            owners=[
                OwnerClass(
                    owner=make_user_urn(owner_id),
                    type=OwnershipTypeClass.DATAOWNER,
                ),
            ]
        )
        # 4. globalTags
        tags = GlobalTagsClass(
            tags=[TagAssociationClass(tag=make_tag_urn(sec))]
        )

        print(f"[{platform}/{table}]")
        try:
            for mce_aspect in (bp, dp, own, tags):
                wrapper = MetadataChangeProposalWrapper(
                    entityUrn=urn,
                    aspect=mce_aspect,
                )
                emitter.emit_mcp(wrapper)
            print(f"  全部 aspect 写入 OK")
            results["datasets_ok"] += 1
        except Exception as e:
            print(f"  FAIL — {type(e).__name__}: {e}")
            results["datasets_fail"] += 1

        time.sleep(0.3)

    print("\n=== 汇总 ===")
    print(f"  12 张表写入: {results['datasets_ok']}/{len(DATASETS)} OK")
    if results["datasets_ok"] == len(DATASETS):
        print("\n✅ 全部完成")
    else:
        print(f"\n⚠️  {results['datasets_fail']} 张表失败")

    print("\n注意：写入 MySQL 后需等待 GMS 将数据同步到 OpenSearch 索引（< 30s）。")
    print("可通过 check_browse.py 验证 navigation 路径是否生效。")


if __name__ == "__main__":
    main()
