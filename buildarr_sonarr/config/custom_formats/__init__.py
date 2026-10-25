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
Sonarr plugin custom format settings configuration (Sonarr v4).
"""


from __future__ import annotations

from logging import getLogger
from typing import Any, Dict

from typing_extensions import Self

from ...api import api_get
from ...secrets import SonarrSecrets
from ..types import SonarrConfigBase
from .custom_format import CustomFormat

logger = getLogger(__name__)


class SonarrCustomFormatsSettingsConfig(SonarrConfigBase):
    """
    Custom formats are matched against release titles and media info to score releases
    in quality profiles. Requires Sonarr v4.

    ```yaml
    sonarr:
      settings:
        custom_formats:
          delete_unmanaged: false
          definitions:
            NF:
              trash_id: "d34870697c9db575f17700212167be23"
              default_score: 50
            LATAM:
              default_score: 100
              conditions:
                latam:
                  type: release-title
                  regex: '\\b(LATAM|LATINO)\\b'
    ```
    """

    delete_unmanaged: bool = False
    """
    Automatically delete custom formats not defined in Buildarr.
    """

    definitions: Dict[str, CustomFormat] = {}
    """
    Define custom formats to configure on Sonarr here.
    """

    def uses_trash_metadata(self) -> bool:
        for customformat in self.definitions.values():
            if customformat.uses_trash_metadata():
                return True
        return False

    def _post_init_render(self, secrets: SonarrSecrets) -> None:
        api_condition_schema_dicts = _get_condition_schema_dicts(secrets)
        for customformat_name, customformat in self.definitions.items():
            if customformat.uses_trash_metadata():
                customformat._post_init_render(
                    customformat_name=customformat_name,
                    api_condition_schema_dicts=api_condition_schema_dicts,
                )

    @classmethod
    def from_remote(cls, secrets: SonarrSecrets) -> Self:
        api_condition_schema_dicts = _get_condition_schema_dicts(secrets)
        return cls(
            definitions={
                api_customformat["name"]: CustomFormat._from_remote(
                    api_condition_schema_dicts=api_condition_schema_dicts,
                    api_customformat=api_customformat,
                )
                for api_customformat in api_get(secrets, "/api/v3/customformat")
            },
        )

    def update_remote(
        self,
        tree: str,
        secrets: SonarrSecrets,
        remote: Self,
        check_unmanaged: bool = False,
    ) -> bool:
        changed = False
        api_condition_schema_dicts = _get_condition_schema_dicts(secrets)
        api_customformats: Dict[str, Dict[str, Any]] = {
            api_customformat["name"]: api_customformat
            for api_customformat in api_get(secrets, "/api/v3/customformat")
        }
        for customformat_name, customformat in self.definitions.items():
            customformat_tree = f"{tree}.definitions[{customformat_name!r}]"
            if customformat_name not in remote.definitions:
                customformat._create_remote(
                    tree=customformat_tree,
                    secrets=secrets,
                    api_condition_schema_dicts=api_condition_schema_dicts,
                    customformat_name=customformat_name,
                )
                changed = True
            elif customformat._update_remote(
                tree=customformat_tree,
                secrets=secrets,
                remote=remote.definitions[customformat_name],  # type: ignore[arg-type]
                api_condition_schema_dicts=api_condition_schema_dicts,
                api_customformat=api_customformats[customformat_name],
            ):
                changed = True
        return changed

    def delete_remote(self, tree: str, secrets: SonarrSecrets, remote: Self) -> bool:
        changed = False
        customformat_ids: Dict[str, int] = {
            api_customformat["name"]: api_customformat["id"]
            for api_customformat in api_get(secrets, "/api/v3/customformat")
        }
        for customformat_name, customformat in remote.definitions.items():
            if customformat_name not in self.definitions:
                customformat_tree = f"{tree}.definitions[{customformat_name!r}]"
                if self.delete_unmanaged:
                    logger.info("%s: (...) -> (deleted)", customformat_tree)
                    customformat._delete_remote(
                        secrets=secrets,
                        customformat_id=customformat_ids[customformat_name],
                    )
                    changed = True
                else:
                    logger.debug("%s: (...) (unmanaged)", customformat_tree)
        return changed


def _get_condition_schema_dicts(secrets: SonarrSecrets) -> Dict[str, Dict[str, Any]]:
    return {
        api_schema_dict["implementation"]: api_schema_dict
        for api_schema_dict in api_get(secrets, "/api/v3/customformat/schema")
    }
