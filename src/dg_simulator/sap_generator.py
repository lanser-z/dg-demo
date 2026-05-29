# src/dg_simulator/sap_generator.py
"""
SAP-ERP 数据生成器（历史数据）
"""
import pandas as pd
import numpy as np
from .base_generator import BaseGenerator

COMPANY_NAMES = [
    "内蒙古伊泰煤炭股份有限公司", "山西焦化能源集团", "陕西煤业化工集团",
    "中煤能源集团有限公司", "山东能源集团有限公司", "河南能源化工集团",
    "开滦能源化工股份有限公司", "冀中能源集团", "大同煤矿集团"
]
CITIES = ["呼和浩特", "太原", "西安", "北京", "济南", "郑州", "唐山", "邢台", "大同"]


class SAPGenerator(BaseGenerator):

    def generate_kna1(self, rows: int = 15000) -> pd.DataFrame:
        df = pd.DataFrame({
            'KUNNR': [f'{i:06d}' for i in range(100001, 100001 + rows)],
            'NAME1': np.random.choice(COMPANY_NAMES, rows),
            'NAME2': [f'分公司{i%50}' for i in range(rows)],
            'ORT01': np.random.choice(CITIES, rows),
            'STCD1': [f'9{random.randint(110000,159999)}{random.randint(1000,9999)}{random.randint(100,999)}' for _ in range(rows)],
            'STCD2': [f'{random.randint(110000,659900)}{random.randint(100000,999999)}' for _ in range(rows)],
            'TELF1': [f'1{3-9}{random.randint(100000000,999999999)}' for _ in range(rows)],
            'ERDAT': self.generate_dates('2021-01-01', '2024-01-01', rows),
        })
        return df

    def generate_vbak(self, rows: int = 2800000, kna1_df: pd.DataFrame = None) -> pd.DataFrame:
        df = pd.DataFrame({
            'VBELN': [f'{i:010d}' for i in range(1000000001, 1000000001 + rows)],
            'ERDAT': self.generate_dates('2021-01-01', '2024-01-01', rows),
            'ERZET': [f'{h:02d}{m:02d}{s:02d}' for h,m,s in
                       zip(np.random.randint(0,24,rows), np.random.randint(0,60,rows), np.random.randint(0,60,rows))],
            'KUNNR': np.random.choice(kna1_df['KUNNR'], rows) if kna1_df is not None
                     else [f'{random.randint(100001,115000):06d}' for _ in range(rows)],
            'NETWR': np.round(np.random.uniform(1000, 500000, rows), 2),
            'WAERK': 'CNY',
            'BZIRK': np.random.choice(['D001','D002','D003','D004','D005'], rows),
            'VKORG': np.random.choice(['CN01','CN02','CN03'], rows),
        })
        return df

    def generate_vbap(self, rows: int = 7200000, vbak_df: pd.DataFrame = None) -> pd.DataFrame:
        if vbak_df is None:
            vbak_df = self.generate_vbak(100000)

        df = pd.DataFrame({
            'VBELN': np.random.choice(vbak_df['VBELN'], rows),
            'POSNR': [f'{i:06d}' for i in np.random.randint(1, 100, rows)],
            'MATNR': [f'{random.randint(1000000,9999999)}' for _ in range(rows)],
            'KWMENG': np.round(np.random.uniform(1, 500, rows), 3),
            'VRKME': 'TO',
            'NETWR': np.round(np.random.uniform(500, 100000, rows), 2),
            'CHARG': [f'L{random.randint(1000,9999)}' for _ in range(rows)],
        })
        df.loc[::1000, 'VBELN'] = df.loc[::1000, 'VBELN'].shift(1)
        return df
