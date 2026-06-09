"""
datahub_client — DataHub 元数据平台集成

提供：
- list_datasets(): 从 DataHub 查询数据集列表
- ingest_metadata(assets): 上报资产元数据到 DataHub
- get_lineage(guid): 查询血缘链路

注意事项：
- DataHub GMS 需要已初始化数据库（metadata_aspect 等表存在）
  使用官方 quickstart 启动时会自动初始化；单独使用 acryldata/datahub-gms:latest
  镜像时需要额外初始化步骤。如果数据库未初始化，ingest_metadata 会返回 500 错误。
- 默认 GMS 地址为 http://localhost:8080，可通过环境变量 DATAHUB_GMS_URL 覆盖。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests


@dataclass
class DataHubConfig:
    """DataHub 连接配置"""
    gms_url: str = os.getenv("DATAHUB_GMS_URL", "http://localhost:8080")
    username: str = os.getenv("DATAHUB_USER", "datahub")
    password: str = os.getenv("DATAHUB_PASSWORD", "datahub")


class DataHubClient:
    """DataHub GraphQL API 客户端"""

    def __init__(self, config: DataHubConfig | None = None):
        self.config = config or DataHubConfig()
        self._session = requests.Session()
        if self.config.username:
            self._session.auth = (self.config.username, self.config.password)

    def _graphql(self, query: str, variables: dict | None = None) -> dict:
        """执行 GraphQL 查询"""
        resp = self._session.post(
            f"{self.config.gms_url}/api/graphql",
            json={"query": query, "variables": variables or {}},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def is_alive(self) -> bool:
        """检查 DataHub GMS 是否存活"""
        try:
            resp = self._session.post(
                f"{self.config.gms_url}/api/graphql",
                json={"query": "{ __typename }"},
                timeout=3,
            )
            return resp.status_code == 200 and resp.json().get("data", {}).get("__typename") == "Query"
        except requests.RequestException:
            return False

    def list_datasets(self, platform: str | None = None) -> list[dict]:
        """
        列出 DataHub 中注册的数据集。

        Args:
            platform: 可选，筛选平台（如 "lims"）

        Returns:
            list of dataset metadata dicts
        """
        filters_line = f'filters: {{ platform: "{platform}" }},\n                    ' if platform else ""
        query = """
        query ListDatasets {
            searchAcrossEntities(
                input: {
                    query: "*",
                    """ + filters_line + """
                    start: 0,
                    count: 1000
                }
            ) {
                searchResults {
                    entity {
                        ... on Dataset {
                            name
                            description
                            platform { name }
                        }
                    }
                }
            }
        }
        """
        try:
            result = self._graphql(query)
            data = result.get("data")
            if data is None:
                return []
            return data.get("searchAcrossEntities", {}).get("searchResults", [])
        except requests.RequestException:
            return []

    def ingest_metadata(self, assets: pd.DataFrame) -> dict:
        """
        将资产目录上报到 DataHub（通过 OpenAPI v3 entity 端点）。

        注意：此功能需要 DataHub GMS 数据库已完成初始化（metadata_aspect 等表存在）。
        如果数据库未初始化，DataHub 无法持久化元数据。

        Args:
            assets: get_asset_catalog() 返回的 DataFrame

        Returns:
            {"ingested": N, "failed": N, "details": [...]}
        """
        ingest_url = f"{self.config.gms_url}/openapi/v3/entity/dataset?async=false"
        results = {"ingested": 0, "failed": 0, "details": []}

        for _, row in assets.iterrows():
            urn = f"urn:li:dataset:(urn:li:dataPlatform:{row['system'].lower().replace('-', '_')},{row['table_name'].lower()},PROD)"
            # OpenAPI v3 entity 格式（每个 aspect 需 {"value": {...}}）
            payload = [
                {
                    "urn": urn,
                    "datasetProperties": {
                        "value": {
                            "description": str(row.get("chinese_name", "")),
                            "tags": [str(row.get("security_level", ""))],
                        }
                    },
                    "ownership": {
                        "value": {
                            "owners": [
                                {
                                    "owner": f"urn:li:corpuser:{str(row.get('owner', '')).lower().replace(' ', '.')}",
                                    "type": "DATAOWNER",
                                }
                            ],
                        }
                    },
                }
            ]
            try:
                resp = self._session.post(
                    ingest_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                if resp.status_code == 200:
                    results["ingested"] += 1
                    results["details"].append({"table": row["table_name"], "status": "ok"})
                else:
                    # 尝试解析错误信息
                    err_msg = ""
                    try:
                        err_data = resp.json()
                        err_msg = err_data.get("message", "")[:80]
                    except Exception:
                        err_msg = resp.text[:80]
                    results["failed"] += 1
                    results["details"].append({
                        "table": row["table_name"],
                        "status": "error",
                        "code": resp.status_code,
                        "msg": err_msg,
                    })
            except requests.RequestException as e:
                results["failed"] += 1
                results["details"].append({"table": row["table_name"], "status": "error", "msg": str(e)})

        return results

    def get_lineage(self, guid: str) -> dict:
        """
        查询指定实体的血缘链路。

        Returns:
            {"upstream": [...], "downstream": [...]}
        """
        query = """
        query GetLineage($guid: String!) {
            dataset(urn: $guid) {
                lineage {
                    upstream {
                        entity { urn name type displayName }
                    }
                    downstream {
                        entity { urn name type displayName }
                    }
                }
            }
        }
        """
        try:
            result = self._graphql(query, {"guid": guid})
            lineage = result.get("data", {}).get("dataset", {})
            return lineage.get("lineage", {}) if lineage else {}
        except requests.RequestException:
            return {"upstream": [], "downstream": []}


# ── 便捷函数 ────────────────────────────────────────────────────────────────

_client: DataHubClient | None = None


def get_client() -> DataHubClient:
    """返回全局 DataHub 客户端（延迟初始化）"""
    global _client
    if _client is None:
        _client = DataHubClient()
    return _client


def is_datahub_available() -> bool:
    """检查 DataHub 是否可用"""
    return get_client().is_alive()
