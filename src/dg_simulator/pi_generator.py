# src/dg_simulator/pi_generator.py
"""
PI-System 时序数据生成器（历史数据）
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .base_generator import BaseGenerator

TAG_HIERARCHY = {
    'MINE_001': {
        'FACE_A1': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
        'FACE_A2': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
        'FACE_B1': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
    },
    'MINE_002': {
        'FACE_B2': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
        'FACE_B3': ['WAGAS', 'TEMP', 'CO', 'CO2', 'PRESS', 'FAN_SPEED'],
    }
}


class PIGenerator(BaseGenerator):

    def generate_tags(self) -> list:
        tags = []
        for mine, faces in TAG_HIERARCHY.items():
            for face, sensors in faces.items():
                for sensor in sensors:
                    tags.append({
                        'tag': f'{mine}_{face}_{sensor}',
                        'mine': mine,
                        'face': face,
                        'sensor_type': sensor,
                        'unit': self._get_unit(sensor),
                    })
        return tags

    def generate_timeseries_data(self, tags: list, start: datetime, end: datetime,
                                  interval_seconds: int = 30) -> pd.DataFrame:
        records = []
        current = start
        while current <= end:
            for tag in tags:
                value = self._generate_sensor_value(tag['sensor_type'], current)
                records.append({
                    'tag': tag['tag'],
                    'timestamp': current,
                    'value': value,
                    'status': 0 if value is not None else -1,
                    'mine': tag['mine'],
                    'face': tag['face'],
                })
            current += timedelta(seconds=interval_seconds)
        return pd.DataFrame(records)

    def _generate_sensor_value(self, sensor_type: str, timestamp: datetime) -> float:
        hour = timestamp.hour
        is_night = hour < 6 or hour > 22
        base_values = {
            'WAGAS': 0.35 + self.rng.normal(0, 0.05),
            'TEMP': 22 + (5 if is_night else 0) + self.rng.normal(0, 1),
            'CO': 5 + self.rng.exponential(2),
            'CO2': 400 + self.rng.normal(0, 20),
            'PRESS': 101.325 + self.rng.normal(0, 0.5),
            'FAN_SPEED': 1450 + self.rng.normal(0, 50),
        }
        value = base_values.get(sensor_type, 0)
        if self.rng.random() < 0.05:
            value *= random.choice([1.5, 0.5, 3.0, 0.1])
        return round(max(0, value), 3)

    def _get_unit(self, sensor_type: str) -> str:
        return {'WAGAS': '%', 'TEMP': '℃', 'CO': 'ppm',
                'CO2': 'ppm', 'PRESS': 'kPa', 'FAN_SPEED': 'rpm'}.get(sensor_type, '')
