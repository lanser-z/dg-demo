# src/dg_simulator/scada_simulator.py
"""
SCADA 实时流数据模拟器

模拟通过 Kafka/RabbitMQ 推送的实时点位数据
每秒推送一次，包含设备状态、报警、确认等事件

实际煤炭SCADA点位示例：
  - 皮带机状态：1=运行 2=停止 3=故障
  - 排水泵状态：0=停止 1=运行 2=故障 3=备用
  - 提升机状态：0=到位 1=上行 2=下行 3=急停
"""
import json
import random
import threading
import time
from datetime import datetime
from typing import Callable, Optional


# SCADA点位定义
SCADA_POINTS = {
    # 皮带运输系统
    'BELT_001_SPEED': {'type': 'float', 'unit': 'm/s', 'range': (0, 5), 'alarm': 4.5},
    'BELT_001_STATUS': {'type': 'int', 'unit': '', 'range': (1, 3), 'alarm': 3},
    'BELT_002_SPEED': {'type': 'float', 'unit': 'm/s', 'range': (0, 5), 'alarm': 4.5},
    'BELT_002_STATUS': {'type': 'int', 'unit': '', 'range': (1, 3), 'alarm': 3},

    # 排水系统
    'PUMP_001_STATUS': {'type': 'int', 'unit': '', 'range': (0, 3), 'alarm': 2},
    'PUMP_001_FLOW': {'type': 'float', 'unit': 'm³/h', 'range': (0, 200), 'alarm': 180},
    'PUMP_001_PRESSURE': {'type': 'float', 'unit': 'MPa', 'range': (0, 2), 'alarm': 1.8},
    'PUMP_002_STATUS': {'type': 'int', 'unit': '', 'range': (0, 3), 'alarm': 2},
    'PUMP_002_FLOW': {'type': 'float', 'unit': 'm³/h', 'range': (0, 200), 'alarm': 180},

    # 通风系统
    'FAN_001_SPEED': {'type': 'float', 'unit': 'rpm', 'range': (0, 1500), 'alarm': 1450},
    'FAN_001_TEMP': {'type': 'float', 'unit': '℃', 'range': (0, 80), 'alarm': 70},
    'FAN_001_STATUS': {'type': 'int', 'unit': '', 'range': (0, 2), 'alarm': 2},
    'FAN_002_SPEED': {'type': 'float', 'unit': 'rpm', 'range': (0, 1500), 'alarm': 1450},

    # 提升系统
    'HOIST_001_POSITION': {'type': 'float', 'unit': 'm', 'range': (0, 500), 'alarm': None},
    'HOIST_001_SPEED': {'type': 'float', 'unit': 'm/s', 'range': (0, 10), 'alarm': 9},
    'HOIST_001_STATUS': {'type': 'int', 'unit': '', 'range': (0, 3), 'alarm': 3},
    'HOIST_001_LOAD': {'type': 'float', 'unit': 't', 'range': (0, 20), 'alarm': 18},

    # 采煤系统
    'SHIELD_001_PRESSURE': {'type': 'float', 'unit': 'MPa', 'range': (0, 50), 'alarm': 45},
    'SHIELD_002_PRESSURE': {'type': 'float', 'unit': 'MPa', 'range': (0, 50), 'alarm': 45},
    'MINER_001_STATUS': {'type': 'int', 'unit': '', 'range': (0, 4), 'alarm': None},
    'MINER_001_SPEED': {'type': 'float', 'unit': 'm/min', 'range': (0, 10), 'alarm': None},

    # 环境监测（冗余PI，但SCADA更强调报警）
    'CH4_001_LEVEL': {'type': 'float', 'unit': '%', 'range': (0, 10), 'alarm': 0.8},
    'CO_001_LEVEL': {'type': 'float', 'unit': 'ppm', 'range': (0, 100), 'alarm': 24},
    'TEMP_001_LEVEL': {'type': 'float', 'unit': '℃', 'range': (0, 50), 'alarm': 35},
}


