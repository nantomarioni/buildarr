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
Instance settings configuration.
"""


from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import Self

from buildarr.config.resilience import resilient_update_sections

from ..types import RadarrConfigBase
from .custom_formats import RadarrCustomFormatsSettings
from .download_clients import RadarrDownloadClientsSettings
from .general import RadarrGeneralSettings
from .indexers import RadarrIndexersSettings
from .media_management import RadarrMediaManagementSettings
from .metadata import RadarrMetadataSettings
from .notifications import RadarrNotificationsSettings
from .profiles import RadarrProfilesSettings
from .quality import RadarrQualitySettings
from .tags import RadarrTagsSettings
from .ui import RadarrUISettings

if TYPE_CHECKING:
    from ...secrets import RadarrSecrets


class RadarrSettings(RadarrConfigBase):
    media_management: RadarrMediaManagementSettings = (
        RadarrMediaManagementSettings()  # type: ignore[call-arg]
    )
    profiles: RadarrProfilesSettings = RadarrProfilesSettings()
    quality: RadarrQualitySettings = RadarrQualitySettings()
    custom_formats: RadarrCustomFormatsSettings = RadarrCustomFormatsSettings()
    indexers: RadarrIndexersSettings = RadarrIndexersSettings()  # type: ignore[call-arg]
    download_clients: RadarrDownloadClientsSettings = RadarrDownloadClientsSettings()
    # TODO: Enable import lists.
    # lists: RadarrListsSettings = RadarrListsSettings()
    notifications: RadarrNotificationsSettings = RadarrNotificationsSettings()
    metadata: RadarrMetadataSettings = RadarrMetadataSettings()
    tags: RadarrTagsSettings = RadarrTagsSettings()
    general: RadarrGeneralSettings = RadarrGeneralSettings()
    ui: RadarrUISettings = RadarrUISettings()

    def update_remote(
        self,
        tree: str,
        secrets: RadarrSecrets,
        remote: Self,
        check_unmanaged: bool = False,
    ) -> bool:
        # Overload base function to guarantee execution order of section updates.
        # 1. Tags must be created before everything else.
        # 2. Qualities must be updated before quality profiles.
        # 3. Download clients must be created before indexers.
        # Each section is isolated so a failure in one does not block the others.
        return resilient_update_sections(
            [
                (
                    f"{tree}.tags",
                    lambda: self.tags.update_remote(
                        tree=f"{tree}.tags", secrets=secrets, remote=remote.tags,
                        check_unmanaged=check_unmanaged,
                    ),
                ),
                (
                    f"{tree}.quality",
                    lambda: self.quality.update_remote(
                        tree=f"{tree}.quality", secrets=secrets, remote=remote.quality,
                        check_unmanaged=check_unmanaged,
                    ),
                ),
                (
                    f"{tree}.custom_formats",
                    lambda: self.custom_formats.update_remote(
                        tree=f"{tree}.custom_formats", secrets=secrets,
                        remote=remote.custom_formats,
                        check_unmanaged=check_unmanaged,
                    ),
                ),
                (
                    f"{tree}.download_clients",
                    lambda: self.download_clients.update_remote(
                        tree=f"{tree}.download_clients", secrets=secrets,
                        remote=remote.download_clients,
                        check_unmanaged=check_unmanaged,
                    ),
                ),
                (
                    f"{tree}.indexers",
                    lambda: self.indexers.update_remote(
                        tree=f"{tree}.indexers", secrets=secrets, remote=remote.indexers,
                        check_unmanaged=check_unmanaged,
                    ),
                ),
                (
                    f"{tree}.media_management",
                    lambda: self.media_management.update_remote(
                        tree=f"{tree}.media_management", secrets=secrets,
                        remote=remote.media_management,
                        check_unmanaged=check_unmanaged,
                    ),
                ),
                (
                    f"{tree}.profiles",
                    lambda: self.profiles.update_remote(
                        tree=f"{tree}.profiles", secrets=secrets, remote=remote.profiles,
                        check_unmanaged=check_unmanaged,
                    ),
                ),
                # (
                #     f"{tree}.lists",
                #     lambda: self.lists.update_remote(
                #         tree=f"{tree}.lists", secrets=secrets, remote=remote.lists,
                #         check_unmanaged=check_unmanaged,
                #     ),
                # ),
                (
                    f"{tree}.notifications",
                    lambda: self.notifications.update_remote(
                        tree=f"{tree}.notifications", secrets=secrets,
                        remote=remote.notifications,
                        check_unmanaged=check_unmanaged,
                    ),
                ),
                (
                    f"{tree}.metadata",
                    lambda: self.metadata.update_remote(
                        tree=f"{tree}.metadata", secrets=secrets, remote=remote.metadata,
                        check_unmanaged=check_unmanaged,
                    ),
                ),
                (
                    f"{tree}.general",
                    lambda: self.general.update_remote(
                        tree=f"{tree}.general", secrets=secrets, remote=remote.general,
                        check_unmanaged=check_unmanaged,
                    ),
                ),
                (
                    f"{tree}.ui",
                    lambda: self.ui.update_remote(
                        tree=f"{tree}.ui", secrets=secrets, remote=remote.ui,
                        check_unmanaged=check_unmanaged,
                    ),
                ),
            ],
        )

    def delete_remote(self, tree: str, secrets: RadarrSecrets, remote: Self) -> bool:
        # Overload base function to guarantee execution order of section deletions.
        # 1. Indexers must be deleted before download clients.
        # Each section is isolated so a failure in one does not block the others.
        return resilient_update_sections(
            [
                (
                    f"{tree}.profiles",
                    lambda: self.profiles.delete_remote(
                        f"{tree}.profiles", secrets, remote.profiles,
                    ),
                ),
                (
                    f"{tree}.indexers",
                    lambda: self.indexers.delete_remote(
                        f"{tree}.indexers", secrets, remote.indexers,
                    ),
                ),
                (
                    f"{tree}.download_clients",
                    lambda: self.download_clients.delete_remote(
                        tree=f"{tree}.download_clients", secrets=secrets,
                        remote=remote.download_clients,
                    ),
                ),
                (
                    f"{tree}.media_management",
                    lambda: self.media_management.delete_remote(
                        tree=f"{tree}.media_management", secrets=secrets,
                        remote=remote.media_management,
                    ),
                ),
                # (
                #     f"{tree}.lists",
                #     lambda: self.lists.delete_remote(
                #         tree=f"{tree}.lists", secrets=secrets, remote=remote.lists,
                #     ),
                # ),
                (
                    f"{tree}.notifications",
                    lambda: self.notifications.delete_remote(
                        tree=f"{tree}.notifications", secrets=secrets,
                        remote=remote.notifications,
                    ),
                ),
                (
                    f"{tree}.tags",
                    lambda: self.tags.delete_remote(
                        f"{tree}.tags", secrets, remote.tags,
                    ),
                ),
                (
                    f"{tree}.custom_formats",
                    lambda: self.custom_formats.delete_remote(
                        tree=f"{tree}.custom_formats", secrets=secrets,
                        remote=remote.custom_formats,
                    ),
                ),
                (
                    f"{tree}.quality",
                    lambda: self.quality.delete_remote(
                        f"{tree}.quality", secrets, remote.quality,
                    ),
                ),
                (
                    f"{tree}.metadata",
                    lambda: self.metadata.delete_remote(
                        f"{tree}.metadata", secrets, remote.metadata,
                    ),
                ),
                (
                    f"{tree}.general",
                    lambda: self.general.delete_remote(
                        f"{tree}.general", secrets, remote.general,
                    ),
                ),
                (
                    f"{tree}.ui",
                    lambda: self.ui.delete_remote(
                        f"{tree}.ui", secrets, remote.ui,
                    ),
                ),
            ],
        )
