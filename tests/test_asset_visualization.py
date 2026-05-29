"""
测试：数据资产可视化

TDD 阶段一（Red）：验证功能不存在，测试应全部失败
TDD 阶段二（Green）：实现最简代码使测试通过
"""
from __future__ import annotations

import pytest
from pathlib import Path


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def historical_data_root() -> Path:
    """data/historical/ 根目录"""
    root = Path(__file__).parent.parent / "data" / "historical"
    return root


@pytest.fixture
def incremental_data_root() -> Path:
    """data/incremental/ 根目录"""
    root = Path(__file__).parent.parent / "data" / "incremental"
    return root


# ── 测试1：系统接入状态 ────────────────────────────────────────────────────

class TestSystemStatus:
    """5个系统接入状态应可枚举，每系统有 name/status/record_count"""

    def test_get_system_status_returns_list(self):
        """get_system_status() 应返回列表"""
        from dg_platform.asset_visualizer import get_system_status

        result = get_system_status()
        assert isinstance(result, list)

    def test_five_systems_enumerated(self):
        """应有5个系统：SAP-ERP / PI-System / SCADA / LIMS / OA"""
        from dg_platform.asset_visualizer import get_system_status

        systems = get_system_status()
        system_names = {s["name"] for s in systems}

        expected = {"SAP-ERP", "PI-System", "SCADA", "LIMS", "OA"}
        assert system_names == expected, f"期望 {expected}，实际 {system_names}"

    def test_each_system_has_required_fields(self):
        """每系统应包含 name / status / record_count / size_mb 字段"""
        from dg_platform.asset_visualizer import get_system_status

        systems = get_system_status()
        required_fields = {"name", "status", "record_count", "size_mb"}

        for s in systems:
            assert required_fields.issubset(s.keys()), f"系统 {s.get('name')} 缺少字段"

    def test_status_values_are_valid(self):
        """status 只能是 connected / disconnected / unknown"""
        from dg_platform.asset_visualizer import get_system_status

        systems = get_system_status()
        valid_statuses = {"connected", "disconnected", "unknown"}

        for s in systems:
            assert s["status"] in valid_statuses, f"系统 {s['name']} status 无效: {s['status']}"

    def test_record_count_is_non_negative(self):
        """record_count >= 0"""
        from dg_platform.asset_visualizer import get_system_status

        systems = get_system_status()
        for s in systems:
            assert s["record_count"] >= 0, f"系统 {s['name']} 行数为负: {s['record_count']}"


# ── 测试2：资产目录 ────────────────────────────────────────────────────────

class TestAssetCatalog:
    """资产目录应返回每张表的元数据"""

    def test_get_asset_catalog_returns_dataframe(self):
        """get_asset_catalog() 应返回 DataFrame"""
        from dg_platform.asset_visualizer import get_asset_catalog

        result = get_asset_catalog()
        assert result is not None

    def test_required_columns_present(self):
        """资产目录 DataFrame 必须包含以下列"""
        from dg_platform.asset_visualizer import get_asset_catalog

        df = get_asset_catalog()
        required_cols = {
            "table_name",
            "chinese_name",
            "owner",
            "row_count",
            "size_mb",
            "partition_field",
            "system",
        }
        missing = required_cols - set(df.columns)
        assert not missing, f"缺少列: {missing}"

    def test_covers_all_systems(self):
        """5个系统均应有资产记录"""
        from dg_platform.asset_visualizer import get_asset_catalog

        df = get_asset_catalog()
        systems_in_catalog = set(df["system"].unique())

        expected = {"SAP-ERP", "PI-System", "SCADA", "LIMS", "OA"}
        missing = expected - systems_in_catalog
        assert not missing, f"资产目录缺少系统: {missing}"

    def test_sap_tables_present(self):
        """SAP-ERP 应至少有: vbak, vbap, kna1"""
        from dg_platform.asset_visualizer import get_asset_catalog

        df = get_asset_catalog()
        sap_tables = set(df[df["system"] == "SAP-ERP"]["table_name"].str.lower())

        expected = {"vbak", "vbap", "kna1"}
        missing = expected - sap_tables
        assert not missing, f"SAP-ERP 缺少表: {missing}"

    def test_row_count_positive(self):
        """有历史数据的表 row_count > 0（SCADA 实时系统除外）"""
        from dg_platform.asset_visualizer import get_asset_catalog

        df = get_asset_catalog()
        # SCADA 是实时流系统，无历史文件，行数允许为 0
        non_scada = df[df["system"] != "SCADA"]
        zero_rows = non_scada[non_scada["row_count"] <= 0]
        assert zero_rows.empty, f"以下表行数为0: {zero_rows['table_name'].tolist()}"

    def test_size_mb_positive(self):
        """有历史数据的表 size_mb > 0（SCADA 实时系统除外）"""
        from dg_platform.asset_visualizer import get_asset_catalog

        df = get_asset_catalog()
        non_scada = df[df["system"] != "SCADA"]
        zero_size = non_scada[non_scada["size_mb"] <= 0]
        assert zero_size.empty, f"以下表大小为0: {zero_size['table_name'].tolist()}"


