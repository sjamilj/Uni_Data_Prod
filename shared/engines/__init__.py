"""Course HTML clean engine registry."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from engines.generic import GenericCourseHtmlEngine
from engines.utopian import UtopianCourseHtmlEngine
from uni_paths import resolve_code_dir

_BUILTIN_ENGINES = {
    "generic": GenericCourseHtmlEngine,
    "utopian": UtopianCourseHtmlEngine,
}


def _load_plugin_module(code_dir: Path) -> ModuleType | None:
    path = resolve_code_dir(code_dir) / "course_html_builder.py"
    if not path.is_file():
        return None
    module_name = f"uni_course_html_builder_{abs(hash(path.resolve()))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    uni_code = str(path.parent)
    if uni_code not in sys.path:
        sys.path.insert(0, uni_code)
    spec.loader.exec_module(module)
    return module


def get_course_html_engine(engine_name: str, code_dir: Path):
    """Resolve built-in engine or optional course_html_builder.py plugin."""
    name = (engine_name or "generic").strip().lower() or "generic"
    if name == "plugin":
        module = _load_plugin_module(code_dir)
        if module is None:
            raise ValueError(
                "COURSE_CLEAN_ENGINE=plugin requires code/course_html_builder.py"
            )
        engine = getattr(module, "CourseHtmlEngine", None) or getattr(
            module, "course_html_engine", None
        )
        if engine is None:
            raise ValueError(
                "course_html_builder.py must define CourseHtmlEngine or course_html_engine"
            )
        return engine() if isinstance(engine, type) else engine

    if name == "auto":
        module = _load_plugin_module(code_dir)
        if module is not None:
            return get_course_html_engine("plugin", code_dir)
        return GenericCourseHtmlEngine

    try:
        return _BUILTIN_ENGINES[name]
    except KeyError as exc:
        known = ", ".join(sorted(_BUILTIN_ENGINES))
        raise ValueError(
            f"Unknown COURSE_CLEAN_ENGINE={name!r} (expected one of: {known}, plugin, auto)"
        ) from exc
