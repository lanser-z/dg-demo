"""
通过 GMS REST API 写入 DataHub dataset entity（正确方式）。
使用 MetadataChangeProposalWrapper + DatahubRestEmitter，
GMS 自动将数据写入 MySQL 并同步到 OpenSearch。
"""
import datahub.metadata.schema_classes as schema
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.emitter.mcp import MetadataChangeProposalWrapper

GMS_HOST = "http://localhost:28080"

ASSETS = [
    {"platform": "sap_erp",   "table": "kna1",  "description": "SAP客户主数据 — 包含客户编码/名称/地址/统一社会信用代码"},
    {"platform": "sap_erp",   "table": "vbak",  "description": "SAP销售订单抬头 — 包含订单号/客户/金额/日期/订单类型"},
    {"platform": "sap_erp",   "table": "vbap",  "description": "SAP销售订单行项目 — 包含物料/数量/单价/批次/矿井"},
    {"platform": "sap_erp",   "table": "likp",  "description": "SAP交货单抬头 — 包含交货单号/发货状态/交货日期"},
    {"platform": "sap_erp",   "table": "lips",  "description": "SAP交货单行项目 — 包含物料/数量/交货单号"},
    {"platform": "sap_erp",   "table": "mara",  "description": "SAP物料主数据 — 包含物料编码/物料类型/计量单位"},
    {"platform": "pi_system", "table": "tags",   "description": "PI时序传感器标签 — 100个传感器标签时序数据，含瓦斯/温度/CO等告警阈值"},
    {"platform": "lims",      "table": "samples","description": "LIMS煤质检测批次 — 含灰分/挥发分/硫分/发热量等指标"},
    {"platform": "oa",        "table": "doc_flow","description": "OA审批流程记录 — 包含合同/付款/采购等审批流"},
    {"platform": "oa",        "table": "contract", "description": "OA合同记录 — 包含合同编号/甲方/乙方/金额/签订日期"},
    {"platform": "oa",        "table": "meeting",  "description": "OA会议记录 — 包含会议主题/参会人/会议纪要"},
    {"platform": "scada",     "table": "equipment_status","description": "SCADA设备状态 — 皮带机/排水泵/提升机的实时开关机状态"},
]

emitter = DatahubRestEmitter(gms_server=GMS_HOST, timeout_sec=30)
print(f"Connected to GMS: {GMS_HOST}")

for asset in ASSETS:
    platform = asset["platform"]
    table   = asset["table"]
    desc    = asset["description"]
    urn     = f"urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)"
    plat_urn = f"urn:li:dataPlatform:{platform}"

    aspects_ok = []

    def emit(aspect_obj, aspect_name):
        try:
            mcp = MetadataChangeProposalWrapper(
                entityUrn=urn,
                entityType="dataset",
                aspect=aspect_obj,
                changeType="UPSERT",
            )
            emitter.emit(mcp)
            aspects_ok.append(aspect_name)
        except Exception as e:
            print(f"  ERROR {aspect_name}: {e}")

    # 1. DatasetKey (key aspect)
    emit(schema.DatasetKeyClass(
        platform=plat_urn,
        name=table,
        origin="PROD",
    ), "datasetKey")

    # 2. DatasetProperties
    emit(schema.DatasetPropertiesClass(
        name=table,
        description=desc,
        customProperties={},
    ), "datasetProperties")

    # 3. DataPlatformInstance
    emit(schema.DataPlatformInstanceClass(
        platform=plat_urn,
    ), "dataPlatformInstance")

    # 4. Ownership
    emit(schema.OwnershipClass(
        owners=[
            schema.OwnerClass(
                owner="urn:li:corpuser:datahub",
                type=schema.OwnershipTypeClass.TECHNICAL_OWNER,
                source=schema.OwnershipSourceClass(
                    type=schema.OwnershipSourceTypeClass.MANUAL,
                ),
            )
        ]
    ), "ownership")

    # 5. BrowsePathsV2
    emit(schema.BrowsePathsV2Class(
        path=[schema.BrowsePathEntryClass(id=platform)]
    ), "browsePathsV2")

    print(f"  {platform:10s}/{table:20s} → {aspects_ok}")

emitter.flush()
print("\nAll datasets written successfully.")
