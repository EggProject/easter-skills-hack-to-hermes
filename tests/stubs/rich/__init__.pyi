"""``rich`` stub — minimal type declarations for the third-party rich package.

The upstream ``rich`` distribution does not ship ``.pyi`` files, but our
project uses ``rich`` only in the optional rich-table renderer for the
``profiles`` CLI. We declare just the public surface we touch so that
``mypy --strict`` can resolve the imports under ``TYPE_CHECKING``.
"""

from typing import Any

__all__ = ["console", "table"]
