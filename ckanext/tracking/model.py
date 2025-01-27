# encoding: utf-8
""" Tracking models

Tracking functinoality used to be implemented in core CKAN and it was
later moved to an extension during the development of CKAN 2.11.

Even when tracking models are defined here, the tables are still
being created in the database by core CKAN db migrations. This is not
ideal but it has been done this way to avoid breaking existing
installations.

If you are looking for the database migrations, you can find them in
the core CKAN folder:
ckan/migrations/versions/057_660a5aae527e_tracking.py
"""
from __future__ import annotations

import datetime

from sqlalchemy import types, Column, text, Index, Table

import ckan.model.meta as meta
import ckan.model.domain_object as domain_object
import ckan.model.types as _types
from ckan.model.base import BaseModel

__all__ = ['TrackingSummary', 'TrackingRaw']


class TrackingRaw(domain_object.DomainObject, BaseModel):

    __table__ = Table(
        "tracking_raw",
        BaseModel.metadata,
        Column("user_key", types.Unicode(100), nullable=False, primary_key=True),
        Column("url", types.UnicodeText, nullable=False, primary_key=True),
        Column("tracking_type", types.Unicode(10), nullable=False),
        Column(
            "access_timestamp",
            types.DateTime,
            primary_key=True,
            default=datetime.datetime.now
        ),
    )

    def __init__(self, user_key: str,
                 url: str,
                 tracking_type: str) -> None:
        self.user_key = user_key
        self.url = url
        self.tracking_type = tracking_type

    @classmethod
    def get(cls, **kw: _types.Any) -> TrackingRaw | None:
        """Get tracking raw entry."""
        query = meta.Session.query(cls).autoflush(False)
        return query.filter_by(**kw).first()

    @classmethod
    def create(cls, **kw: _types.Any) -> TrackingRaw:
        """Create a new tracking raw entry."""
        obj = cls(**kw)
        meta.Session.add(obj)
        meta.Session.commit()
        return obj


Index('tracking_raw_user_key', TrackingRaw.user_key)
Index('tracking_raw_url', TrackingRaw.url)
Index('tracking_raw_access_timestamp', 'access_timestamp')


class TrackingSummary(domain_object.DomainObject, BaseModel):

    __table__ = Table(
        "tracking_summary",
        BaseModel.metadata,
        Column("url", types.UnicodeText, nullable=False, primary_key=True),
        Column("package_id", types.UnicodeText),
        Column("tracking_type", types.Unicode(10), nullable=False),
        Column("count", types.Integer, nullable=False),
        Column("running_total", types.Integer, nullable=False, server_default="0"),
        Column("recent_views", types.Integer, nullable=False, server_default="0"),
        Column("tracking_date", types.Date)
    )

    def __init__(self,
                 url: str,
                 package_id: str | None,
                 tracking_type: str | None,
                 count: int,
                 running_total: int,
                 recent_views: int,
                 tracking_date: datetime.date) -> None:
        self.url = url
        self.package_id = package_id
        self.tracking_type = tracking_type
        self.count = count  # type: ignore
        self.running_total = running_total
        self.recent_views = recent_views
        self.tracking_date = tracking_date

    @classmethod
    def get(cls, **kw: _types.Any) -> TrackingSummary | None:
        obj = meta.Session.query(cls).autoflush(False)
        return obj.filter_by(**kw).first()

    @classmethod
    def create(cls, **kwargs: _types.Any) -> TrackingSummary:
        obj = cls(**kwargs)
        meta.Session.add(obj)
        meta.Session.commit()
        return obj

    @classmethod
    def update(cls, filters: dict[str, _types.Any],
               **kwargs: _types.Any) -> TrackingSummary | None:
        obj = meta.Session.query(cls).filter_by(**filters).first()
        if obj:
            for key, value in kwargs.items():
                setattr(obj, key, value)
            meta.Session.commit()
        return obj

    @classmethod
    def get_for_package(cls, package_id: str) -> dict[str, int]:
        obj = meta.Session.query(cls).autoflush(False)
        obj = obj.filter_by(package_id=package_id)
        data = obj.order_by(text('tracking_date desc')).first()
        if data:
            return {'total': data.running_total, 'recent': data.recent_views}

        return {'total': 0, 'recent': 0}

    @classmethod
    def get_for_resource(cls, url: str) -> dict[str, int]:
        obj = meta.Session.query(cls).autoflush(False)
        data = obj.filter_by(url=url).\
            order_by(text('tracking_date desc')).\
            first()
        if data:
            return {'total': data.running_total, 'recent': data.recent_views}

        return {'total': 0, 'recent': 0}


Index('tracking_summary_url', TrackingSummary.url)
Index('tracking_summary_package_id', TrackingSummary.package_id)
Index('tracking_summary_date', 'tracking_date')
