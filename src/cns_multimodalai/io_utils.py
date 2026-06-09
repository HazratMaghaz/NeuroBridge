from pathlib import Path
import json
import pandas as pd

def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def read_csv(path, **kwargs):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return pd.read_csv(path, **kwargs)

def write_json(obj, path):
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return path

def read_json(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8"))

def write_markdown(text, path):
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")
    return path
