# src/dg_simulator/lims_generator.py
"""
LIMS 煤质检测生成器（历史数据）
"""
import pandas as pd
import numpy as np
from .base_generator import BaseGenerator

MINE_CODES = ['M001', 'M002', 'M003', 'M004', 'M005']
SAMPLE_TYPES = ['原煤', '精煤', '中煤', '矸石', '洗煤']


class LIMSGenerator(BaseGenerator):

    def generate_samples(self, rows: int = 800000) -> pd.DataFrame:
        df = pd.DataFrame({
            'SAMPLE_ID': [f'LM{random.randint(100000, 999999)}' for _ in range(rows)],
            'MINE_CODE': np.random.choice(MINE_CODES, rows),
            'SAMPLE_TYPE': np.random.choice(SAMPLE_TYPES, rows, p=[0.4, 0.3, 0.1, 0.1, 0.1]),
            'SAMPLING_DATE': self.generate_dates('2021-01-01', '2024-01-01', rows),
            'REPORTER': np.random.choice(['张工', '李工', '王工', '刘工', '陈工'], rows),
        })
        df['TEST_DATE'] = df['SAMPLING_DATE'] + pd.to_timedelta(np.random.randint(1, 8, rows), unit='D')
        return df

    def generate_test_results(self, samples_df: pd.DataFrame) -> pd.DataFrame:
        results = []
        for _, sample in samples_df.iterrows():
            st = sample['SAMPLE_TYPE']
            if st == '原煤':
                ad, qgr = np.random.uniform(15, 35), np.random.uniform(22, 28)
            elif st == '精煤':
                ad, qgr = np.random.uniform(6, 12), np.random.uniform(28, 32)
            elif st == '中煤':
                ad, qgr = np.random.uniform(20, 40), np.random.uniform(18, 24)
            elif st == '矸石':
                ad, qgr = np.random.uniform(50, 80), np.random.uniform(8, 14)
            else:
                ad, qgr = np.random.uniform(8, 18), np.random.uniform(26, 30)

            results.append({
                'SAMPLE_ID': sample['SAMPLE_ID'],
                'AD': round(ad, 2),
                'VD': round(np.random.uniform(15, 40), 2),
                'FC': round(100 - ad - np.random.uniform(15, 40) * 0.9, 2),
                'QGR_AD': round(qgr, 2),
                '全水分Mt': round(np.random.uniform(5, 15), 2),
                '全硫St': round(np.random.uniform(0.3, 2.5), 2),
                'Mar': round(np.random.uniform(8, 20), 2),
            })
        return pd.DataFrame(results)
