from importlib.resources import files
from pathlib import Path


def get_default_model_path() -> Path:
    return Path(str(files("wyoming_livekit_wakeword") / "models" / "hey_livekit.onnx"))
