# Copyright (C) 2023 Callum Dickinson
#
# Buildarr is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
#
# Buildarr is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with Buildarr.
# If not, see <https://www.gnu.org/licenses/>.


"""
Resilient configuration update helpers.

Provides utilities for wrapping section-level update_remote and delete_remote calls
so that a failure in one section (e.g. indexers) does not prevent other sections
(e.g. notifications, download clients) from being processed.

Errors are logged with full tracebacks but do not abort the run. The caller
is responsible for propagating failure status upstream (e.g. via exit code).
"""


from __future__ import annotations

from logging import getLogger
from typing import Any, Callable, List, Tuple

logger = getLogger(__name__)


def resilient_update_sections(
    sections: List[Tuple[str, Callable[[], bool]]],
) -> bool:
    """
    Execute a list of section update/delete callables with per-section error isolation.

    Each entry is a tuple of (section_name, callable_returning_bool).
    If a section raises an exception, it is logged and execution continues
    with the remaining sections.

    Args:
        sections: List of (section_name, callable) tuples. Each callable
                  should return True if the remote was changed, False otherwise.

    Returns:
        True if any section reported a change, False otherwise.
    """
    changed = False
    for section_name, section_fn in sections:
        try:
            if section_fn():
                changed = True
        except Exception:
            logger.error(
                "Failed to process section '%s', skipping."
                " Will retry on next Buildarr run.",
                section_name,
                exc_info=True,
            )
    return changed
