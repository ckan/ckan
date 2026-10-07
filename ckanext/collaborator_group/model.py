# -*- coding: utf-8 -*-

import datetime
import logging

import ckan.model.meta as meta
import ckan.model.domain_object as domain_object

from sqlalchemy import types, Column, Table, ForeignKey


log = logging.getLogger(__name__)


package_group_member_table = Table(
    "package_group_member",
    meta.metadata,
    Column("package_id", ForeignKey("package.id"), primary_key=True),
    Column("group_id", ForeignKey("group.id"), primary_key=True),
    Column("capacity", types.UnicodeText, nullable=False),
    Column("modified", types.DateTime, default=datetime.datetime.utcnow),
)


class PackageGroupMember(domain_object.DomainObject):
    package_id: str
    group_id: str
    capacity: str
    modified: datetime.datetime


meta.mapper(PackageGroupMember, package_group_member_table)


def create_tables():
    package_group_member_table.create()
    log.info("Dataset collaborator-group database tables created")


def drop_tables():
    package_group_member_table.drop()
    log.info("Dataset collaborator-group database tables dropped")


def tables_exist():
    return package_group_member_table.exists()
