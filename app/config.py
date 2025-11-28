import yaml
from pathlib import Path

def load_config(path: str = 'config.yaml'):
    cfg_file = Path(path)
    if not cfg_file.exists():
        raise FileNotFoundError('config.yaml not found. Copy config.example.yaml to config.yaml and edit it.')
    with open(cfg_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
