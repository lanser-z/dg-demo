"""
register_subject_dwd.py — Phase 2 / Background §6.11 DataHub 主题域 DWD 注册

向 DataHub GMS 注册：
1. `dwd` 自定义 platform（urn:li:dataPlatform:dwd，display name "DWD"）
2. 6 张新主题 DWD 表的 `datasetKey` + `datasetProperties` aspect（customProperties 标 layer/subject）

URN 格式（canonical）：
    Platform:  urn:li:dataPlatform:dwd
    Dataset:   urn:li:dataset:(urn:li:dataPlatform:dwd,dwd.{subject}.{table},PROD)
    例:        urn:li:dataset:(urn:li:dataPlatform:dwd,dwd.sales.dwd_vbak,PROD)

调用：
    uv run python scripts/register_subject_dwd.py

依赖：acryl-datahub[datahub-rest]>=0.12
"""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    DataPlatformInfoClass,
    DatasetKeyClass,
    DatasetPropertiesClass,
    PlatformTypeClass,
)
from datahub.utilities.urns.data_platform_urn import DataPlatformUrn
from datahub.utilities.urns.dataset_urn import DatasetUrn

GMS_URL = os.environ.get("DATAHUB_GMS_URL", "http://localhost:28080")
PLATFORM_NAME = "dwd"
PLATFORM_DISPLAY_NAME = "DWD"

SUBJECT_TABLES: list[tuple[str, str, str]] = [
    ("sales", "dwd_vbak", "SAP 销售订单抬头清洗表（主题：销售）"),
    ("sales", "dwd_vbap", "SAP 销售订单行项目清洗表（主题：销售）"),
    ("sales", "dwd_kna1", "SAP 客户主数据清洗表（主题：销售）"),
    ("production", "dwd_tags", "PI System 时序标签清洗表（主题：生产）"),
    ("coal_quality", "dwd_samples", "LIMS 样品化验清洗表（主题：煤质）"),
    ("finance", "dwd_doc_flow", "OA 文档流清洗表（主题：财务）"),
]

log = logging.getLogger("register_subject_dwd")


def _build_emitter() -> DatahubRestEmitter:
    return DatahubRestEmitter(gms_server=GMS_URL, token=None)


def register_platform(emitter: DatahubRestEmitter) -> None:
    """注册 `dwd` 自定义 platform（幂等）。"""
    platform_urn = DataPlatformUrn(platform_name=PLATFORM_NAME)
    aspect = DataPlatformInfoClass(
        name=PLATFORM_NAME,
        type=PlatformTypeClass.OTHERS,
        datasetNameDelimiter=".",
        displayName=PLATFORM_DISPLAY_NAME,
        logoUrl="https://raw.githubusercontent.com/datahub-project/datahub/master/datahub-web-react/src/images/datahub-logo.svg",
    )
    mcp = MetadataChangeProposalWrapper(
        entityUrn=str(platform_urn),
        aspect=aspect,
    )
    emitter.emit(mcp)
    log.info("✅ platform registered: %s", platform_urn)


def register_dataset(
    emitter: DatahubRestEmitter,
    subject: str,
    table: str,
    description: str,
) -> str:
    """注册一张新主题 DWD 表的 datasetKey + datasetProperties，返回 URN。"""
    dataset_name = f"dwd.{subject}.{table}"
    dataset_urn = DatasetUrn(
        platform=PLATFORM_NAME,
        name=dataset_name,
        env="PROD",
    )

    key_aspect = DatasetKeyClass(
        platform=PLATFORM_NAME,
        name=dataset_name,
        origin="PROD",
    )
    emitter.emit(
        MetadataChangeProposalWrapper(
            entityUrn=str(dataset_urn),
            aspect=key_aspect,
        )
    )

    props_aspect = DatasetPropertiesClass(
        description=description,
        customProperties={
            "layer": "dwd",
            "subject": subject,
            "table": table,
            "lake_path": f"data/lakehouse/dwd/{subject}/{table}",
        },
        name=f"{subject}.{table}",
        qualifiedName=str(dataset_urn),
    )
    emitter.emit(
        MetadataChangeProposalWrapper(
            entityUrn=str(dataset_urn),
            aspect=props_aspect,
        )
    )

    log.info("✅ %s subject=%s table=%s", dataset_urn, subject, table)
    return str(dataset_urn)


def verify_dataset(urn: str) -> bool:
    """查 GMS：datasetKey aspect 是否已落库。"""
    import urllib.parse
    import requests
    enc = urllib.parse.quote(urn, safe="")
    r = requests.get(
        f"{GMS_URL}/aspects/{enc}?aspect=datasetKey&version=0",
        auth=("datahub", "datahub"),
        timeout=10,
    )
    return r.status_code == 200


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    log.info("DataHub GMS: %s", GMS_URL)
    emitter = _build_emitter()

    register_platform(emitter)
    time.sleep(0.5)

    print()
    print("=" * 60)
    print("📦 6 张新主题 DWD 表注册到 DataHub")
    print("=" * 60)
    urns: list[str] = []
    for subject, table, desc in SUBJECT_TABLES:
        urn = register_dataset(emitter, subject, table, desc)
        urns.append(urn)
        print(f"  ✅ {urn}")

    print()
    print("⏳ 等待 5s 让 GMS 异步消费 MCP...")
    time.sleep(5)
    print("=" * 60)
    print("🔍 验证 datasetKey aspect")
    print("=" * 60)
    failed: list[str] = []
    for urn in urns:
        ok = verify_dataset(urn)
        mark = "✅" if ok else "❌"
        print(f"  {mark} {urn}")
        if not ok:
            failed.append(urn)

    print()
    print("=" * 60)
    print(f"✅ 注册完成: {len(urns) - len(failed)}/{len(urns)} datasetKey 验证通过")
    if failed:
        print(f"❌ 失败: {len(failed)}")
    print("=" * 60)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
