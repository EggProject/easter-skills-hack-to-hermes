"""Minimal type stub for the ``yaml`` (PyYAML) package.

This stub provides the surface used by ``_enabled_detection_parse``
(``safe_load`` and the ``YAMLError`` exception) without pulling in the
optional ``types-PyYAML`` distribution. Keep this file minimal — add
declarations only as new consumers appear.
"""

from typing import Any

class YAMLError(Exception): ...

def safe_load(stream: Any) -> Any: ...
