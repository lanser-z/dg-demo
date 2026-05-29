# src/dg_simulator/sap_incremental.py
"""
SAP-ERP 增量数据生成器
模式：upsert（订单可能修改）、append（发货过账）

每天增量估算：
  - VBAK: ~3000-5000 条新订单
  - VBAP: ~8000-12000 条行项目
  - LIKP(交货单): ~2000 条
  - LIPS(交货行): ~6000 条
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .incremental_base import IncrementalGenerator

# 从历史生成器继承姓氏/公司数据
COMPANY_NAMES = [
    "内蒙古伊泰煤炭股份有限公司", "山西焦化能源集团", "陕西煤业化工集团",
    "中煤能源集团有限公司", "山东能源集团有限公司", "河南能源化工集团",
]

CITIES = ["呼和浩特", "太原", "西安", "北京", "济南", "郑州", "唐山", "邢台", "大同"]


class SAPIncrementalGenerator(IncrementalGenerator):

    def __init__(self, config: dict, output_base: str):
        super().__init__(config, output_base)
        self.start_vbeln = 1000000001  # 订单号起点（接续历史）
        self.issue_rate = config.get('issue_rate', 0.02)

    def generate(self, date_str: str) -> dict:
        """生成某一天的SAP增量数据"""
        date = datetime.strptime(date_str, "%Y-%m-%d")
        metas = []

        # 1. VBAK 销售订单头（每天 3000-5000 条）
        vbak_count = int(np.random.normal(4000, 800))
        vbak_count = max(100, min(vbak_count, 8000))  # 限制范围
        vbak = self._generate_vbak(date, vbak_count)
        meta = self.write_parquet(vbak, 'VBAK', date_str, 'sap_erp')
        if meta:
            metas.append(meta)

        # 2. VBAP 销售订单行（每订单约 2-3 行）
        vbap_count = int(vbak_count * np.random.normal(2.5, 0.5))
        vbap = self._generate_vbap(date, vbap_count, vbak)
        vbap = self.add_quality_issues(vbap)
        meta = self.write_parquet(vbap, 'VBAP', date_str, 'sap_erp')
        if meta:
            metas.append(meta)

        # 3. LIKP 交货单头（订单的 60-70% 会创建交货）
        likp_count = int(vbak_count * np.random.uniform(0.6, 0.7))
        likp = self._generate_likp(date, likp_count, vbak)
        meta = self.write_parquet(likp, 'LIKP', date_str, 'sap_erp')
        if meta:
            metas.append(meta)

        # 4. LIPS 交货行
        lips_count = int(likp_count * np.random.normal(2.2, 0.5))
        lips = self._generate_lips(likp_count, lips_count)
        lips = self.add_quality_issues(lips)
        meta = self.write_parquet(lips, 'LIPS', date_str, 'sap_erp')
        if meta:
            metas.append(meta)

        return {'date': date_str, 'records': metas}

    def _generate_vbak(self, date: datetime, rows: int) -> pd.DataFrame:
        """生成销售订单头"""
        vbeln_start = self.start_vbeln
        self.start_vbeln += rows  # 下一天顺延

        # 订单类型分布
        auart = np.random.choice(
            ['OR', 'ZOR', 'RET'],  # OR=标准订单,ZOR=出口,RET=退货
            size=rows,
            p=[0.78, 0.20, 0.02]
        )

        # 销售区域分布
        bzirk = np.random.choice(['D001', 'D002', 'D003', 'D004', 'D005'], rows)
        vkorg = np.random.choice(['CN01', 'CN02', 'CN03'], rows)
        vtweg = np.random.choice(['10', '20'], rows, p=[0.8, 0.2])
        spart = np.random.choice(['00', '01', '02', '03'], rows, p=[0.6, 0.2, 0.1, 0.1])

        df = pd.DataFrame({
            'VBELN': [f'{vbeln_start + i:010d}' for i in range(rows)],
            'ERDAT': date.strftime('%Y-%m-%d'),
            'ERZET': [f'{h:02d}{m:02d}{s:02d}' for h, m, s in zip(
                np.random.randint(6, 22, rows),
                np.random.randint(0, 60, rows),
                np.random.randint(0, 60, rows)
            )],
            'ERNAM': np.random.choice(['SAPUSER', 'BATCH_JOB', 'ZHANGSAN', 'LIISI', 'WANGWU'], rows),
            'AUART': auart,
            'KUNNR': [f'{np.random.randint(100001, 115000):06d}' for _ in range(rows)],
            'NETWR': np.round(np.random.uniform(1000, 500000, rows), 2),
            'WAERK': 'CNY',
            'BZIRK': bzirk,
            'VKORG': vkorg,
            'VTWEG': vtweg,
            'SPART': spart,
            'BSTNK': [f'PO{np.random.randint(100000, 999999)}' for _ in range(rows)],  # 采购订单引用
            'IHREZ': [f'REF{np.random.randint(10000, 99999)}' for _ in range(rows)],  # 客户参考
            # 状态字段（模拟业务状态流转）
            'FABKL': np.random.choice(['CN01', 'CN02', 'CN03'], rows),  # 工厂
            'LIFSK': np.random.choice(['', '', '', 'C'], rows, p=[0.6, 0.2, 0.15, 0.05]),  # 交货冻结
            'FAKSK': np.random.choice(['', '', 'C'], rows, p=[0.8, 0.15, 0.05]),  # 开票冻结
        })

        # 注入一些异常状态（模拟未清订单）
        df.loc[::50, 'LIFSK'] = 'C'
        df.loc[::100, 'FAKSK'] = 'C'

        return df

    def _generate_vbap(self, date: datetime, rows: int, vbak_df: pd.DataFrame) -> pd.DataFrame:
        """生成销售订单行"""
        # 按订单号分组，每订单 1-5 行
        vbelns = np.random.choice(vbak_df['VBELN'], rows)

        # 产品组（煤炭相关）
        matnrs = np.random.choice([
            '501010001', '501010002', '501010003',  # 原煤
            '501020001', '501020002',              # 精煤
            '501030001',                            # 洗煤
            '501040001',                            # 焦炭
        ], rows, p=[0.40, 0.15, 0.10, 0.15, 0.10, 0.05, 0.05])

        df = pd.DataFrame({
            'VBELN': vbelns,
            'POSNR': [f'{i:06d}' for i in np.random.randint(1, 100, rows)],
            'MATNR': matnrs,
            'KWMENG': np.round(np.random.uniform(10, 5000, rows), 3),
            'VRKME': 'TO',
            'NETWR': np.round(np.random.uniform(500, 100000, rows), 2),
            'WAERK': 'CNY',
            'CHARG': [f'L{np.random.randint(1000, 9999)}' for _ in range(rows)],
            'WERKS': np.random.choice(['CN01', 'CN02', 'CN03'], rows),
            'LGORT': np.random.choice(['FG01', 'FG02', 'FG03', 'RM01'], rows),  # 库存地点
        })

        # 交货日期（订单日期后 7-30 天）
        delivery_delta = np.random.randint(7, 31, rows)
        edatu_dates = [date + timedelta(days=int(d)) for d in delivery_delta]
        df['EDATU'] = [d.strftime('%Y-%m-%d') for d in edatu_dates]

        return df

    def _generate_likp(self, date: datetime, rows: int, vbak_df: pd.DataFrame) -> pd.DataFrame:
        """生成交货单头"""
        vbelns = np.random.choice(vbak_df['VBELN'], rows)
        vbeln_start = int(vbelns[0]) + 50000000  # 交货单号与订单号段区分

        df = pd.DataFrame({
            'VBELN': [f'{vbeln_start + i:010d}' for i in range(rows)],
            'ERDAT': date.strftime('%Y-%m-%d'),
            'ERZET': [f'{h:02d}{m:02d}{s:02d}' for h, m, s in zip(
                np.random.randint(8, 18, rows),
                np.random.randint(0, 60, rows),
                np.random.randint(0, 60, rows)
            )],
            'KUNNR': vbak_df['KUNNR'].iloc[:rows].values,
            'VSTEL': np.random.choice(['DC01', 'DC02', 'DC03'], rows),  # 装运点
            'LIFEX': [f'EX{np.random.randint(100000, 999999)}' for _ in range(rows)],  # 外部交货号
            'WOERK': np.random.choice(['CN01', 'CN02', 'CN03'], rows),
        })

        # 过账日期（滞后几天）
        post_date_delta = np.random.randint(0, 3, rows)
        wadats = [date + timedelta(days=int(d)) for d in post_date_delta]
        df['WADAT'] = [d.strftime('%Y-%m-%d') for d in wadats]
        df['WADAT_IST'] = df['WADAT']  # 实际发货日期初值

        # 状态
        df['KOSTL'] = np.random.choice(['', 'C', 'C', 'C'], rows, p=[0.7, 0.1, 0.1, 0.1])  # C=已过账

        return df

    def _generate_lips(self, likp_count: int, rows: int) -> pd.DataFrame:
        """生成交货单行"""
        vbeln_start = int(np.random.randint(1000000001, 1000001000)) + 50000000
        vbelns = [f'{vbeln_start + i:010d}' for i in range(likp_count)]
        vbelns = np.repeat(vbelns, rows // likp_count + 1)[:rows]

        matnrs = np.random.choice([
            '501010001', '501010002', '501010003',
            '501020001', '501020002',
        ], rows)

        df = pd.DataFrame({
            'VBELN': vbelns,
            'POSNR': [f'{i:06d}' for i in np.random.randint(1, 100, rows)],
            'MATNR': matnrs,
            'LFIMG': np.round(np.random.uniform(10, 5000, rows), 3),  # 交货数量
            'VRKME': 'TO',
            'WERKS': np.random.choice(['CN01', 'CN02', 'CN03'], rows),
            'LGORT': np.random.choice(['FG01', 'FG02', 'FG03'], rows),
        })

        return df