# ── 测试3：质量评分卡 ───────────────────────────────────────────────────────

class TestQualityScoreCard:
    """每系统应有质量评分（完整性/一致性/时效性/准确性）"""

    def test_get_quality_score_card_returns_dataframe(self):
        """get_quality_score_card() 应返回 DataFrame"""
        from dg_platform.asset_visualizer import get_quality_score_card

        result = get_quality_score_card()
        assert result is not None

    def test_required_columns_present(self):
        """评分卡应包含系统和4个维度"""
        from dg_platform.asset_visualizer import get_quality_score_card

        df = get_quality_score_card()
        required_cols = {"system", "completeness", "consistency", "timeliness", "accuracy"}
        missing = required_cols - set(df.columns)
        assert not missing, f"缺少列: {missing}"

    def test_covers_five_systems(self):
        """5个系统均应有评分"""
        from dg_platform.asset_visualizer import get_quality_score_card

        df = get_quality_score_card()
        systems = set(df["system"].unique())
        expected = {"SAP-ERP", "PI-System", "SCADA", "LIMS", "OA"}
        assert systems == expected

    def test_score_range_0_to_100(self):
        """各维度评分在 0-100 之间"""
        from dg_platform.asset_visualizer import get_quality_score_card

        df = get_quality_score_card()
        score_cols = ["completeness", "consistency", "timeliness", "accuracy"]

        for col in score_cols:
            assert df[col].between(0, 100).all(), \
                f"{col} 列存在超出 0-100 范围的分数"

    def test_overall_score_column_exists(self):
        """应有综合得分列"""
        from dg_platform.asset_visualizer import get_quality_score_card

        df = get_quality_score_card()
        # 综合得分 = 完整性*0.3 + 一致性*0.3 + 时效性*0.2 + 准确性*0.2
        assert "overall_score" in df.columns, \
            f"缺少综合得分列，当前列: {df.columns.tolist()}"


# ── 测试4：安全分级 ────────────────────────────────────────────────────────

class TestSecurityClassification:
    """每系统/表应有安全分级：核心资产/重要资产/一般资产"""

    def test_get_security_classification_returns_dataframe(self):
        """get_security_classification() 应返回 DataFrame"""
        from dg_platform.asset_visualizer import get_security_classification

        result = get_security_classification()
        assert result is not None

    def test_required_columns_present(self):
        """安全分级 DataFrame 必须包含"""
        from dg_platform.asset_visualizer import get_security_classification

        df = get_security_classification()
        required_cols = {"system", "table_name", "security_level"}
        missing = required_cols - set(df.columns)
        assert not missing, f"缺少列: {missing}"

    def test_valid_security_levels(self):
        """security_level 只可是: 核心资产 / 重要资产 / 一般资产"""
        from dg_platform.asset_visualizer import get_security_classification

        df = get_security_classification()
        valid_levels = {"核心资产", "重要资产", "一般资产"}

        invalid = df[~df["security_level"].isin(valid_levels)]
        assert invalid.empty, f"存在无效安全分级: {invalid['security_level'].unique()}"

    def test_all_tables_classified(self):
        """资产目录中所有表均应有安全分级"""
        from dg_platform.asset_visualizer import get_asset_catalog, get_security_classification

        catalog = get_asset_catalog()
        security = get_security_classification()

        catalog_tables = set(catalog["table_name"])
        security_tables = set(security["table_name"])

        unclassified = catalog_tables - security_tables
        assert not unclassified, f"以下表未分类: {unclassified}"
