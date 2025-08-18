from __future__ import annotations

from datetime import datetime, timezone
from ckan.model.types import make_uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, relationship

from ckan.lib.dictization import table_dictize
from ckan.types import Context

from .base import BaseModel


def now():
    return datetime.now(timezone.utc)


class Owner(BaseModel):
    """Model with details about current owner of an item.

    Keyword Args:
        item_id (str): ID of the owned object
        item_type (str): type of the owned object
        owner_id (str): ID of the owner
        owner_type (str): Type of the owner
        pinned (bool): is ownership protected from transfer

    Example:
        ```python
        owner = Owner(
            item_id=file.id,
            item_type="file",
            owner_id=user.id,
            owner_type="user,
        )
        ```
    """

    __table__ = sa.Table(
        "owner",
        BaseModel.metadata,
        sa.Column("item_id", sa.Text, primary_key=True),
        sa.Column("item_type", sa.Text, primary_key=True),
        sa.Column("owner_id", sa.Text, nullable=False),
        sa.Column("owner_type", sa.Text, nullable=False),
        sa.Column("pinned", sa.Boolean, default=False, nullable=False),
        sa.Index("idx_owner_owner", "owner_type", "owner_id", unique=False),
    )

    item_id: Mapped[str]
    item_type: Mapped[str]
    owner_id: Mapped[str]
    owner_type: Mapped[str]
    pinned: Mapped[bool]

    history: Mapped[OwnerTransferHistory] = relationship(
        cascade="delete, delete-orphan",
    )

    def dictize(self, context: Context):
        return table_dictize(self, context)


class OwnerTransferHistory(BaseModel):
    """Model for tracking ownership history of the file.

    Keyword Args:
        item_id (str): ID of the owned object
        item_type (str): type of the owned object
        owner_id (str): ID of the owner
        owner_type (str): Type of the owner
        leave_date (datetime): date of ownership transfer to a different owner
        actor (str | None): user who initiated ownership transfer

    Example:
        ```python
        record = TransferHistory(
            item_id=file.id,
            item_type="file",
            owner_id=prev_owner.owner_id,
            owner_type=prev_owner.owner_type,
        )
        ```
    """

    __table__ = sa.Table(
        "owner_transfer_history",
        BaseModel.metadata,
        sa.Column("id", sa.Text, primary_key=True, default=make_uuid),
        sa.Column("item_id", sa.Text, nullable=False),
        sa.Column("item_type", sa.Text, nullable=False),
        sa.Column("owner_id", sa.Text, nullable=False),
        sa.Column("owner_type", sa.Text, nullable=False),
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            default=now,
            nullable=False,
        ),
        sa.Column("action", sa.Text, nullable=False, default="transfer"),
        sa.Column("actor", sa.Text, nullable=False),
        sa.Index("idx_owner_transfer_item", "item_id", "item_type", unique=False),
        sa.ForeignKeyConstraint(
            ["item_id", "item_type"],
            ["owner.item_id", "owner.item_type"],
        ),
    )

    id: Mapped[str]
    item_id: Mapped[str]
    item_type: Mapped[str]
    owner_id: Mapped[str]
    owner_type: Mapped[str]
    at: Mapped[datetime]
    action: Mapped[str]
    actor: Mapped[str]

    current_owner: Mapped[Owner] = relationship(
        back_populates="history",
        foreign_keys=[__table__.c.item_id, __table__.c.item_type],
    )

    def dictize(self, context: Context):
        return table_dictize(self, context)

    @classmethod
    def from_owner(cls, owner: Owner):
        return cls(
            item_id=owner.item_id,
            item_type=owner.item_type,
            owner_id=owner.owner_id,
            owner_type=owner.owner_type,
        )
