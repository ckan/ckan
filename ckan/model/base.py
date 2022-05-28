# -*- coding: utf-8 -*-

from sqlalchemy.ext.declarative import declarative_base
from .meta import metadata

Base = declarative_base(metadata=metadata)
