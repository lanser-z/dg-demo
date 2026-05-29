# src/dg_simulator/oa_incremental.py
"""
OA 系统增量生成器
模式：append（流程数据）

每天增量估算：
  - DOC_FLOW: ~500-1000 条流程
  - CONTRACT: ~30-80 条合同
  - MEETING: ~20-50 条会议纪要
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .incremental_base import IncrementalGenerator
import random


class OAIncrementalGenerator(IncrementalGenerator):

    def __init__(self, config: dict, output_base: str):
        super().__init__(config, output_base)
        self.doc_no_counter = 100000
        self.flow_id_counter = 500000

    def generate(self, date_str: str) -> dict:
        """生成某一天的OA增量数据"""
        date = datetime.strptime(date_str, "%Y-%m-%d")
        metas = []

        # 1. 流程数据
        flow_count = int(np.random.normal(800, 150))
        flow_count = max(100, min(flow_count, 2000))
        doc_flow = self._generate_doc_flow(date, flow_count)
        doc_flow = self.add_quality_issues(doc_flow)
        meta = self.write_parquet(doc_flow, 'DOC_FLOW', date_str, 'oa')
        if meta:
            metas.append(meta)

        # 2. 合同数据（较少）
        contract_count = int(np.random.normal(50, 20))
        contract_count = max(5, min(contract_count, 200))
        contract = self._generate_contract(date, contract_count)
        meta = self.write_parquet(contract, 'CONTRACT', date_str, 'oa')
        if meta:
            metas.append(meta)

        # 3. 会议纪要
        meeting_count = int(np.random.normal(30, 10))
        meeting_count = max(5, min(meeting_count, 100))
        meeting = self._generate_meeting(date, meeting_count)
        meta = self.write_parquet(meeting, 'MEETING', date_str, 'oa')
        if meta:
            metas.append(meta)

        return {'date': date_str, 'records': metas}

    def _generate_doc_flow(self, date: datetime, rows: int) -> pd.DataFrame:
        """生成公文流程"""
        flow_ids = [f'FL{self.flow_id_counter + i:08d}' for i in range(rows)]
        self.flow_id_counter += rows

        doc_nos = [f'DOC{date.year}{self.doc_no_counter + i:06d}' for i in range(rows)]
        self.doc_no_counter += rows

        # 流程类型分布
        flow_types = np.random.choice(
            ['请假', '报销', '采购申请', '付款申请', '用车申请', '出差', '公文审批', '印章使用'],
            rows,
            p=[0.25, 0.20, 0.15, 0.15, 0.08, 0.07, 0.05, 0.05]
        )

        # 发起人
        initiators = np.random.choice(
            ['张明', '李华', '王强', '刘洋', '陈静', '赵磊', '周涛', '吴霞', '郑伟', '孙杰'],
            rows
        )

        # 部门
        depts = np.random.choice(
            ['生产部', '安全部', '财务部', '采购部', '综合办', '技术部', '销售部', '机电队'],
            rows
        )

        # 申请日期
        apply_date_offsets = [random.randint(0, 4) for _ in range(rows)]
        apply_dates = [date - timedelta(days=d) for d in apply_date_offsets]

        # 状态分布
        statuses = np.random.choice(
            ['已完成', '审批中', '已驳回', '已撤销', '已完成', '已完成'],
            rows,
            p=[0.4, 0.3, 0.1, 0.05, 0.1, 0.05]
        )

        df = pd.DataFrame({
            'FLOW_ID': flow_ids,
            'DOC_NO': doc_nos,
            'FLOW_TYPE': flow_types,
            'INITIATOR': initiators,
            'INITIATOR_DEPT': depts,
            'APPLY_DATE': [d.strftime('%Y-%m-%d') for d in apply_dates],
            'CURRENT_NODE': [self._get_current_node(st) for st in statuses],
            'STATUS': statuses,
            'APPROVER': np.random.choice(['李总', '王总', '张总', '刘总', '陈总', '赵总', '周总'], rows),
            'APPROVE_DATE': date.strftime('%Y-%m-%d'),
            'REMARK': [''] * rows,
        })

        # 金额字段（仅部分流程有）
        has_amount = np.random.random(rows) < 0.4
        df['AMOUNT'] = np.where(has_amount, np.random.uniform(100, 50000, rows).round(2), None)

        return df

    def _get_current_node(self, status: str) -> str:
        if status == '已完成':
            return '归档'
        elif status == '审批中':
            return np.random.choice(['部门负责人', '分管领导', '财务复核', '总经理'])
        elif status == '已驳回':
            return '已驳回'
        elif status == '已撤销':
            return '已撤销'
        return '未知'

    def _generate_contract(self, date: datetime, rows: int) -> pd.DataFrame:
        """生成合同数据"""
        contract_ids = [f'CT{date.year}{np.random.randint(10000, 99999):05d}' for _ in range(rows)]

        # 合同类型
        contract_types = np.random.choice(
            ['采购合同', '销售合同', '服务合同', '租赁合同', '施工合同', '运输合同'],
            rows,
            p=[0.3, 0.25, 0.15, 0.1, 0.1, 0.1]
        )

        # 签约方
        counterparties = np.random.choice([
            '山西焦化能源集团', '内蒙古伊泰煤炭', '陕西延长石油',
            '中煤能源销售公司', '国电华北电力', '华能山西能源',
            '大唐山西发电', '国电投山西分公司', '河南能源化工集团',
            '山东能源煤炭营销公司', '冀中能源股份', '开滦集团',
        ], rows)

        df = pd.DataFrame({
            'CONTRACT_ID': contract_ids,
            'CONTRACT_NAME': [f'{ct[:2]}{np.random.choice(["标的物", "服务", "物资", "工程"])}{np.random.randint(100, 999)}号' for ct in contract_types],
            'CONTRACT_TYPE': contract_types,
            'COUNTERPARTY': counterparties,
            'SIGN_DATE': (date - pd.to_timedelta(np.random.randint(1, 30), unit='D')).strftime('%Y-%m-%d'),
            'EFFECTIVE_DATE': date.strftime('%Y-%m-%d'),
            'EXPIRY_DATE': (date + pd.to_timedelta(np.random.randint(30, 730), unit='D')).strftime('%Y-%m-%d'),
            'AMOUNT': np.round(np.random.uniform(50000, 50000000, rows), 2),
            'CURRENCY': 'CNY',
            'PAYMENT_TERM': np.random.choice(['预付30%', '月结30天', '月结60天', '到货付款'], rows),
            'STATUS': np.random.choice(['执行中', '执行中', '执行中', '已终止', '已到期'], rows, p=[0.4, 0.3, 0.15, 0.1, 0.05]),
            'CONTRACT_MANAGER': np.random.choice(['张明', '李华', '王强', '刘洋', '陈静'], rows),
            'DEPT': np.random.choice(['采购部', '销售部', '综合办', '生产部', '安全部'], rows),
        })

        return df

    def _generate_meeting(self, date: datetime, rows: int) -> pd.DataFrame:
        """生成会议纪要"""
        df = pd.DataFrame({
            'MEETING_ID': [f'MT{date.year}{i:05d}' for i in range(1, rows + 1)],
            'MEETING_DATE': date.strftime('%Y-%m-%d'),
            'MEETING_TYPE': np.random.choice(['安全生产例会', '生产调度会', '技术研讨会', '班前会', '专题会'], rows),
            'VENUE': np.random.choice(['三楼会议室', '五楼会议室', '调度室', '视频会议', '现场'], rows),
            'CHAIRMAN': np.random.choice(['矿长', '生产副矿长', '总工程师', '安全矿长', '调度主任'], rows),
            'RECORDER': np.random.choice(['王秘书', '李秘书', '张秘书', '刘秘书'], rows),
            'ATTENDEES': [','.join(np.random.choice(['张明', '李华', '王强', '刘洋', '陈静', '赵磊', '周涛'],
                                                   size=np.random.randint(3, 8))) for _ in range(rows)],
            'SUMMARY': [f'会议讨论了{np.random.choice(["安全生产", "设备维护", "产量计划", "人员安排", "隐患整改"])}相关事项。'] * rows,
            'DECISIONS': [f'决定：{np.random.choice(["加强巡检", "增加检修频次", "调整作业计划", "完善应急预案"])}。'] * rows,
            'FOLLOW_UP': [f'责任部门：{np.random.choice(["生产部", "安全部", "机电队", "综合办"])}，完成时间：{np.random.randint(1, 30)}日内。'] * rows,
        })

        return df
