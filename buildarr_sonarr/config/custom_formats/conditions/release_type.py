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
Custom format condition for matching based on release type (Sonarr only).
"""


from __future__ import annotations

from typing import Any, Dict, List, Literal, cast

from buildarr.config import RemoteMapEntry
from buildarr.types import NonEmptyStr
from pydantic import validator

from .base import Condition


class ReleaseTypeCondition(Condition):
    # Custom format condition for matching based on release type.

    type: Literal["release-type", "release_type", "releasetype"] = "release-type"
    """
    Buildarr type keywords associated with this condition type.
    """

    release_type: NonEmptyStr
    """
    The release type to match against, as named by your Sonarr instance version.

    Names are parsed into lower case with dashes, e.g. `Season Pack` -> `season-pack`.
    As of Sonarr v4, the release types are `unknown`, `single-episode`,
    `multi-episode` and `season-pack`.
    """

    _implementation: Literal["ReleaseTypeSpecification"] = "ReleaseTypeSpecification"

    @classmethod
    def _release_type_parse(cls, value: str) -> str:
        # Results:
        #   1. Season Pack -> season-pack
        #   2. Multi-Episode -> multi-episode
        #   3. SINGLE_EPISODE -> single-episode
        return value.lower().replace("_", "-").replace(" ", "-")

    @validator("release_type")
    def validate_release_type(cls, value: str) -> str:
        return cls._release_type_parse(value)

    @classmethod
    def _get_remote_map(cls, api_schema_dict: Dict[str, Any]) -> List[RemoteMapEntry]:
        return [
            (
                "release_type",
                "value",
                {
                    "decoder": lambda v: cls._release_type_decode(api_schema_dict, v),
                    "encoder": lambda v: cls._release_type_encode(api_schema_dict, v),
                    "is_field": True,
                },
            ),
        ]

    @classmethod
    def _release_type_decode(cls, api_schema_dict: Dict[str, Any], value: int) -> str:
        field: Dict[str, Any] = next(f for f in api_schema_dict["fields"] if f["name"] == "value")
        select_options = cast(List[Dict[str, Any]], field["selectOptions"])
        for o in select_options:
            option = cast(Dict[str, Any], o)
            option_name = cast(str, option["name"])
            option_value = cast(int, option["value"])
            if option_value == value:
                return cls._release_type_parse(option_name)
        supported_release_types = ", ".join(
            (f"{cls._release_type_parse(o['name'])} ({o['value']})" for o in select_options),
        )
        raise ValueError(
            f"Invalid custom format release type value {value} during decoding"
            f", supported release types are: {supported_release_types}",
        )

    @classmethod
    def _release_type_encode(cls, api_schema_dict: Dict[str, Any], value: str) -> int:
        field: Dict[str, Any] = next(f for f in api_schema_dict["fields"] if f["name"] == "value")
        select_options = cast(List[Dict[str, Any]], field["selectOptions"])
        for o in select_options:
            option = cast(Dict[str, Any], o)
            option_name = cast(str, option["name"])
            option_value = cast(int, option["value"])
            if cls._release_type_parse(option_name) == value:
                return option_value
        supported_release_types = ", ".join(
            cls._release_type_parse(o["name"]) for o in select_options
        )
        raise ValueError(
            f"Invalid or unsupported custom format release type '{value}'"
            f", supported release types are: {supported_release_types}",
        )
