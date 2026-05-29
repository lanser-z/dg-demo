# src/dg_simulator/pi_incremental.py
"""
PI-System 时序数据增量生成器
模式：append（持续追加）

每天每标签：86400 / 30 = 2880 个数据点
5个矿井 × 5个工作面 × 6个传感器 = 150 个标签
每天总计：150 × 2880 = 432,000 条

但实际模拟中，我们采样生成（保留骨架，省略海量）
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .incremental_base import IncrementalGenerator

# 矿井-工作面-传感器拓扑
TAG_HIERARCHY = {
    'MINE_001': {
        'FACE_A1': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
        'FACE_A2': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
        'FACE_B1': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
    },
    'MINE_002': {
        'FACE_A1': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
        'FACE_B1': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
        'FACE_B2': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
    },
    'MINE_003': {
        'FACE_C1': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
        'FACE_C2': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
    },
    'MINE_004': {
        'FACE_D1': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
        'FACE_D2': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
        'FACE_D3': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
    },
    'MINE_005': {
        'FACE_E1': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
        'FACE_E2': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
    },
}

UNITS = {
    'WAGAS': '%',
    'TEMP': '℃',
    'CO': 'ppm',
    'CO2': 'ppm',
    'PRESS': 'kPa',
    'FAN_SPEED': 'rpm',
}


class PIIncrementalGenerator(IncrementalGenerator):

    def __init__(self, config: dict, output_base: str):
        super().__init__(config, output_base)
        # 构建标签列表
        self.tags = []
        for mine, faces in TAG_HIERARCHY.items():
            for face, sensors in faces.items():
                for sensor in sensors:
                    self.tags.append({
                        'tag': f'{mine}_{face}_{sensor}',
                        'mine': mine,
                        'face': face,
                        'sensor': sensor,
                        'unit': UNITS[sensor],
                    })

        # 模拟设备基线（用于生成正常波动范围内的值）
        self.baselines = self._init_baselines()

    def _init_baselines(self) -> dict:
        """初始化各传感器基线"""
        baselines = {}
        for tag in self.tags:
            sensor = tag['sensor']
            if sensor == 'WAGAS':
                baselines[tag['tag']] = 0.35 + np.random.uniform(-0.1, 0.1)
            elif sensor == 'TEMP':
                baselines[tag['tag']] = 22 + np.random.uniform(-2, 2)
            elif sensor == 'CO':
                baselines[tag['tag']] = 5 + np.random.uniform(0, 3)
            elif sensor == 'CO2':
                baselines[tag['tag']] = 400 + np.random.uniform(-30, 30)
            elif sensor == 'PRESS':
                baselines[tag['tag']] = 101.325 + np.random.uniform(-1, 1)
            elif sensor == 'FAN_SPEED':
                baselines[tag['tag']] = 1450 + np.random.uniform(-50, 50)
        return baselines

    def generate(self, date_str: str) -> dict:
        """生成某一天的PI时序数据"""
        date = datetime.strptime(date_str, "%Y-%m-%d")
        metas = []

        # 生成整天数据（采样策略：每5分钟一个点，而非30秒）
        # 每天每个标签：288点（5分钟间隔）
        # 150个标签 × 288点 = 43,200条/天
        interval_minutes = 5
        points_per_day = 1440 // interval_minutes  # 288

        records = []
        for tag in self.tags:
            for point_idx in range(points_per_day):
                minute = point_idx * interval_minutes
                timestamp = date + timedelta(minutes=minute)

                value = self._generate_value(tag['tag'], tag['sensor'], timestamp)

                records.append({
                    'tag': tag['tag'],
                    'timestamp': timestamp.isoformat(),
                    'value': round(value, 3),
                    'status': 0 if value is not None else -1,
                    'mine': tag['mine'],
                    'face': tag['face'],
                    'sensor': tag['sensor'],
                    'unit': tag['unit'],
                })

        df = pd.DataFrame(records)

        # 注入质量问题（0.5%缺失，模拟设备掉线）
        df = self._add_pi_quality_issues(df)

        meta = self.write_parquet(df, 'tags', date_str, 'pi_system')
        if meta:
            metas.append(meta)

        return {'date': date_str, 'records': metas}

    def _generate_value(self, tag: str, sensor: str, timestamp: datetime) -> float:
        """根据传感器类型和时间生成值"""
        hour = timestamp.hour
        minute = timestamp.minute

        # 时间因子：白天生产高峰期值略高
        is_working_hour = 8 <= hour <= 18
        is_night = hour < 6 or hour > 22

        base = self.baselines[tag]

        if sensor == 'WAGAS':
            # 瓦斯：白天微升，夜间略降，有周期性
            time_factor = 0.02 if is_working_hour else (-0.01 if is_night else 0)
            noise = self.rng.normal(0, 0.02)
            value = base + time_factor + noise
            # 偶尔异常波动（1%概率）
            if self.rng.random() < 0.01:
                value *= np.random.choice([1.5, 2.0, 3.0])

        elif sensor == 'TEMP':
            # 温度：白天高于夜间，有设备发热
            time_factor = 3 if is_working_hour else (-2 if is_night else 0)
            noise = self.rng.normal(0, 0.5)
            value = base + time_factor + noise

        elif sensor == 'CO':
            # 一氧化碳：生产时略高，指数分布模拟
            time_factor = 2 if is_working_hour else 0
            noise = self.rng.exponential(1.5)
            value = max(0, base + time_factor + noise)
            if self.rng.random() < 0.01:
                value *= 5  # 异常突升

        elif sensor == 'CO2':
            # 二氧化碳：与通风效果相关
            noise = self.rng.normal(0, 15)
            value = base + noise

        elif sensor == 'PRESS':
            # 气压：相对稳定，小幅波动
            noise = self.rng.normal(0, 0.3)
            value = base + noise

        elif sensor == 'FAN_SPEED':
            # 风机转速：稳定在额定值附近
            noise = self.rng.normal(0, 20)
            value = base + noise
            # 偶尔调速（5%概率）
            if self.rng.random() < 0.05:
                value *= np.random.choice([0.9, 1.1])

        return max(0, value)

    def _add_pi_quality_issues(self, df: pd.DataFrame) -> pd.DataFrame:
        """PI系统特有质量问题：设备掉线、数据缺失"""
        # 0.5% 整体缺失
        missing_mask = self.rng.random(len(df)) < 0.005
        df.loc[missing_mask, 'value'] = None
        df.loc[missing_mask, 'status'] = -1

        # 1% 坏点（极值）
        bad_mask = self.rng.random(len(df)) < 0.01
        df.loc[bad_mask, 'value'] = 99999
        df.loc[bad_mask, 'status'] = -2

        return df
