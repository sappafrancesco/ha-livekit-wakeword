from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from .resources import scan_bundled_models


@dataclass
class State:
    custom_models: Dict[str, Path] = field(default_factory=dict)
    bundled_models: Dict[str, Path] = field(default_factory=scan_bundled_models)

    def resolve_model(self, name: str) -> Path | None:
        return self.custom_models.get(name) or self.bundled_models.get(name)

    def known_names(self):
        return set(self.custom_models) | set(self.bundled_models)
