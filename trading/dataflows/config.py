"""Global config store — single source of truth for dataflow routing."""

_CONFIG: dict = {}


def set_config(config: dict):
    global _CONFIG
    _CONFIG = config


def get_config() -> dict:
    return _CONFIG
