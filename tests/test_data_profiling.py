"""
测试：数据探查

验证 Parquet 文件可读、分区发现、行数统计等基础能力
"""
from __future__ import annotations

import pytest
from pathlib import Path


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def historical_data_root() -> Path:
    """data/historical/ 根目录"""
    return Path(__file__).parent.parent / "data" / "historical"


@pytest.fixture
def sap_vbak_path(historical_data_root: Path) -> Path:
    """SAP VBAK 历史数据路径"""
    return historical_data_root / "sap_erp"


@pytest.fixture
def pi_tags_path(historical_data_root: Path) -> Path:
    """PI-System 标签数据路径"""
    return historical_data_root / "pi_system"


@pytest.fixture
def lims_samples_path(historical_data_root: Path) -> Path:
    """LIMS 样品数据路径"""
    return historical_data_root / "lims"


@pytest.fixture
def oa_doc_flow_path(historical_data_root: Path) -> Path:
    """OA 文档流数据路径"""
    return historical_data_root / "oa"


# ── 测试5：数据探查基础 ───────────────────────────────────────────────────

class TestDataProfiling:
    """基于本地 Parquet 文件的数据探查能力"""

    def test_historical_data_exists(self, historical_data_root: Path):
        """data/historical/ 目录必须存在"""
        assert historical_data_root.exists(), f"历史数据目录不存在: {historical_data_root}"

    def test_sap_erp_data_exists(self, historical_data_root: Path):
        """sap_erp/ 子目录存在"""
        assert (historical_data_root / "sap_erp").exists()

    def test_pi_system_data_exists(self, historical_data_root: Path):
        """pi_system/ 子目录存在"""
        assert (historical_data_root / "pi_system").exists()

    def test_lims_data_exists(self, historical_data_root: Path):
        """lims/ 子目录存在"""
        assert (historical_data_root / "lims").exists()

    def test_oa_data_exists(self, historical_data_root: Path):
        """oa/ 子目录存在"""
        assert (historical_data_root / "oa").exists()


class TestParquetReadability:
    """Parquet 文件可读性测试"""

    def test_profile_parquet_returns_dict(self):
        """profile_parquet() 应返回字典，包含行列数、列名、分区信息"""
        from dg_platform.data_profiler import profile_parquet

        result = profile_parquet(
            Path(__file__).parent.parent / "data" / "historical" / "sap_erp" / "kna1.parquet"
        )
        assert isinstance(result, dict)
        assert "row_count" in result
        assert "column_names" in result

    def test_profile_sap_vbak(self, sap_vbak_path: Path):
        """VBAK parquet 可读取，行数>0"""
        from dg_platform.data_profiler import profile_parquet

        # 读取分区文件
        vbak_files = list(sap_vbak_path.glob("vbak_year=2022.parquet"))
        assert vbak_files, "未找到 vbak_year=2022.parquet"

        profile = profile_parquet(vbak_files[0])
        assert profile["row_count"] > 0, "VBAK 行数应为正数"

    def test_profile_pi_tags(self, pi_tags_path: Path):
        """PI tags parquet 可读取"""
        from dg_platform.data_profiler import profile_parquet

        pi_files = list(pi_tags_path.glob("*.parquet"))
        assert pi_files, "PI-System 目录无 parquet 文件"

        profile = profile_parquet(pi_files[0])
        assert profile["row_count"] > 0

    def test_profile_lims_samples(self, lims_samples_path: Path):
        """LIMS samples parquet 可读取"""
        from dg_platform.data_profiler import profile_parquet

        lims_files = list(lims_samples_path.glob("*.parquet"))
        assert lims_files, "LIMS 目录无 parquet 文件"

        profile = profile_parquet(lims_files[0])
        assert profile["row_count"] > 0

    def test_profile_oa_doc_flow(self, oa_doc_flow_path: Path):
        """OA doc_flow parquet 可读取"""
        from dg_platform.data_profiler import profile_parquet

        oa_files = list(oa_doc_flow_path.glob("*.parquet"))
        assert oa_files, "OA 目录无 parquet 文件"

        profile = profile_parquet(oa_files[0])
        assert profile["row_count"] > 0


class TestPartitionDiscovery:
    """分区发现能力测试"""

    def test_discover_partitions_returns_list(self, sap_vbak_path: Path):
        """discover_partitions() 应返回分区列表"""
        from dg_platform.data_profiler import discover_partitions

        result = discover_partitions(sap_vbak_path)
        assert isinstance(result, list)

    def test_sap_vbak_has_year_partitions(self, sap_vbak_path: Path):
        """VBAK 应有 year=2022 和 year=2023 分区"""
        from dg_platform.data_profiler import discover_partitions

        partitions = discover_partitions(sap_vbak_path)
        partition_values = {p.get("partition_value") for p in partitions}

        assert "2022" in partition_values or any("2022" in str(p) for p in partitions), \
            f"未找到 year=2022 分区，实际: {partitions}"

    def test_pi_has_year_month_partitions(self, pi_tags_path: Path):
        """PI-System 应有 year=YYYY / month=MM 分区"""
        from dg_platform.data_profiler import discover_partitions

        partitions = discover_partitions(pi_tags_path)
        assert partitions, "PI-System 分区不应为空"

        # 检查是否有 year 和 month 分区字段
        has_year = any("year" in str(p).lower() for p in partitions)
        has_month = any("month" in str(p).lower() for p in partitions)
        assert has_year, f"PI-System 未找到 year 分区: {partitions}"


class TestRowCountAggregation:
    """跨分区行数汇总测试"""

    def test_count_rows_across_partitions(self, sap_vbak_path: Path):
        """跨分区汇总行数应大于单个分区"""
        from dg_platform.data_profiler import profile_parquet, count_rows

        vbak_files = list(sap_vbak_path.glob("vbak_year=*.parquet"))
        assert len(vbak_files) >= 2, "应有至少2个 VBAK 分区"

        # 单分区行数
        single = profile_parquet(vbak_files[0])["row_count"]

        # 跨分区总行数
        total = count_rows(sap_vbak_path)

        assert total >= single, f"总行数 {total} 应 >= 单分区 {single}"
