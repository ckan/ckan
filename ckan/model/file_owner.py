from __future__ import annotations

from typing import TYPE_CHECKING

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing_extensions import Annotated, ClassVar

from ckan.lib.dictization import table_dictize
from ckan.model.types import make_uuid
from ckan.types import Context

from .meta import registry

if TYPE_CHECKING:
    from .file import File


def now():
    return datetime.now(timezone.utc)


datetime_tz = Annotated[datetime, mapped_column(sa.DateTime(timezone=True))]
text = Annotated[str, mapped_column(sa.TEXT)]


@registry.mapped_as_dataclass
class FileOwner:
    """Model with details about current owner of an item.

    Args:
        file_id (str): ID of the owned object
        owner_id (str): ID of the owner
        owner_type (str): Type of the owner
        pinned (bool): is ownership protected from transfer

    Example:
        ```py
        owner = FileOwner(
            file_id=smth.id,
            owner_id=user.id,
            owner_type="user,
        )
        ```
    """

    __table__: ClassVar[sa.Table]

    __tablename__ = "file_owner"

    __table_args__ = (
        sa.Index("idx_owner_owner", "owner_type", "owner_id", unique=False),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["file.id"],
            "file_owner_file_id_fkey",
            ondelete="CASCADE",
        ),
    )

    file_id: Mapped[text] = mapped_column(primary_key=True)
    owner_id: Mapped[text]
    owner_type: Mapped[text]

    pinned: Mapped[bool] = mapped_column(default=False)

    files: Mapped[list["File"]] = relationship(
        back_populates="owner",
        init=False,
        compare=False,
    )

    def select_history(self):
        """Returns a select statement to fetch ownership history."""
        return (
            sa.select(FileOwnerTransferHistory)
            .join(FileOwner)
            .where(
                FileOwnerTransferHistory.file_id == self.file_id,
            )
        )

    def dictize(self, context: Context):
        return table_dictize(self, context)


@registry.mapped_as_dataclass
class FileOwnerTransferHistory:
    """Model for tracking ownership history of the file.

    Args:
        file_id (str): ID of the owned object
        owner_id (str): ID of the previous owner
        owner_type (str): Type of the previous owner
        leave_date (datetime): date of ownership transfer to a different owner
        actor (str): user who initiated ownership transfer

    Example:
        ```py
        record = FileOwnerTransferHistory(
            prev_owner.file_id,
            prev_owner.owner_id, prev_owner.owner_type,
        )
        ```
    """

    __tablename__ = "file_owner_transfer_history"

    __table_args__ = (
        sa.Index("idx_owner_transfer_item", "file_id", unique=False),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["file_owner.file_id"],
            "owner_transfer_history_file_id_fkey",
            ondelete="CASCADE",
        ),
    )

    file_id: Mapped[text]
    owner_id: Mapped[text]
    owner_type: Mapped[text]

    actor: Mapped[text]

    current_owner: Mapped[FileOwner] = relationship(init=False)

    id: Mapped[text] = mapped_column(primary_key=True, default_factory=make_uuid)
    at: Mapped[datetime_tz] = mapped_column(default=None, insert_default=sa.func.now())
    action: Mapped[text] = mapped_column(default="transfer")

    def dictize(self, context: Context):
        return table_dictize(self, context)

    @classmethod
    def from_owner(cls, owner: FileOwner, actor: str = ""):
        return cls(
            file_id=owner.file_id,
            owner_id=owner.owner_id,
            owner_type=owner.owner_type,
            actor=actor,
        )
