#!/usr/bin/env python3
"""
GMS REST API 示例脚本
展示如何通过 Python requests 与 DataHub GMS 交互

使用方式:
    uv run python scripts/gms_rest_api_example.py

注意: GMS 不支持直接 POST /entities 写入。正确写入方式:
  1. datahub ingest -c delta-lake-ingestion.yaml  (推荐)
  2. datahub actions -c datahub-actions.yml       (Kafka 事件流)
  3. GraphQL patchEntity mutation (开发调试)

参考: docs.datahub.com/docs/metadata-service
"""

import requests

GMS_SERVER = "http://localhost:28080"
DATASET_URN = "urn:li:dataset:(urn:li:dataPlatform:delta-lake,data/lakehouse/dwd/sap_erp/kna1,PROD)"


def check_health():
    """验证 GMS 健康状态"""
    response = requests.get(f"{GMS_SERVER}/health", timeout=5)
    print(f"[Health Check] Status: {response.status_code}")
    if response.status_code == 200:
        print(f"[Health Check] Response: {response.text[:100]}")
    return response.status_code == 200


def get_dataset(urn: str) -> dict:
    """
    通过 OpenAPI GET 读取 dataset entity 的 browsePaths aspect

    Args:
        urn: Dataset URN

    Returns:
        Response JSON
    """
    url = f"{GMS_SERVER}/openapi/entities/v1/latest"
    params = {"urns": urn}
    response = requests.get(url, params=params, timeout=5)
    print(f"[GET Dataset] Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        aspects = data.get("responses", {}).get(urn, {}).get("aspects", {})
        print(f"[GET Dataset] Aspects found: {list(aspects.keys())}")
        return data
    else:
        print(f"[GET Dataset] Response: {response.text[:200]}")
        return {}


if __name__ == "__main__":
    print("=== GMS REST API 示例 ===")
    print(f"GMS Server: {GMS_SERVER}")

    if check_health():
        print("\n[OK] GMS is healthy")

        print(f"\n[Example] Reading dataset entity:")
        print(f"  URN: {DATASET_URN}")
        result = get_dataset(DATASET_URN)
        print(f"\n[Result] Received {len(result)} response(s)")

        print("\n[Note] Direct POST /entities is not supported.")
        print("       Use datahub ingest or datahub actions for ingestion:")
        print("         uv run datahub ingest -c scripts/delta-lake-ingestion.yaml")
        print("         datahub actions -c scripts/datahub-actions.yml")
    else:
        print("\n[ERROR] GMS is not reachable. Is DataHub running?")
        print("  Run: datahub docker quickstart")
