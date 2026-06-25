"""``rich.table`` stub — see ``tests/stubs/rich/__init__.pyi`` for context."""

from typing import Any

class Table:
    row_count: int

    def __init__(self, *, title: str | None = ..., show_lines: bool = ..., **kwargs: Any) -> None: ...
    def add_column(
        self,
        header: str,
        *,
        width: int | None = ...,
        justify: str | None = ...,
        **kwargs: Any,
    ) -> None: ...
    def add_row(self, *cells: Any, end_section: bool = ...) -> None: ...
