import os
import yaml
from pathlib import Path

# Base workspace directory
ROOT_DIR = Path(__file__).resolve().parents[1]

def load_yaml(filename: str) -> dict:
    config_path = ROOT_DIR / "config" / filename
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# Load configurations
PATHS = load_yaml("paths.yaml")
KAFKA_CFG = load_yaml("kafka.yaml")
FEAST_CFG = load_yaml("feast.yaml")
MLOPS_CFG = load_yaml("mlops.yaml")

# Helper to resolve relative path
def resolve_path(rel_path: str) -> Path:
    p = Path(rel_path)
    if p.is_absolute():
        return p
    return ROOT_DIR / p
