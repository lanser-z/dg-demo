# src/dg_simulator/lims_incremental.py
"""
LIMS 煤质检测增量生成器
模式：append（每天新增检测样本）

每天增量估算：~3000 条检测记录
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .incremental_base import IncrementalGenerator
import random


MINE_CODES = ['M001', 'M002', 'M003', 'M004', 'M005']
MINE_NAMES = {
    'M001': '鄂尔多斯一号煤矿',
    'M002': '榆林李家沟煤矿',
    'M003': '朔州安太堡煤矿',
    'M004': '吕梁庞庞塔煤矿',
    'M005': '晋城寺河煤矿',
}
SAMPLE_TYPES = ['原煤', '精煤', '中煤', '矸石', '洗煤']
SAMPLE_TYPE_PROBS = [0.40, 0.30, 0.10, 0.10, 0.10]

REPORTERS = ['张工', '李工', '王工', '刘工', '陈工', '赵工', '孙工', '周工']


class LIMSIncrementalGenerator(IncrementalGenerator):

    def __init__(self, config: dict, output_base: str):
        super().__init__(config, output_base)
        self.sample_id_counter = 1000000  # 接续历史

    def generate(self, date_str: str) -> dict:
        """生成某一天的LIMS增量数据"""
        date = datetime.strptime(date_str, "%Y-%m-%d")
        metas = []

        # 每天 2000-4000 条检测记录
        rows = int(np.random.normal(3000, 400))
        rows = max(500, min(rows, 6000))

        df = self._generate_samples(date, rows)
        df = self.add_quality_issues(df)

        meta = self.write_parquet(df, 'samples', date_str, 'lims')
        if meta:
            metas.append(meta)

        return {'date': date_str, 'records': metas}

    def _generate_samples(self, date: datetime, rows: int) -> pd.DataFrame:
        """生成检测样本"""
        sample_ids = [f'LM{self.sample_id_counter + i:06d}' for i in range(rows)]
        self.sample_id_counter += rows

        mine_codes = np.random.choice(MINE_CODES, rows)
        sample_types = np.random.choice(SAMPLE_TYPES, rows, p=SAMPLE_TYPE_PROBS)

        # 采样日期（可追溯到前7天）
        sampling_date_offsets = [random.randint(-7, 0) for _ in range(rows)]
        sampling_dates = [date + timedelta(days=d) for d in sampling_date_offsets]

        # 检测日期（采样后1-7天）
        test_date_offsets = [random.randint(1, 8) for _ in range(rows)]
        test_dates = [sampling_dates[i] + timedelta(days=test_date_offsets[i]) for i in range(rows)]

        df = pd.DataFrame({
            'SAMPLE_ID': sample_ids,
            'MINE_CODE': mine_codes,
            'MINE_NAME': [MINE_NAMES.get(m, m) for m in mine_codes],
            'SAMPLE_TYPE': sample_types,
            'SAMPLING_DATE': [d.strftime('%Y-%m-%d') for d in sampling_dates],
            'SAMPLING_POINT': [self._random_sampling_point(m) for m in mine_codes],
            'SAMPLING_PERSON': np.random.choice(['刘师傅', '王师傅', '张师傅', '李师傅', '赵师傅'], rows),
            'TEST_DATE': [d.strftime('%Y-%m-%d') for d in test_dates],
            'TEST_LAB': np.random.choice(['中心化验室', '一分室', '二分室', '三分室'], rows),
            'REPORTER': np.random.choice(REPORTERS, rows),
            'REPORT_STATUS': np.random.choice(['已审核', '已审核', '待审核', '已发布'], rows, p=[0.5, 0.3, 0.1, 0.1]),
        })

        # 关联检测结果
        results = self._generate_test_results(sample_ids, sample_types, mine_codes)
        df = df.merge(results, on='SAMPLE_ID')

        return df

    def _generate_test_results(self, sample_ids, sample_types, mine_codes) -> pd.DataFrame:
        """生成检测指标结果"""
        rows = len(sample_ids)
        results = pd.DataFrame({'SAMPLE_ID': sample_ids})

        # 灰分（Air Dry）- 与煤种相关
        ad_values = []
        for st in sample_types:
            if st == '原煤':
                ad_values.append(np.random.uniform(15, 35))
            elif st == '精煤':
                ad_values.append(np.random.uniform(6, 12))
            elif st == '中煤':
                ad_values.append(np.random.uniform(20, 40))
            elif st == '矸石':
                ad_values.append(np.random.uniform(50, 80))
            else:  # 洗煤
                ad_values.append(np.random.uniform(8, 18))
        results['AD'] = np.round(ad_values, 2)

        # 挥发分
        results['VD'] = np.round(results['AD'] * np.random.uniform(0.8, 1.5, rows) + np.random.uniform(-3, 3), 2)

        # 固定碳
        results['FC'] = np.round(100 - results['AD'] - results['VD'] * 0.9, 2)
        results['FC'] = results['FC'].clip(lower=30)

        # 发热量（MJ/kg）- 与灰分负相关
        results['QGR_AD'] = np.round(np.random.uniform(22, 32, rows) - results['AD'] * 0.1, 2)

        # 全水分
        results['全水分Mt'] = np.round(np.random.uniform(5, 15, rows), 2)

        # 全硫
        results['全硫St'] = np.round(np.random.uniform(0.3, 2.5, rows), 2)

        # 水分（收到基）
        results['Mar'] = np.round(np.random.uniform(8, 20, rows), 2)

        # 磷、砷（微量元素，部分煤种较高）
        results['全磷P'] = np.round(np.random.uniform(0.001, 0.1, rows), 4)
        results['全砷As'] = np.round(np.random.uniform(1, 50, rows), 1)

        # 粒度
        results['粒度'] = np.random.choice(['<50mm', '50-100mm', '>100mm', '混煤'], rows, p=[0.3, 0.3, 0.2, 0.2])

        return results

    def _random_sampling_point(self, mine_code: str) -> str:
        """随机采样点"""
        points = {
            'M001': ['305综采面', '302备采面', '主井皮带', '选煤厂入料口'],
            'M002': ['201工作面', '203工作面', '主井皮带', '装车站'],
            'M003': ['首采区', '二采区', '中央煤仓', '装车点'],
            'M004': ['西翼工作面', '东翼工作面', '筛分车间', '储煤场'],
            'M005': ['南坪隧道', '北坪隧道', '洗煤车间', '产品仓'],
        }
        return np.random.choice(points.get(mine_code, ['主井']))
