# src/dg_simulator/incremental_base.py
"""
增量数据生成器基类
支持 append / upsert / overwrite 三种增量模式
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Literal


class IncrementalGenerator(ABC):
    """增量数据生成器基类"""

    def __init__(self, config: dict, output_base: str):
        self.config = config
        self.output_base = Path(output_base)
        self.rng = np.random.default_rng()
        self.issue_rate = config.get('issue_rate', 0.02)  # 默认2%问题率

    def _ensure_dir(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_parquet(self, df: pd.DataFrame, table: str, date_str: str, system: str):
        """写入增量Parquet，带分区标记"""
        if df is None or len(df) == 0:
            return None

        date_path = self.output_base / date_str / system
        self._ensure_dir(date_path)

        file_path = date_path / f'{table}.parquet'
        df.to_parquet(file_path, index=False)

        # 写入本批次元数据
        meta = {
            'table': table,
            'system': system,
            'date': date_str,
            'rows': len(df),
            'written_at': datetime.now().isoformat(),
            'file_size_bytes': file_path.stat().st_size,
        }

        meta_dir = date_path / '_meta'
        self._ensure_dir(meta_dir)
        meta_file = meta_dir / f'{table}.json'
        with open(meta_file, 'w') as f:
            json.dump(meta, f, indent=2)

        return meta

    def add_quality_issues(self, df: pd.DataFrame) -> pd.DataFrame:
        """注入数据质量问题（持续性注入，与历史一致）"""
        if df is None or len(df) == 0:
            return df

        df = df.copy()
        issue_count = max(1, int(len(df) * self.issue_rate))

        issues = self.rng.choice(
            ['null', 'outlier', 'duplicate', 'format_error'],
            size=issue_count,
            p=[0.4, 0.25, 0.2, 0.15]  # null最常见
        )

        # 只对数值型和字符串型列注入问题
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        str_cols = df.select_dtypes(include=['object']).columns.tolist()
        all_cols = numeric_cols + str_cols

        if not all_cols:
            return df

        for issue in issues:
            idx = self.rng.integers(0, len(df))
            col = self.rng.choice(all_cols)

            if issue == 'null':
                df.at[df.index[idx], col] = None
            elif issue == 'outlier' and col in numeric_cols:
                df.at[df.index[idx], col] = df[col].max() * (5 + self.rng.random() * 10)
            elif issue == 'duplicate':
                if idx > 0:
                    df.iloc[idx] = df.iloc[idx - 1].copy()
            elif issue == 'format_error' and col in str_cols:
                df.at[df.index[idx], col] = "ERR:INVALID"

        return df

    @abstractmethod
    def generate(self, date_str: str) -> dict:
        """生成某一天的增量数据，返回写入的元数据列表"""
        pass


class AppendIncremental(IncrementalGenerator):
    """追加型增量：时序数据（PI-System、SCADA）"""

    def generate(self, date_str: str) -> dict:
        """PI追加模式：整天数据，每30秒一个点"""
        pass


class UpsertIncremental(IncrementalGenerator):
    """ upsert型增量：业务数据（ERP订单、LIMS）"""
    pass


class OverwriteIncremental(IncrementalGenerator):
    """覆盖型增量：主数据（KNA1、客户信息）"""
    pass
