from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Literal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    foreign,
    mapped_column,
    relationship,
)
from typing_extensions import Annotated, ClassVar

from ckan.lib.dictization import table_dictize
from ckan.model.types import make_uuid

from .meta import registry
from .file_owner import FileOwner


def now():
    return datetime.now(timezone.utc)


datetime_tz = Annotated[datetime, mapped_column(sa.DateTime(timezone=True))]
text = Annotated[str, mapped_column(sa.TEXT)]
bigint = Annotated[int, mapped_column(sa.BigInteger)]


@registry.mapped_as_dataclass
class File:
    """Model with file details.

    Args:
        name (str): name shown to users
        location (str): location of the file inside storage
        storage (str): storage that contains the file
        content_type (str): MIMEtype
        size (int): size in bytes
        hash (str): checksum
        created (datetime): date of creation
        storage_data (dict[str, Any]): additional data set by storage
        plugin_data (dict[str, Any]): additional data set by plugins

    Example:
        ```py
        file = File(
            name="file.txt",
            location="relative/path/safe-name.txt",
            storage="default",
            content_type="text/plain",
            size=100,
            hash="abc123",
        )
        ```
    """

    __table__: ClassVar[sa.Table]

    __tablename__ = "file"

    __table_args__ = (
        sa.Index("idx_file_location_in_storage", "storage", "location", unique=True),
    )

    name: Mapped[text]
    location: Mapped[text]
    storage: Mapped[text]

    content_type: Mapped[text] = mapped_column(default="application/octet-stream")
    size: Mapped[bigint] = mapped_column(default=0)
    hash: Mapped[text] = mapped_column(default="")

    created: Mapped[datetime_tz] = mapped_column(
        default=None, insert_default=sa.func.now()
    )

    storage_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default_factory=dict)
    plugin_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default_factory=dict)

    id: Mapped[text] = mapped_column(primary_key=True, default_factory=make_uuid)

    owner: Mapped[FileOwner | None] = relationship(
        primaryjoin=sa.and_(
            FileOwner.item_id == foreign(id),
            FileOwner.item_type == "file",
        ),
        single_parent=True,
        cascade="delete, delete-orphan",
        lazy="joined",
        init=False,
        compare=False,
    )

    def dictize(self, context: Any) -> dict[str, Any]:
        result = table_dictize(self, context)
        result["storage_data"] = copy.deepcopy(result["storage_data"])

        if self.owner:
            result["owner_type"] = self.owner.owner_type
            result["owner_id"] = self.owner.owner_id
            result["pinned"] = self.owner.pinned

        else:
            result["owner_type"] = None
            result["owner_id"] = None
            result["pinned"] = False

        plugin_data = result.pop("plugin_data")
        if context.get("include_plugin_data"):
            result["plugin_data"] = copy.deepcopy(plugin_data)

        return result

    def patch_data(
        self,
        patch: dict[str, Any],
        dict_path: list[str] | None = None,
        prop: Literal["storage_data", "plugin_data"] = "plugin_data",
    ) -> dict[str, Any]:
        data: dict[str, Any] = copy.deepcopy(getattr(self, prop))

        target: Any = data
        if dict_path:
            for part in dict_path:
                target = target.setdefault(part, {})
                if not isinstance(target, dict):
                    raise TypeError(part)

        target.update(patch)

        setattr(self, prop, data)
        return data

    @classmethod
    def by_location(cls, location: str, storage: str):
        stmt = sa.select(cls).where(
            cls.location == location,
            cls.storage == storage,
        )

        return stmt
