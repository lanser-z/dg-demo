# src/dg_simulator/base_generator.py
"""
各系统数据生成器基类
"""
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import random


class BaseGenerator(ABC):
    """各系统数据生成器基类"""

    def __init__(self, config: dict, output_dir: str):
        self.config = config
        self.output_dir = output_dir
        self.rng = np.random.default_rng(seed=42)

    def generate_dates(self, start: str, end: str, rows: int) -> list:
        """生成日期序列"""
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        dates = []
        for _ in range(rows):
            date = start_dt + (end_dt - start_dt) * self.rng.random()
            dates.append(date)
        return sorted(dates)

    def add_data_quality_issues(self, df: pd.DataFrame, issue_rate: float = 0.02) -> pd.DataFrame:
        """注入数据质量问题"""
        if df is None or len(df) == 0:
            return df
        df = df.copy()
        issue_count = max(1, int(len(df) * issue_rate))

        issues = self.rng.choice(
            ['null', 'outlier', 'duplicate', 'format_error'],
            size=issue_count,
            p=[0.4, 0.3, 0.2, 0.1]
        )

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
                df.at[df.index[idx], col] = df[col].max() * 10
            elif issue == 'duplicate':
                if idx > 0:
                    df.iloc[idx] = df.iloc[idx - 1].copy()
            elif issue == 'format_error' and col in str_cols:
                df.at[df.index[idx], col] = "ERR:INVALID"

        return df
