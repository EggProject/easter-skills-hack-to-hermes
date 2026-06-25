"""``rich.console`` stub — see ``tests/stubs/rich/__init__.pyi`` for context."""

from typing import Any, Self

class Console:
    def __init__(
        self,
        *,
        file: Any = ...,
        record: bool = ...,
        width: int | None = ...,
        **kwargs: Any,
    ) -> None: ...
    def print(self, *objects: Any, **kwargs: Any) -> None: ...
    def export_text(self, **kwargs: Any) -> str: ...
