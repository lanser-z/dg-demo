"""
测试：DataHub 客户端

验证 DataHub 客户端的优雅降级（网络不可用时不崩溃）
"""
import pytest
from unittest.mock import patch, MagicMock

from dg_platform.datahub_client import (
    DataHubClient,
    DataHubConfig,
    is_datahub_available,
)


class TestDataHubClient:
    """DataHub 客户端测试"""

    def test_client_initializes_with_defaults(self):
        """客户端初始化成功"""
        client = DataHubClient()
        assert client.config.gms_url == "http://localhost:8080"

    def test_client_initializes_with_custom_config(self):
        """自定义配置正确生效"""
        config = DataHubConfig(gms_url="http://custom:9090")
        client = DataHubClient(config)
        assert client.config.gms_url == "http://custom:9090"

    def test_is_alive_returns_false_when_unreachable(self):
        """DataHub 不可达时返回 False（不抛异常）"""
        client = DataHubClient(DataHubConfig(gms_url="http://localhost:99999"))
        # 网络不可达时应返回 False，不是抛异常
        result = client.is_alive()
        assert isinstance(result, bool)
        assert result is False

    def test_list_datasets_returns_list_when_unreachable(self):
        """DataHub 不可达时 list_datasets 返回空列表（不抛异常）"""
        client = DataHubClient(DataHubConfig(gms_url="http://localhost:99999"))
        result = client.list_datasets()
        assert isinstance(result, list)
        assert result == []

    def test_ingest_metadata_returns_structured_result(self):
        """ingest_metadata 返回标准结构"""
        import pandas as pd
        from dg_platform.datahub_client import DataHubClient, DataHubConfig

        client = DataHubClient(DataHubConfig(gms_url="http://localhost:99999"))
        test_df = pd.DataFrame([{
            "system": "SAP-ERP",
            "table_name": "VBAK",
            "chinese_name": "销售订单抬头",
            "owner": "销售部",
            "row_count": 1000,
            "size_mb": 10.0,
            "partition_field": "year",
            "security_level": "重要资产",
        }])

        result = client.ingest_metadata(test_df)
        assert "ingested" in result
        assert "failed" in result
        assert "details" in result
        assert result["failed"] == 1  # 无法连接，所以 failed

    def test_get_lineage_returns_dict_when_unreachable(self):
        """get_lineage 不可达时返回空结构（不抛异常）"""
        client = DataHubClient(DataHubConfig(gms_url="http://localhost:99999"))
        result = client.get_lineage("some-guid")
        assert isinstance(result, dict)
        assert "upstream" in result
        assert "downstream" in result

    def test_is_datahub_available_returns_bool(self):
        """is_datahub_available 返回布尔值"""
        result = is_datahub_available()
        assert isinstance(result, bool)