class SCADASimulator:
    """SCADA实时流模拟器"""

    def __init__(self, on_message: Optional[Callable] = None, interval_seconds: float = 1.0):
        self.on_message = on_message  # 回调函数，接收 (timestamp, point_name, value)
        self.interval = interval_seconds
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # 当前设备状态（用于状态机模拟）
        self.current_states = {}
        self._init_states()

    def _init_states(self):
        """初始化设备状态"""
        for point, cfg in SCADA_POINTS.items():
            if cfg['type'] == 'int':
                self.current_states[point] = cfg['range'][0] + 1  # 默认"运行"状态
            else:
                self.current_states[point] = (cfg['range'][0] + cfg['range'][1]) / 2

    def start(self, duration_seconds: Optional[int] = None):
        """启动模拟器

        Args:
            duration_seconds: 运行时长，None=持续运行直到stop()
        """
        self.running = True

        def run():
            start_time = time.time()
            while self.running:
                self._push_all_points()

                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    self.running = False
                    break

                time.sleep(self.interval)

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

        print(f"[SCADA Simulator] 启动，每 {self.interval}s 推送一次，共 {len(SCADA_POINTS)} 个点位")

    def stop(self):
        """停止模拟器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("[SCADA Simulator] 已停止")

    def _push_all_points(self):
        """推送所有点位一次"""
        timestamp = datetime.now().isoformat()

        for point, cfg in SCADA_POINTS.items():
            value = self._generate_value(point, cfg)
            self.current_states[point] = value

            # 构造消息
            msg = {
                'timestamp': timestamp,
                'point': point,
                'value': round(value, 3) if isinstance(value, float) else value,
                'unit': cfg['unit'],
                'status': self._get_status(value, cfg),
            }

            if self.on_message:
                self.on_message(timestamp, point, msg)

    def _generate_value(self, point: str, cfg: dict) -> float:
        """根据点位类型生成值（含状态机逻辑）"""
        r = cfg['range']
        current = self.current_states.get(point, r[0])

        if cfg['type'] == 'int':
            # 整型通常是状态机，90%概率保持原状态
            if random.random() < 0.9:
                return current
            else:
                # 10%概率切换状态
                states = list(range(r[0], r[1] + 1))
                return random.choice([s for s in states if s != current])

        else:
            # 浮点型带随机波动
            if 'SPEED' in point or 'FLOW' in point:
                # 期望值围绕基准波动
                base = (r[0] + r[1]) / 2
                delta = (r[1] - r[0]) * 0.1
                value = base + random.gauss(0, delta)
            elif 'TEMP' in point or 'PRESSURE' in point:
                # 缓慢漂移
                value = current + random.gauss(0, 0.5)
            elif 'LEVEL' in point or 'LOAD' in point:
                # 随机游走
                value = current + random.gauss(0, r[1] * 0.02)
            else:
                value = current + random.gauss(0, (r[1] - r[0]) * 0.05)

            return max(r[0], min(r[1], value))

    def _get_status(self, value: float, cfg: dict) -> int:
        """判断点位状态：0=正常 1=预警 2=报警"""
        alarm = cfg.get('alarm')
        if alarm is None:
            return 0

        if isinstance(value, (int, float)):
            if value >= alarm * 1.2:  # 20%超限 = 报警
                return 2
            elif value >= alarm:  # 达到报警阈值 = 预警
                return 1
        return 0


# 简单测试：打印到控制台
def test_console():
    def printer(timestamp, point, msg):
        if msg['status'] > 0:
            status_label = {1: '⚠️预警', 2: '🚨报警'}[msg['status']]
            print(f"{timestamp} [{status_label}] {point}={msg['value']}{msg['unit']}")

    sim = SCADASimulator(on_message=printer, interval_seconds=2)
    sim.start()
    time.sleep(10)
    sim.stop()


if __name__ == '__main__':
    test_console()
