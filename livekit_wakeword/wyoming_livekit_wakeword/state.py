from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from .resources import get_default_model_path


@dataclass
class State:
    custom_models: Dict[str, Path] = field(default_factory=dict)
    default_model_path: Path = field(default_factory=get_default_model_path)
