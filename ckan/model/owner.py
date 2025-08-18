from __future__ import annotations

from datetime import datetime, timezone
from ckan.model.types import make_uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, relationship, mapped_column

from ckan.lib.dictization import table_dictize
from ckan.types import Context
from typing_extensions import Annotated

from .meta import registry


def now():
    return datetime.now(timezone.utc)


datetime_tz = Annotated[datetime, mapped_column(sa.DateTime(timezone=True))]
text = Annotated[str, mapped_column(sa.TEXT)]


@registry.mapped_as_dataclass
class Owner:
    """Model with details about current owner of an item.

    Args:
        item_id (str): ID of the owned object
        item_type (str): type of the owned object
        owner_id (str): ID of the owner
        owner_type (str): Type of the owner
        pinned (bool): is ownership protected from transfer

    Example:
        ```py
        owner = Owner(
            item_id=smth.id,
            item_type=smth_type,
            owner_id=user.id,
            owner_type="user,
        )
        ```
    """

    __tablename__ = "owner"

    __table_args__ = (
        sa.Index("idx_owner_owner", "owner_type", "owner_id", unique=False),
    )

    item_id: Mapped[text] = mapped_column(primary_key=True)
    item_type: Mapped[text] = mapped_column(primary_key=True)
    owner_id: Mapped[text]
    owner_type: Mapped[text]

    pinned: Mapped[bool] = mapped_column(default=False)

    def select_history(self):
        """Returns a select statement to fetch ownership history."""
        return (
            sa.select(OwnerTransferHistory)
            .join(Owner)
            .where(
                OwnerTransferHistory.item_id == self.item_id,
                OwnerTransferHistory.item_type == self.item_type,
            )
        )

    def dictize(self, context: Context):
        return table_dictize(self, context)


@registry.mapped_as_dataclass
class OwnerTransferHistory:
    """Model for tracking ownership history of the file.

    Args:
        item_id (str): ID of the owned object
        item_type (str): type of the owned object
        owner_id (str): ID of the previous owner
        owner_type (str): Type of the previous owner
        leave_date (datetime): date of ownership transfer to a different owner
        actor (str): user who initiated ownership transfer

    Example:
        ```py
        record = TransferHistory(
            prev_owner.item_id, prev_owner.item_type,
            prev_owner.owner_id, prev_owner.owner_type,
        )
        ```
    """

    __tablename__ = "owner_transfer_history"

    __table_args__ = (
        sa.Index("idx_owner_transfer_item", "item_id", "item_type", unique=False),
        sa.ForeignKeyConstraint(
            ["item_id", "item_type"],
            ["owner.item_id", "owner.item_type"],
        ),
    )

    item_id: Mapped[text]
    item_type: Mapped[text]
    owner_id: Mapped[text]
    owner_type: Mapped[text]

    actor: Mapped[text]

    current_owner: Mapped[Owner] = relationship(init=False)

    id: Mapped[text] = mapped_column(primary_key=True, default_factory=make_uuid)
    at: Mapped[datetime_tz] = mapped_column(default=None, insert_default=sa.func.now())
    action: Mapped[text] = mapped_column(default="transfer")

    def dictize(self, context: Context):
        return table_dictize(self, context)

    @classmethod
    def from_owner(cls, owner: Owner, actor: str = ""):
        return cls(
            item_id=owner.item_id,
            item_type=owner.item_type,
            owner_id=owner.owner_id,
            owner_type=owner.owner_type,
            actor=actor,
        )
