"""
历史数据生成器配置读取
"""
import tomllib
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.toml"


def load_config() -> dict:
    with open(CONFIG_PATH, "rb") as f:
        raw = tomllib.load(f)

    return {
        "scale": raw.get("data_scale", {}),
        "quality": raw.get("data_quality", {}),
    }


def get_scale(key: str, default=None):
    cfg = load_config()
    return cfg.get("scale", {}).get(key, default)


def get_quality(key: str, default=None):
    cfg = load_config()
    return cfg.get("quality", {}).get(key, default)
