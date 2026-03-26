"""Load `agent/app/core/settings.py` without `import app` (avoids name clashes on PYTHONPATH)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "agent/app/core/settings.py"


def load_agent_settings_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "xcode_monorepo_agent_settings",
        _SETTINGS_PATH,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
