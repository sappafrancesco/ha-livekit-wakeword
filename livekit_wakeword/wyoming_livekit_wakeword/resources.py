from importlib.resources import files
from pathlib import Path
from typing import Dict


def get_bundled_models_dir() -> Path:
    return Path(str(files("wyoming_livekit_wakeword") / "models"))


def scan_bundled_models() -> Dict[str, Path]:
    return {path.stem: path for path in get_bundled_models_dir().glob("*.onnx")}
